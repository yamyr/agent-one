"""In-memory world state for the Mars simulation."""

import copy
import hashlib
import logging
import random

from .config import settings
from . import storm as storm_mod
from .models import RoverAgentState, RoverWorldView, RoverComputed, RoverContext
from .models import AgentMission, InventoryItem, StoneInfo, ObstacleInfo
from .models import RoverSummary, StationContext

logger = logging.getLogger(__name__)

# ENGINE vs AGENT RESPONSIBILITY — DO NOT BREAK THIS CONTRACT:
# - Engine (world.py): enforces physics — battery drain, movement cost, pickup limits,
#   inventory capacity. It NEVER computes strategy or tells agents what to do.
# - Agents (LLM / mock fallback): observe raw state (battery %, position, station
#   position, fuel costs) and reason about actions. Return-to-base is the agent's call.
# - Tasks are LLM-owned: agents set their own task via ---TASK--- separator in their
#   text response. No Python code computes tasks or injects strategic directives.

if settings.world_seed:
    random.seed(settings.world_seed)
    logger.info("World seed: %s", settings.world_seed)

# Legacy — kept for backward compat in tests; no longer enforced as boundary
GRID_W, GRID_H = 20, 20

CHUNK_SIZE = 16

DIRECTIONS = {
    "north": (0, 1),
    "south": (0, -1),
    "east": (1, 0),
    "west": (-1, 0),
}

# --- Fuel & Battery ---
# Battery is stored as 0.0–1.0 (fraction of max capacity).
# Fuel capacity defines how many "units" of fuel an agent carries.
# Cost per tile = 1 unit = 1/capacity as a fraction.
FUEL_CAPACITY_ROVER = 350  # rover carries 350 fuel units
FUEL_CAPACITY_DRONE = 250  # drone carries 250 fuel units

BATTERY_COST_MOVE = 1 / FUEL_CAPACITY_ROVER  # ~0.00286 per tile
BATTERY_COST_MOVE_DRONE = 3 / FUEL_CAPACITY_DRONE  # 3 fuel units per tile (flying is expensive)
BATTERY_COST_DIG = 6 / FUEL_CAPACITY_ROVER  # 6 fuel units
BATTERY_COST_ANALYZE = 3 / FUEL_CAPACITY_ROVER  # 3 fuel units
BATTERY_COST_SCAN = 2 / FUEL_CAPACITY_DRONE  # 2 fuel units
BATTERY_COST_NOTIFY = 2 / FUEL_CAPACITY_ROVER  # 2 fuel units (radio notification)
CHARGE_RATE = 0.20
MAX_MOVE_DISTANCE = 3
MAX_MOVE_DISTANCE_DRONE = 6

AGENT_STARTS = {(0, 0)}

# --- Vein grades (exponential rarity: weight = 200 * e^(-1.3 * index)) ---
VEIN_GRADES = ["low", "medium", "high", "rich", "pristine"]
VEIN_WEIGHTS = [200, 60, 16, 4, 1]  # approximate: 200*e^(-1.3*i)
VEIN_QUANTITY_RANGES = {
    "low": (10, 50),
    "medium": (51, 150),
    "high": (151, 350),
    "rich": (351, 700),
    "pristine": (701, 1000),
}
TARGET_QUANTITY = 300  # mission success threshold (total basalt delivered)

ROVER_REVEAL_RADIUS = 3
DRONE_REVEAL_RADIUS = 6
REVEAL_RADIUS = ROVER_REVEAL_RADIUS  # legacy alias
MEMORY_MAX = 8

# --- Inventory ---
MAX_INVENTORY_ROVER = 3  # rover can carry at most 3 veins

# --- Solar panels ---
SOLAR_BATTERY_CAPACITY = 0.25
MAX_SOLAR_PANELS = 2

# --- Stone generation ---
STONE_PROBABILITY = 0.015
CORE_PROBABILITY = 0.3

# --- Abandoned structures ---
STRUCTURE_TYPES = [
    {
        "type": "refinery",
        "category": "building",
        "description": "An abandoned refinery capable of extracting valuable materials from basalt",
        "contents": {"processing_capacity": 50},
    },
    {
        "type": "solar_panel_structure",
        "category": "building",
        "description": "A large solar panel array that provides passive charging to nearby rovers",
        "contents": {"charge_rate": 0.01, "charge_interval": 2, "charge_radius": 1},
    },
    {
        "type": "accumulator",
        "category": "building",
        "description": "A power accumulator that increases base capacity and recharges nearby rovers",
        "contents": {"capacity_bonus": 0.20, "recharge_rate": 0.01, "recharge_interval": 5},
    },
    {
        "type": "broken_hauler",
        "category": "vehicle",
        "description": "A broken vehicle hauler once used to transport materials across the surface",
        "contents": {"salvageable_parts": ["wheels", "chassis"]},
    },
    {
        "type": "broken_manipulator",
        "category": "vehicle",
        "description": "A broken construction manipulator used to build buildings and infrastructure",
        "contents": {"salvageable_parts": ["arm", "actuator", "controller"]},
    },
]
STRUCTURE_SPAWN_RADIUS = 10  # max Manhattan distance from base (0,0)
BATTERY_COST_INVESTIGATE = 2 / FUEL_CAPACITY_ROVER  # 2 fuel units
BATTERY_COST_USE_REFINERY = 5 / FUEL_CAPACITY_ROVER  # 5 fuel units

# --- Obstacle generation ---
MOUNTAIN_PROBABILITY = 0.008  # ~0.8% per tile
GEYSER_PROBABILITY = 0.004  # ~0.4% per tile
GEYSER_CYCLE_IDLE = 8  # ticks idle before warning
GEYSER_CYCLE_WARNING = 2  # ticks in warning before erupting
GEYSER_CYCLE_ERUPTING = 3  # ticks erupting
BATTERY_COST_GEYSER = 0.10  # 10% battery drain when caught in eruption


def _random_free_pos(occupied, rng=None, cx=0, cy=0):
    """Pick a random position within a chunk area not in `occupied`."""
    r = rng or random
    x0, y0 = cx * CHUNK_SIZE, cy * CHUNK_SIZE
    for _ in range(CHUNK_SIZE * CHUNK_SIZE * 2):
        x = r.randint(x0, x0 + CHUNK_SIZE - 1)
        y = r.randint(y0, y0 + CHUNK_SIZE - 1)
        if (x, y) not in occupied:
            return x, y
    # Fallback: linear scan for any free position
    for y in range(y0, y0 + CHUNK_SIZE):
        for x in range(x0, x0 + CHUNK_SIZE):
            if (x, y) not in occupied:
                return x, y
    # Chunk fully occupied — return origin as last resort
    logger.warning("Chunk (%d,%d) fully occupied, returning origin", cx, cy)
    return x0, y0


def _spawn_abandoned_structures(rng=None):
    """Spawn one of each structure type within STRUCTURE_SPAWN_RADIUS of base (0,0).

    Uses deterministic RNG so the same world_seed always produces the same layout.
    Avoids (0,0) (station), existing stones, and previously placed structures.
    """
    r = rng or random
    occupied = set(AGENT_STARTS)  # block station tile
    # Collect existing stone positions to avoid overlap
    for s in WORLD.get("stones", []):
        occupied.add(tuple(s["position"]))

    structures = []
    for template in STRUCTURE_TYPES:
        # Find a free position within spawn radius
        for _ in range(200):  # safety limit
            x = r.randint(-STRUCTURE_SPAWN_RADIUS, STRUCTURE_SPAWN_RADIUS)
            y = r.randint(-STRUCTURE_SPAWN_RADIUS, STRUCTURE_SPAWN_RADIUS)
            if abs(x) + abs(y) > STRUCTURE_SPAWN_RADIUS:
                continue
            if (x, y) in occupied:
                continue
            occupied.add((x, y))
            structures.append(
                {
                    "type": template["type"],
                    "category": template["category"],
                    "position": [x, y],
                    "explored": False,
                    "active": False,
                    "description": template["description"],
                    "contents": dict(template["contents"]),
                }
            )
            break
    WORLD.setdefault("structures", []).extend(structures)
    logger.info(
        "Spawned %d abandoned structures within %d tiles of base",
        len(structures),
        STRUCTURE_SPAWN_RADIUS,
    )
    return structures


def _find_structure_at(x, y):
    """Find a structure at the given position, or None."""
    for s in WORLD.get("structures", []):
        if s["position"] == [x, y]:
            return s
    return None


def _get_structure_positions():
    """Return set of (x, y) tuples for all structure positions."""
    return {tuple(s["position"]) for s in WORLD.get("structures", [])}


# --------------- Chunk-based procedural generation ---------------


