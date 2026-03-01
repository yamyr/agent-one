"""In-memory world state for the Mars simulation."""

import copy
import hashlib
import logging
import random

from .config import settings
from .models import RoverAgentState, RoverWorldView, RoverComputed, RoverContext
from .models import AgentMission, InventoryItem, StoneInfo
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


def _random_free_pos(occupied, rng=None, cx=0, cy=0):
    """Pick a random position within a chunk area not in `occupied`."""
    r = rng or random
    x0, y0 = cx * CHUNK_SIZE, cy * CHUNK_SIZE
    while True:
        x = r.randint(x0, x0 + CHUNK_SIZE - 1)
        y = r.randint(y0, y0 + CHUNK_SIZE - 1)
        if (x, y) not in occupied:
            return x, y


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

    chunk_data = {"generated": True, "stone_count": len(stones)}
    chunks[key] = chunk_data
    logger.info("Generated chunk (%d,%d) with %d stones", cx, cy, len(stones))
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
        "chunks": {},
        "solar_panels": [],
        "drone_scans": [],
        "tick": 0,
        "bounds": {"min_x": -3, "max_x": 3, "min_y": -3, "max_y": 3},
        "mission": {
            "status": "running",
            "target_type": "basalt_vein",
            "target_quantity": TARGET_QUANTITY,
            "collected_quantity": 0,
        },
    }
    return world


def _init_world_chunks():
    """Generate starting chunks around origin after WORLD is initialized."""
    # Generate the origin chunk and immediate neighbors
    for cx in range(-1, 2):
        for cy in range(-1, 2):
            _ensure_chunk(cx, cy)


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


WORLD = _build_initial_world()
_init_world_chunks()


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


# Module-level singleton wrapping the global WORLD dict
world = World(WORLD)


def reset_world():
    """Reset WORLD to initial state. Re-seeds RNG if world_seed is set."""
    fresh = _build_initial_world()
    WORLD.clear()
    WORLD.update(fresh)
    _stone_index.clear()
    global _stone_index_source
    _stone_index_source = None
    _init_world_chunks()
    logger.info("World reset")


def next_tick():
    """Increment and return the current tick number."""
    WORLD["tick"] += 1
    return WORLD["tick"]


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

    # Ensure chunk exists at destination
    _ensure_chunk(*_chunk_key(x, y))
    _update_bounds(x, y)

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
        max_dist = MAX_MOVE_DISTANCE_DRONE if is_drone else MAX_MOVE_DISTANCE
        move_cost = BATTERY_COST_MOVE_DRONE if is_drone else BATTERY_COST_MOVE
        distance = max(1, min(max_dist, int(params.get("distance", 1))))

        cost = move_cost * distance
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
            agent["battery"] = max(0.0, agent["battery"] - move_cost * distance)
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
    if agent["battery"] < BATTERY_COST_ANALYZE:
        return {"ok": False, "error": "Not enough battery to analyze"}

    x, y = agent["position"]
    stone = _find_stone_at(x, y)
    if stone is None:
        return {"ok": False, "error": f"No vein at ({x}, {y})"}
    if stone.get("analyzed"):
        return {"ok": False, "error": f"Vein at ({x}, {y}) already analyzed"}

    agent["battery"] = max(0.0, agent["battery"] - BATTERY_COST_ANALYZE)
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
    if agent["battery"] < BATTERY_COST_SCAN:
        return {"ok": False, "error": "Not enough battery to scan"}

    x, y = agent["position"]
    agent["battery"] = max(0.0, agent["battery"] - BATTERY_COST_SCAN)
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
    if agent["battery"] < BATTERY_COST_DIG:
        return {"ok": False, "error": "Not enough battery to dig"}

    x, y = agent["position"]
    stone = _find_stone_at(x, y)
    if stone is None:
        return {"ok": False, "error": f"No vein at ({x}, {y})"}
    if not stone.get("analyzed"):
        return {"ok": False, "error": "Vein not yet analyzed (analyze first)"}

    agent["battery"] = max(0.0, agent["battery"] - BATTERY_COST_DIG)
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
    if agent["battery"] < BATTERY_COST_NOTIFY:
        return {"ok": False, "error": "Not enough battery to notify"}
    message = params.get("message", "")
    if not message:
        return {"ok": False, "error": "Empty message"}
    agent["battery"] = max(0.0, agent["battery"] - BATTERY_COST_NOTIFY)
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

    # Mission info
    world_mission = WORLD.get("mission", {})

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
    return StationContext(
        grid_w=GRID_W,
        grid_h=GRID_H,
        rovers=rovers,
        stones=stones,
        memory=station_agent.get("memory", []),
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
    # Ensure bounds are present
    if "bounds" not in snap:
        snap["bounds"] = {"min_x": 0, "max_x": GRID_W - 1, "min_y": 0, "max_y": GRID_H - 1}
    return snap
