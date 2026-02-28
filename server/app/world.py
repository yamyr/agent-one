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
BATTERY_COST_MOVE_DRONE = 1 / FUEL_CAPACITY_DRONE  # 0.004 per tile
BATTERY_COST_DIG = 6 / FUEL_CAPACITY_ROVER  # 6 fuel units
BATTERY_COST_PICKUP = 2 / FUEL_CAPACITY_ROVER  # 2 fuel units
BATTERY_COST_ANALYZE = 3 / FUEL_CAPACITY_ROVER  # 3 fuel units
BATTERY_COST_ANALYZE_GROUND = 3 / FUEL_CAPACITY_ROVER  # 3 fuel units
BATTERY_COST_SCAN = 2 / FUEL_CAPACITY_DRONE  # 2 fuel units
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
TARGET_QUANTITY = 100  # mission success threshold (total basalt delivered)

ROVER_REVEAL_RADIUS = 3
DRONE_REVEAL_RADIUS = 6
REVEAL_RADIUS = ROVER_REVEAL_RADIUS  # legacy alias
MEMORY_MAX = 8

# --- Return-to-base policy ---
# Agents return when battery <= RETURN_TO_BASE_THRESHOLD (67% capacity).
# As an additional safety net, they also return if the remaining battery
# is barely enough to cover the distance back + a small safety margin.
RETURN_TO_BASE_THRESHOLD = 0.67  # return when battery drops to 67%
BATTERY_SAFETY_MARGIN = 0.06  # extra margin above distance-based cost

# --- Solar panels ---
SOLAR_BATTERY_CAPACITY = 0.25
MAX_SOLAR_PANELS = 2

# --- Stone generation ---
STONE_PROBABILITY = 0.015
CORE_PROBABILITY = 0.3


def _battery_to_reach_station(agent):
    """Calculate battery cost needed to return to station from current position."""
    station = WORLD.get("agents", {}).get("station")
    sp = station["position"] if station else [0, 0]
    x, y = agent["position"]
    dist = abs(x - sp[0]) + abs(y - sp[1])
    cost_per_tile = BATTERY_COST_MOVE_DRONE if agent.get("type") == "drone" else BATTERY_COST_MOVE
    return dist * cost_per_tile


def must_return_to_base(agent):
    """Check if agent must immediately return to base to avoid stranding.

    Returns True if:
      1. Battery is at or below RETURN_TO_BASE_THRESHOLD (67%), OR
      2. Battery is at or below the cost to reach station + safety margin.
    """
    if agent.get("type") == "station":
        return False
    station = WORLD.get("agents", {}).get("station")
    if station and agent["position"] == station["position"]:
        return False  # already at station
    # Dual check: flat threshold OR distance-based safety net
    if agent["battery"] <= RETURN_TO_BASE_THRESHOLD:
        return True
    cost = _battery_to_reach_station(agent)
    return agent["battery"] <= cost + BATTERY_SAFETY_MARGIN


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
                        "extracted": False,
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
                "extracted": False,
                "analyzed": False,
            }
        )

    # Register stones in the global list
    WORLD.setdefault("stones", []).extend(stones)

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


_ROVER_TOOL_DEFS = [
    {
        "name": "move",
        "description": "Move 1-3 tiles in a cardinal direction (north/south/east/west). Costs 1 fuel unit per tile (~0.29% battery). Ground is auto-scanned after each move.",
    },
    {
        "name": "analyze",
        "description": "Analyze an unknown vein at current tile to reveal its grade (low/medium/high/rich/pristine) and basalt quantity. Costs 3 fuel units (~0.86% battery).",
    },
    {
        "name": "dig",
        "description": "Dig at current tile to extract a vein. Costs 6 fuel units (~1.71% battery). Vein must be analyzed first.",
    },
    {
        "name": "pickup",
        "description": "Pick up an extracted vein at current tile into inventory (with its basalt quantity). Costs 2 fuel units (~0.57% battery).",
    },
    {
        "name": "analyze_ground",
        "description": "Analyze ground concentration at current tile to detect nearby basalt vein deposits. Costs 3 fuel units (~0.86% battery). Returns a 0.0-1.0 reading.",
    },
]