def _chunk_seed(cx, cy):
    """Deterministic seed for chunk (cx, cy)."""
    base = settings.world_seed or 42
    return int(hashlib.sha256(f"{base}:{cx}:{cy}".encode()).hexdigest()[:8], 16)


def _chunk_key(x, y):
    """Return the chunk coordinate for a world tile (x, y)."""
    return (
        x // CHUNK_SIZE if x >= 0 else -(-x - 1) // CHUNK_SIZE - 1,
        y // CHUNK_SIZE if y >= 0 else -(-y - 1) // CHUNK_SIZE - 1,
    )


def _ensure_chunk(cx, cy):
    """Generate and cache chunk (cx, cy) if not already present."""
    chunks = WORLD.setdefault("chunks", {})
    key = (cx, cy)
    if key in chunks:
        return chunks[key]

    rng = random.Random(_chunk_seed(cx, cy))
    x0, y0 = cx * CHUNK_SIZE, cy * CHUNK_SIZE

    # Veins: each tile has STONE_PROBABILITY chance of spawning a vein
    stones = []
    is_origin = cx == 0 and cy == 0
    occupied = set(AGENT_STARTS) if is_origin else set()

    for dy in range(CHUNK_SIZE):
        for dx in range(CHUNK_SIZE):
            wx, wy = x0 + dx, y0 + dy
            if (wx, wy) in occupied:
                continue
            if rng.random() < STONE_PROBABILITY:
                grade = rng.choices(VEIN_GRADES, weights=VEIN_WEIGHTS, k=1)[0]
                qty_lo, qty_hi = VEIN_QUANTITY_RANGES[grade]
                true_quantity = rng.randint(qty_lo, qty_hi)
                occupied.add((wx, wy))
                stones.append(
                    {
                        "position": [wx, wy],
                        "type": "unknown",
                        "_true_type": "basalt_vein",
                        "grade": "unknown",
                        "_true_grade": grade,
                        "quantity": 0,
                        "_true_quantity": true_quantity,
                        "analyzed": False,
                    }
                )

    # Origin chunk guaranteed ≥1 vein
    if is_origin and not stones:
        grade = rng.choices(VEIN_GRADES, weights=VEIN_WEIGHTS, k=1)[0]
        qty_lo, qty_hi = VEIN_QUANTITY_RANGES[grade]
        true_quantity = rng.randint(qty_lo, qty_hi)
        sx, sy = _random_free_pos(occupied, rng, cx, cy)
        occupied.add((sx, sy))
        stones.append(
            {
                "position": [sx, sy],
                "type": "unknown",
                "_true_type": "basalt_vein",
                "grade": "unknown",
                "_true_grade": grade,
                "quantity": 0,
                "_true_quantity": true_quantity,
                "analyzed": False,
            }
        )

    # Register stones in the global list
    WORLD.setdefault("stones", []).extend(stones)
    _index_stones(stones)

    # Obstacles: mountains (impassable) and geysers (periodic eruptions)
    obstacles = []
    for dy in range(CHUNK_SIZE):
        for dx in range(CHUNK_SIZE):
            wx, wy = x0 + dx, y0 + dy
            if (wx, wy) in occupied:
                continue
            if is_origin and abs(wx) <= 1 and abs(wy) <= 1:
                continue  # keep origin area clear for agents
            r = rng.random()
            if r < MOUNTAIN_PROBABILITY:
                occupied.add((wx, wy))
                obstacles.append({"position": [wx, wy], "kind": "mountain", "state": "idle"})
            elif r < MOUNTAIN_PROBABILITY + GEYSER_PROBABILITY:
                occupied.add((wx, wy))
                obstacles.append(
                    {
                        "position": [wx, wy],
                        "kind": "geyser",
                        "state": "idle",
                        "_cycle_tick": rng.randint(0, GEYSER_CYCLE_IDLE - 1),
                    }
                )

    WORLD.setdefault("obstacles", []).extend(obstacles)
    _index_obstacles(obstacles)

    chunk_data = {"generated": True, "stone_count": len(stones), "obstacle_count": len(obstacles)}
    chunks[key] = chunk_data
    logger.info(
        "Generated chunk (%d,%d) with %d stones, %d obstacles", cx, cy, len(stones), len(obstacles)
    )
    return chunk_data


def _stone_proximity_concentration(x, y):
    """Concentration based on proximity to veins (Manhattan distance).

    Higher-grade veins produce stronger signals, scaling with grade index.
    """
    max_conc = 0.0
    for s in WORLD.get("stones", []):
        sx, sy = s["position"]
        d = abs(x - sx) + abs(y - sy)
        if d == 0:
            return 1.0
        # Scale by grade: higher grade veins have a wider/stronger signal
        grade = s.get("_true_grade", "low")
        grade_idx = VEIN_GRADES.index(grade) if grade in VEIN_GRADES else 0
        # Effective radius: 10 base + 2 per grade level
        effective_radius = 10.0 + grade_idx * 2.0
        conc = max(0.0, 1.0 - d / effective_radius)
        if conc > max_conc:
            max_conc = conc
    return round(max_conc, 4)


def get_concentration(x, y):
    """Get concentration at (x, y), generating the chunk if needed."""
    cx, cy = _chunk_key(x, y)
    _ensure_chunk(cx, cy)
    return _stone_proximity_concentration(x, y)


def _cells_in_radius(cx, cy, radius):
    """Return set of (x, y) tuples within Manhattan distance `radius` of (cx, cy)."""
    cells = set()
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if abs(dx) + abs(dy) <= radius:
                cells.add((cx + dx, cy + dy))
    return cells


def _reveal_radius_for(agent):
    """Return the reveal radius for an agent based on its type."""
    return DRONE_REVEAL_RADIUS if agent.get("type") == "drone" else ROVER_REVEAL_RADIUS


def _init_revealed(cx, cy, radius=ROVER_REVEAL_RADIUS):
    """Build initial revealed set for an agent starting at (cx, cy)."""
    return [[x, y] for x, y in sorted(_cells_in_radius(cx, cy, radius))]


def _expand_revealed(agent, cx, cy):
    """Add newly visible cells around (cx, cy) to the agent's revealed list."""
    radius = _reveal_radius_for(agent)
    current = {tuple(c) for c in agent.get("revealed", [])}
    # Ensure chunks exist for all cells in reveal radius
    chunks_needed = set()
    for cell in _cells_in_radius(cx, cy, radius):
        chunks_needed.add(_chunk_key(cell[0], cell[1]))
    for ck in chunks_needed:
        _ensure_chunk(*ck)
    for cell in _cells_in_radius(cx, cy, radius):
        if cell not in current:
            agent.setdefault("revealed", []).append(list(cell))
            _update_bounds(cell[0], cell[1])


def _update_bounds(x, y):
    """Expand world bounds to include (x, y)."""
    bounds = WORLD.setdefault("bounds", {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0})
    bounds["min_x"] = min(bounds["min_x"], x)
    bounds["max_x"] = max(bounds["max_x"], x)
    bounds["min_y"] = min(bounds["min_y"], y)
    bounds["max_y"] = max(bounds["max_y"], y)


def _tools_for_ui(tool_schemas):
    """Extract {name, description} from Mistral tool schemas for the UI."""
    return [
        {"name": t["function"]["name"], "description": t["function"]["description"]}
        for t in tool_schemas
    ]


def _rover_tools_for_ui():
    from .agent import ROVER_TOOLS

    return _tools_for_ui(ROVER_TOOLS)


def _drone_tools_for_ui():
    from .agent import DRONE_TOOLS

    return _tools_for_ui(DRONE_TOOLS)


def _make_drone(start_x, start_y):
    return {
        "position": [start_x, start_y],
        "battery": 1.0,
        "mission": {"objective": "Scout terrain for precious stone deposits", "plan": []},
        "visited": [[start_x, start_y]],
        "revealed": _init_revealed(start_x, start_y, DRONE_REVEAL_RADIUS),
        "inventory": [],
        "memory": [],
        "strategic_memory": [],
        "tasks": [],
        "type": "drone",
        "tools": None,  # populated lazily via _ensure_agent_tools()
    }


def _make_rover(start_x, start_y):
    return {
        "position": [start_x, start_y],
        "battery": 1.0,
        "mission": {"objective": "Explore the terrain", "plan": []},
        "visited": [[start_x, start_y]],
        "revealed": _init_revealed(start_x, start_y),
        "inventory": [],
        "memory": [],
        "strategic_memory": [],
        "tasks": [],
        "type": "rover",
        "tools": None,  # populated lazily via _ensure_agent_tools()
        "solar_panels_remaining": MAX_SOLAR_PANELS,
    }


def _build_initial_world():
    if settings.world_seed:
        random.seed(settings.world_seed)
    world = {
        "grid": {"w": GRID_W, "h": GRID_H},  # kept for legacy compat; viewport is dynamic
        "agents": {
            "station": {
                "position": [0, 0],
                "type": "station",
                "battery": 1.0,
                "mission": {"objective": "Coordinate Mars mission", "plan": []},
                "visited": [[0, 0]],
                "memory": [],
            },
            "rover-mistral": _make_rover(0, 0),
            "rover-2": _make_rover(0, 0),
            "drone-mistral": _make_drone(0, 0),
        },
        "stones": [],
        "obstacles": [],
        "chunks": {},
        "solar_panels": [],
        "drone_scans": [],
        "structures": [],
        "tick": 0,
        "generation_id": 0,
        "bounds": {"min_x": -3, "max_x": 3, "min_y": -3, "max_y": 3},
        "mission": {
            "status": "running",
            "target_type": "basalt_vein",
            "target_quantity": TARGET_QUANTITY,
            "collected_quantity": 0,
        },
        "storm": storm_mod.make_storm_state(),
    }
    return world


def _init_world_chunks():
    """Generate starting chunks around origin after WORLD is initialized."""
    # Generate the origin chunk and immediate neighbors
    for cx in range(-1, 2):
        for cy in range(-1, 2):
            _ensure_chunk(cx, cy)
    # Spawn abandoned structures near base after chunks exist
    _spawn_abandoned_structures()


# Spatial index: (x, y) -> stone dict for O(1) lookups.
# Rebuilt lazily when the WORLD["stones"] list is replaced externally (e.g. tests).
_stone_index: dict[tuple[int, int], dict] = {}
_stone_index_source: list | None = None  # tracks which list we indexed


def _rebuild_stone_index() -> None:
    """Rebuild the spatial index from the current stones list."""
    global _stone_index_source
    stones = WORLD.get("stones", [])
    _stone_index.clear()
    for s in stones:
        _stone_index[tuple(s["position"])] = s
    _stone_index_source = stones


def _ensure_stone_index() -> None:
    """Ensure the spatial index is in sync with WORLD['stones']."""
    if WORLD.get("stones") is not _stone_index_source:
        _rebuild_stone_index()


def _index_stones(stones: list[dict]) -> None:
    """Add newly generated stones to the spatial index."""
    for s in stones:
        _stone_index[tuple(s["position"])] = s


def _unindex_stone(stone: dict) -> None:
    """Remove a stone from the spatial index."""
    _stone_index.pop(tuple(stone["position"]), None)


# Spatial index for obstacles: (x, y) -> obstacle dict for O(1) lookups.
_obstacle_index: dict[tuple[int, int], dict] = {}
_obstacle_index_source: list | None = None


def _rebuild_obstacle_index() -> None:
    """Rebuild the obstacle spatial index from the current obstacles list."""
    global _obstacle_index_source
    obstacles = WORLD.get("obstacles", [])
    _obstacle_index.clear()
    for o in obstacles:
        _obstacle_index[tuple(o["position"])] = o
    _obstacle_index_source = obstacles


def _ensure_obstacle_index() -> None:
    """Ensure the obstacle spatial index is in sync with WORLD['obstacles']."""
    if WORLD.get("obstacles") is not _obstacle_index_source:
        _rebuild_obstacle_index()


def _index_obstacles(obstacles: list[dict]) -> None:
    """Add newly generated obstacles to the spatial index."""
    for o in obstacles:
        _obstacle_index[tuple(o["position"])] = o


def is_obstacle_at(x: int, y: int) -> dict | None:
    """Return the obstacle at (x, y) if any, else None. Public API."""
    _ensure_obstacle_index()
    return _obstacle_index.get((x, y))


WORLD = _build_initial_world()
_init_world_chunks()
storm_mod.schedule_next_storm(WORLD)


class World:
    """Instance-based wrapper around the world state dict.

    Enables multi-simulation and thread-safe access (future).
    During migration, wraps the module-level WORLD dict.
    """

    def __init__(self, state: dict | None = None):
        self._state = state if state is not None else _build_initial_world()
        if state is None:
            _init_world_chunks()

    @property
    def state(self) -> dict:
        """Raw world state dict. Prefer typed accessors; use this for
        test setup or bulk reads that don't have a dedicated method yet."""
        return self._state

    # --- Reads ---
    def get_agent(self, agent_id: str) -> dict:
        return self._state["agents"][agent_id]

    def get_agents(self) -> dict:
        return self._state["agents"]

    def get_mission(self) -> dict:
        return self._state["mission"]

    def get_stones(self) -> list:
        return self._state.get("stones", [])

    def get_solar_panels(self) -> list:
        return self._state.get("solar_panels", [])

    def get_drone_scans(self) -> list:
        return self._state.get("drone_scans", [])

    def get_structures(self) -> list:
        return self._state.get("structures", [])

    def get_tick(self) -> int:
        return self._state["tick"]

    # --- Setters ---
    def set_agent_model(self, agent_id: str, model: str):
        self._state["agents"][agent_id]["model"] = model

    def set_agent_last_context(self, agent_id: str, context: str):
        self._state["agents"][agent_id]["last_context"] = context

    def set_pending_commands(self, agent_id: str, commands: list | None):
        if commands:
            self._state["agents"][agent_id]["pending_commands"] = commands
        else:
            self._state["agents"][agent_id].pop("pending_commands", None)

    def get_generation_id(self) -> int:
        return self._state.get("generation_id", 0)

    def summarize_memories(self, agent_id: str) -> str | None:
        return summarize_memories(agent_id)

    def record_strategic_insight(self, agent_id: str, insight: str, tick: int):
        record_strategic_insight(agent_id, insight, tick)


# Module-level singleton wrapping the global WORLD dict
world = World(WORLD)


# -- Inter-agent message relay --

AGENT_MESSAGES: list[dict] = []


def send_agent_message(from_id: str, to_id: str, message: str) -> dict:
    """Route a message from one agent to another (via station relay)."""
    msg = {
        "from": from_id,
        "to": to_id,
        "message": message,
        "tick": WORLD["tick"],
        "read": False,
    }
    AGENT_MESSAGES.append(msg)
    return {"ok": True, "message": message, "to": to_id}


def get_unread_messages(agent_id: str) -> list[dict]:
    """Get and mark as read all messages for an agent."""
    unread = [m for m in AGENT_MESSAGES if m["to"] == agent_id and not m["read"]]
    for m in unread:
        m["read"] = True
    return unread


def get_drone_intel_for_rover(rover_id: str) -> list[dict]:
    """Return drone scan hotspots that the rover hasn't visited yet."""
    rover = WORLD["agents"].get(rover_id)
    if not rover:
        return []
    visited = set(map(tuple, rover.get("visited", [])))
    intel = []
    for scan in WORLD.get("drone_scans", []):
        readings = scan.get("readings", {})
        for cell_key, conc in readings.items():
            if conc <= 0.3:
                continue
            parts = cell_key.split(",")
            cx, cy = int(parts[0]), int(parts[1])
            if (cx, cy) in visited:
                continue
            intel.append(
                {
                    "position": [cx, cy],
                    "concentration": round(conc, 2),
                    "scanned_by": scan.get("scanner", scan.get("agent_id", "drone")),
                    "tick": scan.get("tick", 0),
                }
            )
    intel.sort(key=lambda x: x["concentration"], reverse=True)
    return intel[:5]


def reset_world():
    """Reset WORLD to initial state. Re-seeds RNG if world_seed is set."""
    gen = WORLD.get("generation_id", 0) + 1
    fresh = _build_initial_world()
    fresh["generation_id"] = gen
    WORLD.clear()
    WORLD.update(fresh)
    _stone_index.clear()
    global _stone_index_source
    _stone_index_source = None
    _obstacle_index.clear()
    global _obstacle_index_source
    _obstacle_index_source = None
    AGENT_MESSAGES.clear()
    _init_world_chunks()
    storm_mod.schedule_next_storm(WORLD)
    logger.info("World reset (generation %d)", gen)


def next_tick():
    """Increment and return the current tick number."""
    WORLD["tick"] += 1
    apply_structure_passive_effects()
    return WORLD["tick"]