_DRONE_TOOL_DEFS = [
    {
        "name": "move",
        "description": "Fly 1-6 tiles in a cardinal direction (north/south/east/west). Costs 1 fuel unit per tile (~0.4% battery).",
    },
    {
        "name": "scan",
        "description": "Scan the area below and around the drone to sample concentration readings. Returns probability values for surrounding tiles indicating likelihood of precious stone deposits. Costs 2 fuel units (~0.8% battery).",
    },
]


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
        "ground_readings": {},
        "tools": list(_DRONE_TOOL_DEFS),
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
        "ground_readings": {},
        "tools": list(_ROVER_TOOL_DEFS),
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
            },
            "rover-mistral": _make_rover(0, 0),
            "drone-mistral": _make_drone(0, 0),
        },
        "stones": [],
        "chunks": {},
        "concentration_map": {},
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


WORLD = _build_initial_world()
_init_world_chunks()


def reset_world():
    """Reset WORLD to initial state. Re-seeds RNG if world_seed is set."""
    fresh = _build_initial_world()
    WORLD.clear()
    WORLD.update(fresh)
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
    for stone in WORLD.get("stones", []):
        if stone["position"] == [x, y]:
            return {
                "stone": {
                    "type": stone["type"],
                    "grade": stone.get("grade", "unknown"),
                    "quantity": stone.get("quantity", 0),
                    "extracted": stone.get("extracted", False),
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
    elif action_name == "analyze_ground":
        result = _execute_analyze_ground(agent_id, agent)
        if result["ok"]:
            record_memory(
                agent_id,
                f"Ground concentration at ({result['position'][0]},{result['position'][1]}): {result['concentration']:.3f}",
            )
    elif action_name == "dig":
        if is_drone:
            return {"ok": False, "error": "Drones cannot dig"}
        result = _execute_dig(agent_id, agent)
        if result["ok"]:
            record_memory(
                agent_id,
                f"Dug out {result['stone']['grade']} vein at ({result['position'][0]},{result['position'][1]}), qty={result['stone']['quantity']}",
            )
    elif action_name == "pickup":
        if is_drone:
            return {"ok": False, "error": "Drones cannot pick up veins"}
        result = _execute_pickup(agent_id, agent)
        if result["ok"]:
            record_memory(
                agent_id,
                f"Picked up {result['stone']['grade']} vein (qty={result['stone']['quantity']}) at ({result['position'][0]},{result['position'][1]}), inventory={result['inventory_count']}",
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
    else:
        return {"ok": False, "error": f"Unknown action: {action_name}"}

    if not result["ok"]:
        record_memory(agent_id, f"Failed {action_name}: {result.get('error', '?')}")

    if result["ok"]:
        mission_event = check_mission_status()
        if mission_event:
            result["mission"] = mission_event

    update_tasks(agent_id)
    return result


def _find_stone_at(x, y):
    """Find a stone at the given position, or None."""
    for stone in WORLD.get("stones", []):
        if stone["position"] == [x, y]:
            return stone
    return None


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


def _execute_analyze_ground(agent_id, agent):
    """Analyze ground concentration at current tile to detect nearby core deposits."""
    if agent["battery"] < BATTERY_COST_ANALYZE_GROUND:
        return {"ok": False, "error": "Not enough battery to analyze ground"}

    x, y = agent["position"]
    agent["battery"] = max(0.0, agent["battery"] - BATTERY_COST_ANALYZE_GROUND)
    concentration = get_concentration(x, y)
    readings = agent.setdefault("ground_readings", {})
    readings[f"{x},{y}"] = concentration
    logger.info(
        "Agent %s analyzed ground at (%d,%d), concentration=%.2f", agent_id, x, y, concentration
    )
    return {"ok": True, "position": [x, y], "concentration": round(concentration, 3)}


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
    """Dig at current tile to extract a buried vein."""
    if agent["battery"] < BATTERY_COST_DIG:
        return {"ok": False, "error": "Not enough battery to dig"}

    x, y = agent["position"]
    stone = _find_stone_at(x, y)
    if stone is None:
        return {"ok": False, "error": f"No vein at ({x}, {y})"}
    if not stone.get("analyzed"):
        return {"ok": False, "error": "Vein not yet analyzed (analyze first)"}
    if stone.get("extracted"):
        return {"ok": False, "error": f"Vein at ({x}, {y}) already extracted"}

    agent["battery"] = max(0.0, agent["battery"] - BATTERY_COST_DIG)
    stone["extracted"] = True
    logger.info(
        "Agent %s dug at (%d,%d), extracted %s grade=%s qty=%d",
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


def _execute_pickup(agent_id, agent):
    """Pick up an extracted vein into the agent's inventory."""
    if agent["battery"] < BATTERY_COST_PICKUP:
        return {"ok": False, "error": "Not enough battery to pick up"}

    x, y = agent["position"]
    stone = _find_stone_at(x, y)
    if stone is None:
        return {"ok": False, "error": f"No vein at ({x}, {y})"}
    if not stone.get("analyzed"):
        return {"ok": False, "error": "Vein not yet analyzed (analyze first)"}
    if not stone.get("extracted"):
        return {"ok": False, "error": f"Vein at ({x}, {y}) not yet extracted (dig first)"}

    agent["battery"] = max(0.0, agent["battery"] - BATTERY_COST_PICKUP)
    agent.setdefault("inventory", []).append(
        {
            "type": stone["type"],
            "grade": stone["grade"],
            "quantity": stone["quantity"],
        }
    )
    WORLD["stones"].remove(stone)
    logger.info(
        "Agent %s picked up %s grade=%s qty=%d at (%d,%d)",
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
    return {"ok": True, "battery_before": old_battery, "battery_after": agent["battery"]}


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
    mission["collected_quantity"] = collected_qty

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


def _direction_hint(dx, dy):
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


def update_tasks(agent_id):
    """Recompute short-term tasks for an agent based on current world state."""
    agent = WORLD["agents"].get(agent_id)
    if agent is None:
        return
    # Mission aborted — only task is return to station
    if WORLD["mission"]["status"] == "aborted":
        station = WORLD["agents"].get("station")
        sp = station["position"] if station else [0, 0]
        x, y = agent["position"]
        if [x, y] == sp:
            agent["tasks"] = ["At station — mission aborted, standing by"]
        else:
            dist = abs(sp[0] - x) + abs(sp[1] - y)
            hint = _direction_hint(sp[0] - x, sp[1] - y)
            agent["tasks"] = [
                f"MISSION ABORTED — return to station at ({sp[0]},{sp[1]}) — {hint}, {dist} tiles"
            ]
        return
    if agent.get("type") == "drone":
        _update_drone_tasks(agent_id, agent)
    else:
        _update_rover_tasks(agent_id, agent)


def _update_drone_tasks(agent_id, agent):
    """Recompute tasks for a drone — scan unscanned areas, explore the map."""
    x, y = agent["position"]
    _ = {tuple(c) for c in agent.get("visited", [])}  # reserved for future use
    tasks = []

    # CRITICAL: battery safety — must return to base if battery is low
    if must_return_to_base(agent):
        station = WORLD["agents"].get("station")
        sp = station["position"] if station else [0, 0]
        if [x, y] != [sp[0], sp[1]]:
            cost = _battery_to_reach_station(agent)
            tasks.append(
                f"⚠️ LOW BATTERY ({agent['battery']:.0%}) — RETURN TO STATION at ({sp[0]},{sp[1]}) immediately! "
                f"Need {cost:.0%} to get back."
            )
            agent["tasks"] = tasks
            return

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
        hint = _direction_hint(best_target[0] - x, best_target[1] - y)
        tasks.append(
            f"Fly to unscanned area at ({best_target[0]},{best_target[1]}) — {hint}, {best_dist} tiles"
        )

    if not tasks:
        tasks.append("All areas scanned — patrol for new readings")

    agent["tasks"] = tasks


def _update_rover_tasks(agent_id, agent):
    """Recompute short-term tasks for a rover based on current world state."""
    x, y = agent["position"]
    mission = WORLD["mission"]
    target_type = mission["target_type"]
    inventory = agent.get("inventory", [])
    revealed_set = {tuple(c) for c in agent.get("revealed", [])}
    tasks = []

    # CRITICAL: battery safety — must return to base if battery is low
    if must_return_to_base(agent):
        station = WORLD["agents"].get("station")
        sp = station["position"] if station else [0, 0]
        if [x, y] != sp:
            cost = _battery_to_reach_station(agent)
            nearby_panel = _nearest_solar_panel(x, y)
            if nearby_panel:
                pp = nearby_panel["position"]
                pd = abs(pp[0] - x) + abs(pp[1] - y)
                tasks.append(
                    f"⚠️ LOW BATTERY ({agent['battery']:.0%}) — Solar panel at ({pp[0]},{pp[1]}) is {pd} tiles away, "
                    f"or RETURN TO STATION at ({sp[0]},{sp[1]}). Need {cost:.0%} to get back."
                )
            else:
                tasks.append(
                    f"⚠️ LOW BATTERY ({agent['battery']:.0%}) — RETURN TO STATION at ({sp[0]},{sp[1]}) immediately! "
                    f"Need {cost:.0%} to get back."
                )
            agent["tasks"] = tasks
            return

    # Mission fulfillment check — return to station when target met or carrying basalt
    inv_qty = sum(s.get("quantity", 0) for s in inventory if s["type"] == target_type)
    collected_qty = mission.get("collected_quantity", 0)
    target_qty = mission["target_quantity"]
    has_basalt = any(s["type"] == target_type for s in inventory)
    mission_met = (collected_qty + inv_qty) >= target_qty
    if has_basalt or mission_met:
        station = WORLD["agents"].get("station")
        sp = station["position"] if station else [0, 0]
        if [x, y] == sp:
            if inv_qty > 0:
                tasks.append(
                    f"🏁 Deliver basalt at station ({inv_qty} units, mission needs {target_qty})"
                )
            else:
                tasks.append("🏁 Mission target reached! Standby at station.")
        else:
            if mission_met:
                tasks.append(
                    f"🏁 Mission fulfilled! Return to station at ({sp[0]},{sp[1]}) to deliver {inv_qty} units of basalt IMMEDIATELY"
                )
            else:
                tasks.append(
                    f"Return to station at ({sp[0]},{sp[1]}) to deliver {inv_qty} units of basalt"
                )
        agent["tasks"] = tasks
        return

    # Vein at current tile → analyze, dig, or pickup (priority order)
    stone_here = _find_stone_at(x, y)
    if stone_here:
        if not stone_here.get("analyzed"):
            tasks.append(f"Analyze unknown vein at current tile ({x},{y})")
        elif not stone_here.get("extracted"):
            tasks.append(
                f"Dig {stone_here['grade']} vein (qty={stone_here['quantity']}) at current tile ({x},{y})"
            )
        else:
            tasks.append(
                f"Pick up {stone_here['grade']} vein (qty={stone_here['quantity']}) at current tile ({x},{y})"
            )
        agent["tasks"] = tasks
        return

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
        hint = _direction_hint(sx - x, sy - y)
        if stone["type"] == "unknown":
            label = "unknown vein"
        else:
            label = f"{stone.get('grade', '?')} vein (qty={stone.get('quantity', 0)})"
        tasks.append(f"Navigate to {label} at ({sx},{sy}) — {hint}, {dist} tiles")

    # Check drone scan hotspots — navigate toward high-concentration areas
    if not tasks:
        best_hotspot = _best_drone_hotspot(x, y, revealed_set)
        if best_hotspot:
            hx, hy, conc = best_hotspot
            hint = _direction_hint(hx - x, hy - y)
            dist = abs(hx - x) + abs(hy - y)
            tasks.append(
                f"Navigate to drone-scanned hotspot at ({hx},{hy}) — {hint}, {dist} tiles, concentration={conc:.2f}"
            )

    if not tasks:
        tasks.append("Explore unvisited tiles to find veins")

    agent["tasks"] = tasks


def _best_drone_hotspot(rx, ry, revealed_set):
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
        elif stone_info["extracted"]:
            stone_line = f"{stone_info['grade']} vein, qty={stone_info['quantity']} (extracted — ready for pickup)"
        else:
            stone_line = f"{stone_info['grade']} vein, qty={stone_info['quantity']} (analyzed, buried — needs dig)"
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
            extracted=raw_stone.get("extracted", False),
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
            status = "extracted" if stone.get("extracted") else "buried"
            hint = _direction_hint(sp[0] - x, sp[1] - y)
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
            ground_readings=dict(agent.get("ground_readings", {})),
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

    return StationContext(
        grid_w=GRID_W,
        grid_h=GRID_H,
        rovers=rovers,
        stones=stones,
    )


def get_snapshot():
    """Return a deep copy of the current world state, filtered by fog-of-war."""
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
    # Serialize concentration_map tuple keys to JSON-safe "x,y" strings
    conc = snap.get("concentration_map")
    if conc and isinstance(conc, dict):
        snap["concentration_map"] = {f"{k[0]},{k[1]}": v for k, v in conc.items()}
    # Ensure bounds are present
    if "bounds" not in snap:
        snap["bounds"] = {"min_x": 0, "max_x": GRID_W - 1, "min_y": 0, "max_y": GRID_H - 1}
    return snap