def update_geysers():
    """Advance geyser state machines. Returns list of eruption event dicts.

    Geysers cycle: idle → warning → erupting → idle.
    Agents standing on an erupting geyser lose BATTERY_COST_GEYSER battery.
    """
    events = []
    for obs in WORLD.get("obstacles", []):
        if obs["kind"] != "geyser":
            continue
        ct = obs.get("_cycle_tick", 0) + 1
        total = GEYSER_CYCLE_IDLE + GEYSER_CYCLE_WARNING + GEYSER_CYCLE_ERUPTING
        phase = ct % total
        if phase < GEYSER_CYCLE_IDLE:
            obs["state"] = "idle"
        elif phase < GEYSER_CYCLE_IDLE + GEYSER_CYCLE_WARNING:
            obs["state"] = "warning"
        else:
            if obs["state"] != "erupting":
                # Transition to erupting — apply damage to agents on this tile
                gx, gy = obs["position"]
                for aid, agent in WORLD["agents"].items():
                    if agent.get("type") == "station":
                        continue
                    ax, ay = agent["position"]
                    if ax == gx and ay == gy:
                        old_bat = agent["battery"]
                        agent["battery"] = max(0.0, old_bat - BATTERY_COST_GEYSER)
                        events.append(
                            {
                                "type": "geyser_eruption",
                                "position": [gx, gy],
                                "agent_id": aid,
                                "battery_before": old_bat,
                                "battery_after": agent["battery"],
                            }
                        )
                        logger.info(
                            "Geyser eruption at (%d,%d) hit %s: %.0f%% -> %.0f%%",
                            gx,
                            gy,
                            aid,
                            old_bat * 100,
                            agent["battery"] * 100,
                        )
            obs["state"] = "erupting"
        obs["_cycle_tick"] = ct
    return events


def check_ground(agent_id):
    """Check if a vein is present at the agent's current position."""
    agent = WORLD["agents"].get(agent_id)
    if agent is None:
        return {"stone": None}
    x, y = agent["position"]
    stone = _find_stone_at(x, y)
    if stone:
        return {
            "stone": {
                "type": stone["type"],
                "grade": stone.get("grade", "unknown"),
                "quantity": stone.get("quantity", 0),
            }
        }
    return {"stone": None}


def move_agent(agent_id, x, y):
    """Move an agent to target (x, y). Must be a straight cardinal line, respecting per-agent max distance."""
    agent = WORLD["agents"].get(agent_id)
    if agent is None:
        return {"ok": False, "error": f"Unknown agent: {agent_id}"}

    max_dist = MAX_MOVE_DISTANCE_DRONE if agent.get("type") == "drone" else MAX_MOVE_DISTANCE

    ox, oy = agent["position"]
    dx, dy = x - ox, y - oy
    dist = abs(dx) + abs(dy)
    if dist == 0:
        return {"ok": False, "error": f"Already at ({x}, {y})"}
    if dist > max_dist:
        return {"ok": False, "error": f"Too far: {dist} tiles (max {max_dist})"}
    if dx != 0 and dy != 0:
        return {"ok": False, "error": f"Not a straight line: ({ox}, {oy}) -> ({x}, {y})"}

    # Check for obstacles (structures) along the movement path
    structure_positions = _get_structure_positions()
    step_dx = (1 if dx > 0 else -1) if dx != 0 else 0
    step_dy = (1 if dy > 0 else -1) if dy != 0 else 0
    for step in range(1, dist + 1):
        check_x, check_y = ox + step_dx * step, oy + step_dy * step
        if (check_x, check_y) in structure_positions:
            struct = _find_structure_at(check_x, check_y)
            label = struct["type"].replace("_", " ") if struct else "structure"
            return {"ok": False, "error": f"Path blocked by {label} at ({check_x}, {check_y})"}

    # Ensure chunk exists at destination
    _ensure_chunk(*_chunk_key(x, y))
    _update_bounds(x, y)

    # Block movement onto mountains
    obs = is_obstacle_at(x, y)
    if obs and obs["kind"] == "mountain":
        return {"ok": False, "error": f"Mountain blocks path at ({x}, {y})"}

    agent["position"] = [x, y]
    logger.info("Agent %s moved (%d,%d) -> (%d,%d)", agent_id, ox, oy, x, y)
    return {"ok": True, "from": [ox, oy], "to": [x, y], "distance": dist}


def execute_action(agent_id, action_name, params):
    """Engine entry point: execute an action and update world + agent state."""
    agent = WORLD["agents"].get(agent_id)
    if agent is None:
        return {"ok": False, "error": f"Unknown agent: {agent_id}"}

    is_drone = agent.get("type") == "drone"

    if action_name == "move":
        direction = params.get("direction")
        delta = DIRECTIONS.get(direction)
        if delta is None:
            return {"ok": False, "error": f"Invalid direction: {direction}"}

        # Storm move failure (rovers only)
        if not is_drone and storm_mod.should_move_fail(WORLD):
            record_memory(agent_id, f"Move {direction} failed: dust storm interference")
            return {
                "ok": False,
                "error": "Move blocked by dust storm",
                "storm_blocked": True,
            }

        max_dist = MAX_MOVE_DISTANCE_DRONE if is_drone else MAX_MOVE_DISTANCE
        move_cost = BATTERY_COST_MOVE_DRONE if is_drone else BATTERY_COST_MOVE
        distance = max(1, min(max_dist, int(params.get("distance", 1))))

        # Apply storm battery multiplier
        storm_mult = storm_mod.get_battery_multiplier(WORLD)
        cost = move_cost * distance * storm_mult
        if agent["battery"] < cost:
            record_memory(
                agent_id,
                f"Failed move {direction}: not enough battery ({agent['battery']:.0%} < {cost:.0%})",
            )
            return {
                "ok": False,
                "error": f"Not enough battery to move {distance} tiles (need {cost:.0%}, have {agent['battery']:.0%})",
            }

        ox, oy = agent["position"]
        tx, ty = ox + delta[0] * distance, oy + delta[1] * distance
        result = move_agent(agent_id, tx, ty)
        if result["ok"]:
            agent["battery"] = max(0.0, agent["battery"] - cost)
            # Mark all intermediate + destination tiles as visited/revealed
            for step in range(1, distance + 1):
                sx, sy = ox + delta[0] * step, oy + delta[1] * step
                if [sx, sy] not in agent["visited"]:
                    agent["visited"].append([sx, sy])
                _expand_revealed(agent, sx, sy)
            result["ground"] = check_ground(agent_id)
            ground = result["ground"]
            if ground["stone"]:
                record_memory(
                    agent_id,
                    f"Moved {direction} {distance} to ({tx},{ty}), found {ground['stone']['type']} stone",
                )
            else:
                record_memory(
                    agent_id, f"Moved {direction} {distance} to ({tx},{ty}), empty ground"
                )
    elif action_name == "analyze":
        if is_drone:
            return {"ok": False, "error": "Drones cannot analyze veins"}
        result = _execute_analyze(agent_id, agent)
        if result["ok"]:
            record_memory(
                agent_id,
                f"Analyzed vein at ({result['position'][0]},{result['position'][1]}), grade={result['stone']['grade']}, qty={result['stone']['quantity']}",
            )
    elif action_name == "dig":
        if is_drone:
            return {"ok": False, "error": "Drones cannot dig"}
        result = _execute_dig(agent_id, agent)
        if result["ok"]:
            record_memory(
                agent_id,
                f"Dug and collected {result['stone']['grade']} vein (qty={result['stone']['quantity']}) at ({result['position'][0]},{result['position'][1]}), inventory={result['inventory_count']}",
            )
    elif action_name == "scan":
        result = _execute_scan(agent_id, agent)
        if result["ok"]:
            record_memory(
                agent_id,
                f"Scanned area around ({result['position'][0]},{result['position'][1]}), peak concentration={result['peak']:.3f}",
            )
    elif action_name == "deploy_solar_panel":
        if is_drone:
            return {"ok": False, "error": "Drones cannot deploy solar panels"}
        result = _execute_deploy_solar_panel(agent_id)
    elif action_name == "use_solar_battery":
        if is_drone:
            return {"ok": False, "error": "Drones cannot use solar batteries"}
        result = _execute_use_solar_battery(agent_id)
    elif action_name == "notify":
        result = _execute_notify(agent_id, agent, params)
        if result["ok"]:
            record_memory(agent_id, f"Notified station: {result['message']}")
    elif action_name == "investigate_structure":
        if is_drone:
            return {"ok": False, "error": "Drones cannot investigate structures"}
        result = _execute_investigate_structure(agent_id, agent, params)
    elif action_name == "use_refinery":
        if is_drone:
            return {"ok": False, "error": "Drones cannot use the refinery"}
        result = _execute_use_refinery(agent_id, agent)
    else:
        return {"ok": False, "error": f"Unknown action: {action_name}"}

    if not result["ok"]:
        record_memory(agent_id, f"Failed {action_name}: {result.get('error', '?')}")

    if result["ok"]:
        mission_event = check_mission_status()
        if mission_event:
            result["mission"] = mission_event

    return result


def _find_stone_at(x, y):
    """Find a stone at the given position, or None. O(1) via spatial index."""
    _ensure_stone_index()
    return _stone_index.get((x, y))


def _execute_analyze(agent_id, agent):
    """Analyze an unknown vein at the current tile to reveal its type, grade, and quantity."""
    storm_mult = storm_mod.get_battery_multiplier(WORLD)
    cost = BATTERY_COST_ANALYZE * storm_mult
    if agent["battery"] < cost:
        return {"ok": False, "error": "Not enough battery to analyze"}

    x, y = agent["position"]
    stone = _find_stone_at(x, y)
    if stone is None:
        return {"ok": False, "error": f"No vein at ({x}, {y})"}
    if stone.get("analyzed"):
        return {"ok": False, "error": f"Vein at ({x}, {y}) already analyzed"}

    agent["battery"] = max(0.0, agent["battery"] - cost)
    stone["analyzed"] = True
    stone["type"] = stone["_true_type"]
    stone["grade"] = stone["_true_grade"]
    stone["quantity"] = stone["_true_quantity"]
    logger.info(
        "Agent %s analyzed vein at (%d,%d), type=%s grade=%s qty=%d",
        agent_id,
        x,
        y,
        stone["type"],
        stone["grade"],
        stone["quantity"],
    )
    return {
        "ok": True,
        "position": [x, y],
        "stone": {
            "type": stone["type"],
            "grade": stone["grade"],
            "quantity": stone["quantity"],
        },
    }


def _execute_scan(agent_id, agent):
    """Drone aerial scan: sample concentration map around current position."""
    storm_mult = storm_mod.get_battery_multiplier(WORLD)
    cost = BATTERY_COST_SCAN * storm_mult
    if agent["battery"] < cost:
        return {"ok": False, "error": "Not enough battery to scan"}

    x, y = agent["position"]
    agent["battery"] = max(0.0, agent["battery"] - cost)
    scan_radius = DRONE_REVEAL_RADIUS
    readings = {}
    peak = 0.0
    for cell in _cells_in_radius(x, y, scan_radius):
        val = get_concentration(cell[0], cell[1])
        readings[f"{cell[0]},{cell[1]}"] = round(val, 3)
        if val > peak:
            peak = val

    scan_entry = {
        "position": [x, y],
        "readings": readings,
        "peak": round(peak, 3),
        "scanner": agent_id,
    }
    WORLD.setdefault("drone_scans", []).append(scan_entry)
    logger.info("Agent %s scanned at (%d,%d), peak=%.3f", agent_id, x, y, peak)
    return {"ok": True, "position": [x, y], "readings": readings, "peak": round(peak, 3)}


def _execute_dig(agent_id, agent):
    """Dig and collect an analyzed vein at current tile into inventory."""
    if len(agent.get("inventory", [])) >= MAX_INVENTORY_ROVER:
        return {"ok": False, "error": "Inventory full (max 3 veins)"}
    storm_mult = storm_mod.get_battery_multiplier(WORLD)
    cost = BATTERY_COST_DIG * storm_mult
    if agent["battery"] < cost:
        return {"ok": False, "error": "Not enough battery to dig"}

    x, y = agent["position"]
    stone = _find_stone_at(x, y)
    if stone is None:
        return {"ok": False, "error": f"No vein at ({x}, {y})"}
    if not stone.get("analyzed"):
        return {"ok": False, "error": "Vein not yet analyzed (analyze first)"}

    agent["battery"] = max(0.0, agent["battery"] - cost)
    agent.setdefault("inventory", []).append(
        {
            "type": stone["type"],
            "grade": stone["grade"],
            "quantity": stone["quantity"],
        }
    )
    WORLD["stones"].remove(stone)
    _unindex_stone(stone)
    logger.info(
        "Agent %s dug and collected %s grade=%s qty=%d at (%d,%d)",
        agent_id,
        stone["type"],
        stone["grade"],
        stone["quantity"],
        x,
        y,
    )
    return {
        "ok": True,
        "position": [x, y],
        "stone": {
            "type": stone["type"],
            "grade": stone["grade"],
            "quantity": stone["quantity"],
        },
        "inventory_count": len(agent["inventory"]),
    }


def _execute_notify(agent_id, agent, params):
    """Send a radio notification to station. Costs 2 fuel."""
    storm_mult = storm_mod.get_battery_multiplier(WORLD)
    cost = BATTERY_COST_NOTIFY * storm_mult
    if agent["battery"] < cost:
        return {"ok": False, "error": "Not enough battery to notify"}
    message = params.get("message", "")
    if not message:
        return {"ok": False, "error": "Empty message"}
    agent["battery"] = max(0.0, agent["battery"] - cost)
    return {
        "ok": True,
        "position": list(agent["position"]),
        "message": message,
    }


def _execute_charge(agent_id, agent):
    """Recharge battery at the station."""
    station = WORLD["agents"].get("station")
    if station is None:
        return {"ok": False, "error": "No station in world"}

    if agent["position"] != station["position"]:
        return {"ok": False, "error": "Not at station (must be co-located to charge)"}

    if agent["battery"] >= 1.0:
        return {"ok": False, "error": "Battery already full"}

    old_battery = agent["battery"]
    agent["battery"] = min(1.0, agent["battery"] + CHARGE_RATE)
    logger.info(
        "Agent %s charged %.0f%% -> %.0f%%", agent_id, old_battery * 100, agent["battery"] * 100
    )
    return {
        "ok": True,
        "agent_id": agent_id,
        "battery_before": old_battery,
        "battery_after": agent["battery"],
    }


def charge_agent(agent_id):
    """Station-initiated charge: recharge any non-station agent co-located with the station."""
    agent = WORLD["agents"].get(agent_id)
    if agent is None:
        return {"ok": False, "error": f"Unknown agent: {agent_id}"}
    if agent.get("type") == "station":
        return {"ok": False, "error": f"{agent_id} is a station"}
    result = _execute_charge(agent_id, agent)
    if result["ok"]:
        record_memory(
            agent_id,
            f"Station charged battery {result['battery_before']:.0%} -> {result['battery_after']:.0%}",
        )
    return result


# Backward-compat alias
charge_rover = charge_agent


# --- Agent setters (seal direct WORLD writes from other modules) ---


def set_agent_model(agent_id: str, model: str):
    world.set_agent_model(agent_id, model)


def set_agent_last_context(agent_id: str, context: str):
    world.set_agent_last_context(agent_id, context)


def set_pending_commands(agent_id: str, commands: list | None):
    world.set_pending_commands(agent_id, commands)


def check_mission_status():
    """Update mission collected_quantity and detect success/failure.

    Returns a mission event dict if the status changed, or None.
    """
    mission = WORLD["mission"]
    if mission["status"] in ("success", "failed"):
        return None

    # Sum quantities across all rover inventories
    station = WORLD["agents"].get("station")
    station_pos = station["position"] if station else [0, 0]
    collected_qty = 0
    delivered_qty = 0
    for agent in WORLD["agents"].values():
        if agent.get("type") != "rover":
            continue
        for stone in agent.get("inventory", []):
            if stone["type"] == mission["target_type"]:
                qty = stone.get("quantity", 0)
                collected_qty += qty
                if agent["position"] == station_pos:
                    delivered_qty += qty
    mission["collected_quantity"] = delivered_qty
    mission["in_transit_quantity"] = collected_qty - delivered_qty

    # Success: enough total basalt quantity delivered to station
    if delivered_qty >= mission["target_quantity"]:
        mission["status"] = "success"
        logger.info(
            "Mission SUCCESS: delivered %d/%d basalt to station",
            delivered_qty,
            mission["target_quantity"],
        )
        return {
            "status": "success",
            "collected_quantity": collected_qty,
            "delivered_quantity": delivered_qty,
        }

    # Failure: all rovers have zero battery and none are at the station
    all_dead = True
    for agent in WORLD["agents"].values():
        if agent.get("type") != "rover":
            continue
        if agent["battery"] > 0:
            all_dead = False
            break
        if station_pos and agent["position"] == station_pos:
            all_dead = False
            break
    if all_dead:
        mission["status"] = "failed"
        logger.info("Mission FAILED: all rovers depleted")
        return {"status": "failed", "reason": "all_rovers_depleted"}

    return None


def abort_mission(reason="Manual abort from mission control"):
    """Manually abort the running mission. Returns event dict or None if already terminal."""
    mission = WORLD["mission"]
    if mission["status"] in ("success", "failed", "aborted"):
        return None
    mission["status"] = "aborted"
    # Override each agent's mission objective so it shows in UI
    for agent in WORLD["agents"].values():
        if agent.get("type") in ("rover", "drone"):
            agent["mission"]["objective"] = "ABORTED — return to station"
    logger.info("Mission ABORTED: %s", reason)
    return {"status": "aborted", "reason": reason}


def all_agents_at_station():
    """Check if all mobile agents are at the station. Used to finalize abort."""
    station = WORLD["agents"].get("station")
    if not station:
        return True
    sp = station["position"]
    for agent in WORLD["agents"].values():
        if agent.get("type") not in ("rover", "drone"):
            continue
        if agent["position"] != sp:
            return False
    return True


def record_memory(agent_id, text):
    """Append a short-term memory entry to an agent's memory log."""
    agent = WORLD["agents"].get(agent_id)
    if agent is None:
        return
    mem = agent.setdefault("memory", [])
    mem.append(text)
    if len(mem) > MEMORY_MAX:
        del mem[: len(mem) - MEMORY_MAX]


def summarize_memories(agent_id: str) -> str | None:
    """Return a summary prompt for the agent's memories, or None if too few."""
    agent = WORLD["agents"].get(agent_id)
    if agent is None:
        return None
    memories = agent.get("memory", [])
    if len(memories) < 6:
        return None
    mem_text = "\n".join(f"- {m}" for m in memories[-8:])
    return (
        "Summarize the following rover exploration memories into 1-2 strategic "
        "insights (e.g., 'Zone B3 consistently yields high-grade minerals', "
        "'Storms from the north tend to last 3 ticks'). Be concise.\n\n"
        f"{mem_text}"
    )


def record_strategic_insight(agent_id: str, insight: str, tick: int):
    """Store a strategic insight for the agent, capped at 5."""
    agent = WORLD["agents"].get(agent_id)
    if agent is None:
        return
    sm = agent.setdefault("strategic_memory", [])
    sm.append({"insight": insight, "tick": tick})
    if len(sm) > 5:
        agent["strategic_memory"] = sm[-5:]


def direction_hint(dx, dy):
    """Return human-readable direction hint from deltas.

    Math convention: north = +Y, south = -Y.
    """
    parts = []
    if dy > 0:
        parts.append("north")
    elif dy < 0:
        parts.append("south")
    if dx > 0:
        parts.append("east")
    elif dx < 0:
        parts.append("west")
    return ", ".join(parts) if parts else "here"


def _execute_deploy_solar_panel(agent_id):
    agent = WORLD["agents"].get(agent_id)
    if agent is None or agent.get("type") != "rover":
        return {"ok": False, "error": f"{agent_id} is not a rover"}
    remaining = agent.get("solar_panels_remaining", 0)
    if remaining <= 0:
        return {"ok": False, "error": "No solar panels remaining"}
    x, y = agent["position"]
    for p in WORLD.get("solar_panels", []):
        if p["position"] == [x, y]:
            return {"ok": False, "error": "Solar panel already deployed here"}
    panel = {
        "position": [x, y],
        "battery": SOLAR_BATTERY_CAPACITY,
        "deployed_by": agent_id,
        "depleted": False,
    }
    WORLD.setdefault("solar_panels", []).append(panel)
    agent["solar_panels_remaining"] = remaining - 1
    agent["battery"] = max(0.0, agent["battery"] - BATTERY_COST_MOVE)  # deploy costs 1 fuel
    record_memory(
        agent_id, f"Deployed solar panel at ({x},{y}) — {SOLAR_BATTERY_CAPACITY:.0%} battery"
    )
    return {"ok": True, "result": f"Solar panel deployed at ({x},{y})", "panel": panel}


def _execute_use_solar_battery(agent_id):
    agent = WORLD["agents"].get(agent_id)
    if agent is None or agent.get("type") != "rover":
        return {"ok": False, "error": f"{agent_id} is not a rover"}
    x, y = agent["position"]
    for panel in WORLD.get("solar_panels", []):
        if panel["position"] == [x, y] and not panel["depleted"]:
            charge = panel["battery"]
            agent["battery"] = min(1.0, agent["battery"] + charge)
            panel["battery"] = 0.0
            panel["depleted"] = True
            record_memory(agent_id, f"Used solar battery at ({x},{y}), gained {charge:.0%}")
            return {
                "ok": True,
                "result": f"Recharged {charge:.0%} from solar panel",
                "new_battery": agent["battery"],
            }
    return {"ok": False, "error": "No active solar panel at current position"}


def _nearest_solar_panel(x, y):
    best = None
    best_dist = float("inf")
    for panel in WORLD.get("solar_panels", []):
        if panel["depleted"]:
            continue
        px, py = panel["position"]
        d = abs(px - x) + abs(py - y)
        if d < best_dist:
            best_dist = d
            best = panel
    return best


# --- Abandoned structure interactions ---


def _execute_investigate_structure(agent_id, agent, params):
    """Investigate an adjacent structure to reveal its details."""
    if agent["battery"] < BATTERY_COST_INVESTIGATE:
        return {"ok": False, "error": "Not enough battery to investigate"}

    x, y = agent["position"]
    # Find adjacent structure (Manhattan distance 1)
    target = None
    for s in WORLD.get("structures", []):
        sx, sy = s["position"]
        if abs(sx - x) + abs(sy - y) <= 1:
            target = s
            break

    if target is None:
        return {"ok": False, "error": "No structure within reach (must be adjacent, 1 tile)"}

    if target["explored"]:
        return {
            "ok": False,
            "error": f"{target['type'].replace('_', ' ').title()} already investigated",
        }

    agent["battery"] = max(0.0, agent["battery"] - BATTERY_COST_INVESTIGATE)
    target["explored"] = True
    target["active"] = True
    logger.info(
        "Agent %s investigated %s at (%d,%d)",
        agent_id,
        target["type"],
        target["position"][0],
        target["position"][1],
    )
    record_memory(
        agent_id,
        f"Investigated {target['type'].replace('_', ' ')} at ({target['position'][0]},{target['position'][1]}): {target['description']}",
    )
    return {
        "ok": True,
        "structure": {
            "type": target["type"],
            "category": target["category"],
            "position": target["position"],
            "description": target["description"],
            "contents": target["contents"],
        },
    }


def _execute_use_refinery(agent_id, agent):
    """Use the refinery to process basalt from rover inventory into refined materials."""
    if agent["battery"] < BATTERY_COST_USE_REFINERY:
        return {"ok": False, "error": "Not enough battery to use refinery"}

    x, y = agent["position"]
    # Find adjacent active refinery
    refinery = None
    for s in WORLD.get("structures", []):
        if s["type"] != "refinery":
            continue
        sx, sy = s["position"]
        if abs(sx - x) + abs(sy - y) <= 1 and s.get("active"):
            refinery = s
            break

    if refinery is None:
        return {
            "ok": False,
            "error": "No active refinery within reach (must investigate first and be adjacent)",
        }

    inventory = agent.get("inventory", [])
    basalt_items = [i for i in inventory if i.get("type") == "basalt_vein"]
    if not basalt_items:
        return {"ok": False, "error": "No basalt in inventory to refine"}

    # Process the first basalt item — refining doubles its effective quantity
    item = basalt_items[0]
    original_qty = item.get("quantity", 0)
    bonus = int(original_qty * 0.5)  # +50% bonus from refining
    item["quantity"] = original_qty + bonus
    item["refined"] = True

    agent["battery"] = max(0.0, agent["battery"] - BATTERY_COST_USE_REFINERY)
    logger.info(
        "Agent %s refined basalt at refinery: %d -> %d (bonus +%d)",
        agent_id,
        original_qty,
        item["quantity"],
        bonus,
    )
    record_memory(
        agent_id,
        f"Refined basalt at refinery: {original_qty} -> {item['quantity']} units (+{bonus} bonus)",
    )
    return {
        "ok": True,
        "original_quantity": original_qty,
        "refined_quantity": item["quantity"],
        "bonus": bonus,
    }


def apply_structure_passive_effects():
    """Apply passive effects from active structures. Called each simulation tick.

    - Solar Panel Structure: +1% battery per 2 ticks to rovers within 1 tile.
    - Accumulator: +1% battery per 5 ticks to rovers within range.
    """
    tick = WORLD.get("tick", 0)
    for structure in WORLD.get("structures", []):
        if not structure.get("active"):
            continue

        sx, sy = structure["position"]

        if structure["type"] == "solar_panel_structure":
            # +1% per 2 ticks to rovers within 1 tile (Manhattan)
            interval = structure["contents"].get("charge_interval", 2)
            if tick % interval != 0:
                continue
            charge = structure["contents"].get("charge_rate", 0.01)
            radius = structure["contents"].get("charge_radius", 1)
            for agent in WORLD["agents"].values():
                if agent.get("type") not in ("rover", "drone"):
                    continue
                ax, ay = agent["position"]
                if abs(ax - sx) + abs(ay - sy) <= radius:
                    old = agent["battery"]
                    agent["battery"] = min(1.0, agent["battery"] + charge)
                    if agent["battery"] > old:
                        logger.debug(
                            "Solar panel structure at (%d,%d) charged agent at (%d,%d): %.0f%% -> %.0f%%",
                            sx,
                            sy,
                            ax,
                            ay,
                            old * 100,
                            agent["battery"] * 100,
                        )

        elif structure["type"] == "accumulator":
            # +1% per 5 ticks to rovers nearby (within 2 tiles)
            interval = structure["contents"].get("recharge_interval", 5)
            if tick % interval != 0:
                continue
            charge = structure["contents"].get("recharge_rate", 0.01)
            for agent in WORLD["agents"].values():
                if agent.get("type") not in ("rover", "drone"):
                    continue
                ax, ay = agent["position"]
                if abs(ax - sx) + abs(ay - sy) <= 2:
                    old = agent["battery"]
                    agent["battery"] = min(1.0, agent["battery"] + charge)
                    if agent["battery"] > old:
                        logger.debug(
                            "Accumulator at (%d,%d) recharged agent at (%d,%d): %.0f%% -> %.0f%%",
                            sx,
                            sy,
                            ax,
                            ay,
                            old * 100,
                            agent["battery"] * 100,
                        )


def update_tasks(agent_id):
    """Recompute short-term tasks for an agent based on current world state.

    Returns the new primary task string if it changed, else None.
    """
    agent = WORLD["agents"].get(agent_id)
    if agent is None:
        return None
    old_task = agent["tasks"][0] if agent.get("tasks") else None
    old_key = old_task.split(" — ")[0] if old_task else None
    # Mission aborted — only task is return to station
    if WORLD["mission"]["status"] == "aborted":
        station = WORLD["agents"].get("station")
        sp = station["position"] if station else [0, 0]
        x, y = agent["position"]
        if [x, y] == sp:
            agent["tasks"] = ["At station — mission aborted, standing by"]
        else:
            dist = abs(sp[0] - x) + abs(sp[1] - y)
            hint = direction_hint(sp[0] - x, sp[1] - y)
            agent["tasks"] = [
                f"MISSION ABORTED — return to station at ({sp[0]},{sp[1]}) — {hint}, {dist} tiles"
            ]
        return
    if agent.get("type") == "drone":
        _update_drone_tasks(agent_id, agent)
    else:
        _update_rover_tasks(agent_id, agent)

    new_task = agent["tasks"][0] if agent.get("tasks") else None
    new_key = new_task.split(" — ")[0] if new_task else None
    if new_key != old_key:
        return new_task
    return None


def _update_drone_tasks(agent_id, agent):
    """Recompute tasks for a drone — scan unscanned areas, explore the map."""
    x, y = agent["position"]
    _ = {tuple(c) for c in agent.get("visited", [])}  # reserved for future use
    tasks = []

    # Check if current area has been scanned already
    scanned_positions = {tuple(s["position"]) for s in WORLD.get("drone_scans", [])}
    if (x, y) not in scanned_positions:
        tasks.append(f"Scan area at current position ({x},{y})")

    # Find nearest unscanned region within a search radius around the drone
    search_radius = 30
    best_target = None
    best_dist = float("inf")
    for gx in range(x - search_radius, x + search_radius + 1):
        for gy in range(y - search_radius, y + search_radius + 1):
            if (gx, gy) in scanned_positions:
                continue
            min_scan_dist = min(
                (abs(gx - sp[0]) + abs(gy - sp[1]) for sp in scanned_positions),
                default=search_radius * 2,
            )
            if min_scan_dist < DRONE_REVEAL_RADIUS:
                continue
            d = abs(gx - x) + abs(gy - y)
            if d < best_dist:
                best_dist = d
                best_target = (gx, gy)

    if best_target and best_dist > 0:
        hint = direction_hint(best_target[0] - x, best_target[1] - y)
        tasks.append(
            f"Fly to unscanned area at ({best_target[0]},{best_target[1]}) — {hint}, {best_dist} tiles"
        )

    if not tasks:
        tasks.append("All areas scanned — patrol for new readings")

    agent["tasks"] = tasks


def _update_rover_tasks(agent_id, agent):
    """Recompute short-term tasks for a rover based on current world state."""
    x, y = agent["position"]
    inventory = agent.get("inventory", [])
    revealed_set = {tuple(c) for c in agent.get("revealed", [])}
    tasks = []

    inv_count = len(inventory)

    # Vein at current tile → analyze or dig (priority order)
    stone_here = _find_stone_at(x, y)
    if stone_here:
        if not stone_here.get("analyzed"):
            tasks.append(f"Analyze unknown vein at current tile ({x},{y})")
        elif inv_count < MAX_INVENTORY_ROVER:
            tasks.append(
                f"Dig {stone_here['grade']} vein (qty={stone_here['quantity']}) at current tile ({x},{y})"
            )

    # Known veins on revealed tiles → navigate to best one
    # Prefer: unknown veins (might be high-grade) first, then by grade (higher = better), then distance
    known_stones = []
    for stone in WORLD.get("stones", []):
        sp = tuple(stone["position"])
        if sp in revealed_set:
            dist = abs(sp[0] - x) + abs(sp[1] - y)
            if stone["type"] == "unknown":
                # Unknown veins get top priority (might be high-grade)
                priority = 0
            else:
                # Analyzed veins: prioritize higher grades (lower priority number = better)
                grade = stone.get("grade", "low")
                grade_idx = VEIN_GRADES.index(grade) if grade in VEIN_GRADES else 0
                # Invert: pristine(4) → priority 1, low(0) → priority 5
                priority = len(VEIN_GRADES) - grade_idx
            known_stones.append((priority, dist, stone))
    known_stones.sort(key=lambda t: (t[0], t[1]))

    if known_stones:
        _priority, dist, stone = known_stones[0]
        sx, sy = stone["position"]
        hint = direction_hint(sx - x, sy - y)
        if stone["type"] == "unknown":
            label = "unknown vein"
        else:
            label = f"{stone.get('grade', '?')} vein (qty={stone.get('quantity', 0)})"
        tasks.append(f"Navigate to {label} at ({sx},{sy}) — {hint}, {dist} tiles")

    # Check drone scan hotspots — navigate toward high-concentration areas
    if not tasks:
        best_hotspot = best_drone_hotspot(x, y, revealed_set)
        if best_hotspot:
            hx, hy, conc = best_hotspot
            hint = direction_hint(hx - x, hy - y)
            dist = abs(hx - x) + abs(hy - y)
            tasks.append(
                f"Navigate to drone-scanned hotspot at ({hx},{hy}) — {hint}, {dist} tiles, concentration={conc:.2f}"
            )

    # Adjacent structures → investigate or use
    for structure in WORLD.get("structures", []):
        sp = tuple(structure["position"])
        dist = abs(sp[0] - x) + abs(sp[1] - y)
        if dist <= 1:
            label = structure["type"].replace("_", " ").title()
            if not structure.get("explored"):
                tasks.append(f"Investigate {label} at ({sp[0]},{sp[1]})")
            elif structure["type"] == "refinery" and structure.get("active"):
                basalt_in_inv = any(
                    i.get("type") == "basalt_vein" and not i.get("refined") for i in inventory
                )
                if basalt_in_inv:
                    tasks.append(f"Use Refinery at ({sp[0]},{sp[1]}) to refine basalt")

    # Visible unexplored structures on revealed tiles — suggest navigation
    for structure in WORLD.get("structures", []):
        sp = tuple(structure["position"])
        if sp in revealed_set and not structure.get("explored"):
            dist = abs(sp[0] - x) + abs(sp[1] - y)
            if dist > 1:
                hint = direction_hint(sp[0] - x, sp[1] - y)
                label = structure["type"].replace("_", " ").title()
                tasks.append(f"Navigate to {label} at ({sp[0]},{sp[1]}) — {hint}, {dist} tiles")

    if not tasks:
        tasks.append("Explore unvisited tiles to find veins")

    agent["tasks"] = tasks


def best_drone_hotspot(rx, ry, revealed_set):
    """Find the highest-concentration unvisited cell from drone scans."""
    best = None
    best_conc = 0.15  # minimum threshold to consider
    for scan in WORLD.get("drone_scans", []):
        for key, conc in scan.get("readings", {}).items():
            cx, cy = map(int, key.split(","))
            if (cx, cy) in revealed_set:
                continue  # rover already sees this area
            if conc > best_conc:
                best_conc = conc
                best = (cx, cy, conc)
    return best


def assign_mission(agent_id, objective):
    """Set a new mission objective for the given agent."""
    agent = WORLD["agents"].get(agent_id)
    if agent is None:
        return {"ok": False, "error": f"Unknown agent: {agent_id}"}
    agent["mission"]["objective"] = objective
    logger.info("Mission assigned to %s: %s", agent_id, objective)
    return {"ok": True, "agent_id": agent_id, "objective": objective}


def observe_rover(agent_id):
    """Build typed RoverContext for a rover agent. Everything the rover can see/know."""
    agent = WORLD["agents"][agent_id]
    x, y = agent["position"]

    # Station position
    station_agent = WORLD["agents"].get("station")
    station_pos = station_agent["position"] if station_agent else [0, 0]

    # Unvisited neighbors
    visited_set = {tuple(p) for p in agent.get("visited", [])}
    unvisited_dirs = []
    for name, (dx, dy) in DIRECTIONS.items():
        nx, ny = x + dx, y + dy
        if 0 <= nx < GRID_W and 0 <= ny < GRID_H and (nx, ny) not in visited_set:
            unvisited_dirs.append(name)

    # Vein at current tile
    ground = check_ground(agent_id)
    stone_info = ground["stone"]
    if stone_info:
        if stone_info["type"] == "unknown":
            stone_line = "unknown vein (needs analyze to reveal grade and quantity)"
        else:
            stone_line = (
                f"{stone_info['grade']} vein, qty={stone_info['quantity']} (analyzed — needs dig)"
            )
    else:
        stone_line = "none"

    # Raw stone object — convert to StoneInfo or None (strip hidden fields)
    raw_stone = _find_stone_at(x, y)
    if raw_stone:
        stone_here = StoneInfo(
            position=raw_stone["position"],
            type=raw_stone["type"],
            grade=raw_stone.get("grade", "unknown"),
            quantity=raw_stone.get("quantity", 0),
            analyzed=raw_stone.get("analyzed", False),
        )
    else:
        stone_here = None

    # Visible veins on revealed tiles (not at current position)
    revealed_set = {tuple(c) for c in agent.get("revealed", [])}
    visible_stones = []
    for stone in WORLD.get("stones", []):
        sp = tuple(stone["position"])
        if sp in revealed_set and list(sp) != [x, y]:
            dist = abs(sp[0] - x) + abs(sp[1] - y)
            status = "analyzed" if stone.get("analyzed") else "unknown"
            hint = direction_hint(sp[0] - x, sp[1] - y)
            grade_info = stone.get("grade", "unknown")
            qty_info = stone.get("quantity", 0)
            label = (
                f"{stone['type']} {grade_info}" if stone["type"] != "unknown" else "unknown vein"
            )
            if qty_info > 0:
                label += f" qty={qty_info}"
            visible_stones.append(f"{label} ({status}) at ({sp[0]},{sp[1]}) — {hint}, {dist} tiles")

    # Visible structures on revealed tiles
    visible_structures = []
    for structure in WORLD.get("structures", []):
        sp = tuple(structure["position"])
        if sp in revealed_set:
            dist = abs(sp[0] - x) + abs(sp[1] - y)
            hint = direction_hint(sp[0] - x, sp[1] - y)
            status = "explored" if structure.get("explored") else "unexplored"
            label = structure["type"].replace("_", " ").title()
            visible_structures.append(
                f"{label} ({status}) at ({sp[0]},{sp[1]}) — {hint}, {dist} tiles"
            )

    # Mission info
    world_mission = WORLD.get("mission", {})

    # Nearby obstacles on revealed tiles
    _ensure_obstacle_index()
    nearby_obstacles = []
    for obs in WORLD.get("obstacles", []):
        op = tuple(obs["position"])
        if op in revealed_set:
            dist = abs(op[0] - x) + abs(op[1] - y)
            if dist <= ROVER_REVEAL_RADIUS * 2:
                nearby_obstacles.append(
                    ObstacleInfo(
                        position=list(obs["position"]),
                        kind=obs["kind"],
                        state=obs.get("state", "idle"),
                    )
                )

    return RoverContext(
        agent=RoverAgentState(
            position=list(agent["position"]),
            battery=agent["battery"],
            mission=AgentMission(**agent["mission"]),
            inventory=[InventoryItem(**i) for i in agent.get("inventory", [])],
            memory=list(agent.get("memory", [])),
            tasks=list(agent.get("tasks", [])),
            visited=list(agent.get("visited", [])),
            visited_count=len(agent.get("visited", [])),
        ),
        world=RoverWorldView(
            grid_w=GRID_W,
            grid_h=GRID_H,
            station_position=list(station_pos),
            target_type=world_mission.get("target_type", "basalt_vein"),
            target_quantity=world_mission.get("target_quantity", TARGET_QUANTITY),
            collected_quantity=world_mission.get("collected_quantity", 0),
        ),
        computed=RoverComputed(
            unvisited_dirs=unvisited_dirs,
            stone_line=stone_line,
            stone_here=stone_here,
            visible_stones=visible_stones,
            visible_structures=visible_structures,
            nearby_obstacles=nearby_obstacles,
        ),
    )


def observe_station():
    """Build typed StationContext for the station agent. Summaries of all rovers + stones."""
    rovers = []
    for aid, agent in WORLD["agents"].items():
        if agent["type"] == "station":
            continue
        rovers.append(
            RoverSummary(
                id=aid,
                agent_type=agent.get("type", "rover"),
                position=list(agent["position"]),
                battery=agent["battery"],
                mission=AgentMission(**agent["mission"]),
                visited_count=len(agent.get("visited", [])),
            )
        )

    stones = []
    for s in WORLD.get("stones", []):
        stones.append(
            StoneInfo(
                type=s["type"],
                position=list(s["position"]),
                grade=s.get("grade", "unknown"),
                quantity=s.get("quantity", 0),
            )
        )

    station_agent = WORLD["agents"].get("station", {})
    mission = WORLD.get("mission", {})
    return StationContext(
        grid_w=GRID_W,
        grid_h=GRID_H,
        rovers=rovers,
        stones=stones,
        memory=station_agent.get("memory", []),
        tick=WORLD.get("tick", 0),
        mission_status=mission.get("status", "in_progress"),
        collected_quantity=mission.get("collected_quantity", 0),
        target_quantity=mission.get("target_quantity", TARGET_QUANTITY),
    )


def _ensure_agent_tools():
    """Lazily populate agent tool lists from the canonical LLM schemas in agent.py."""
    for name, agent in WORLD["agents"].items():
        if agent.get("tools") is None:
            if agent.get("type") == "drone":
                agent["tools"] = _drone_tools_for_ui()
            elif agent.get("type") == "rover":
                agent["tools"] = _rover_tools_for_ui()


def get_snapshot():
    """Return a deep copy of the current world state, filtered by fog-of-war."""
    _ensure_agent_tools()
    snap = copy.deepcopy(WORLD)
    # Remove internal chunk data
    snap.pop("chunks", None)
    # Build union of all agents' revealed cells
    revealed = set()
    for agent in snap["agents"].values():
        for cell in agent.get("revealed", []):
            revealed.add(tuple(cell))
    # Filter stones to only those on revealed cells and strip hidden internal fields
    visible = []
    for s in snap["stones"]:
        if tuple(s["position"]) in revealed:
            s.pop("_true_type", None)
            s.pop("_true_grade", None)
            s.pop("_true_quantity", None)
            visible.append(s)
    snap["stones"] = visible
    # Filter structures to only those on revealed cells
    visible_structures = []
    for s in snap.get("structures", []):
        if tuple(s["position"]) in revealed:
            visible_structures.append(s)
    snap["structures"] = visible_structures
    # Filter obstacles by fog-of-war (same revealed set)
    visible_obstacles = []
    for o in snap.get("obstacles", []):
        if tuple(o["position"]) in revealed:
            cleaned = {k: v for k, v in o.items() if not k.startswith("_")}
            visible_obstacles.append(cleaned)
    snap["obstacles"] = visible_obstacles
    # Include agent messages for UI visibility
    snap["agent_messages"] = copy.deepcopy(AGENT_MESSAGES)
    # Ensure bounds are present
    if "bounds" not in snap:
        snap["bounds"] = {"min_x": 0, "max_x": GRID_W - 1, "min_y": 0, "max_y": GRID_H - 1}
    # Add storm info for UI
    snap["storm"] = storm_mod.get_storm_info(WORLD)
    return snap


def check_storm_tick():
    """Advance storm lifecycle on the global WORLD. Returns list of event dicts."""
    return storm_mod.check_storm_tick(WORLD)


def get_storm_info():
    """Return current storm info from the global WORLD."""
    return storm_mod.get_storm_info(WORLD)
