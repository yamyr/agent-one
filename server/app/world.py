"""In-memory world state for the Mars simulation."""

import copy
import hashlib
import logging
import math
import random
import struct

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
STONE_TYPES = ["core", "basalt"]
ROVER_REVEAL_RADIUS = 3
DRONE_REVEAL_RADIUS = 6
REVEAL_RADIUS = ROVER_REVEAL_RADIUS  # legacy alias
TARGET_STONE_TYPE = "core"
TARGET_STONE_COUNT = 1
MEMORY_MAX = 8

# --- Return-to-base policy ---
# Agents return when battery <= RETURN_TO_BASE_THRESHOLD (67% capacity).
# As an additional safety net, they also return if the remaining battery
# is barely enough to cover the distance back + a small safety margin.
RETURN_TO_BASE_THRESHOLD = 0.67  # return when battery drops to 67%
BATTERY_SAFETY_MARGIN = 0.06  # extra margin above distance-based cost


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

    # Concentration: seeded hash-based pseudo-noise
    conc = {}
    for dy in range(CHUNK_SIZE):
        for dx in range(CHUNK_SIZE):
            wx, wy = x0 + dx, y0 + dy
            conc[(wx, wy)] = _noise_concentration(wx, wy)

    # Stones: origin chunk guaranteed ≥1 core, others 0-2 stones
    stones = []
    is_origin = cx == 0 and cy == 0
    occupied = set(AGENT_STARTS) if is_origin else set()
    num_stones = rng.randint(1, 3) if is_origin else rng.randint(0, 2)

    for i in range(num_stones):
        is_core = (i == 0 and is_origin) or rng.random() < 0.3
        sx, sy = _random_free_pos(occupied, rng, cx, cy)
        occupied.add((sx, sy))
        stones.append(
            {
                "position": [sx, sy],
                "type": "unknown",
                "_true_type": "core" if is_core else "basalt",
                "extracted": False,
                "analyzed": False,
            }
        )

    # Register stones in the global list
    WORLD.setdefault("stones", []).extend(stones)
    # Merge concentration into global map
    WORLD.setdefault("concentration_map", {}).update(conc)

    chunk_data = {"generated": True, "stone_count": len(stones)}
    chunks[key] = chunk_data
    logger.info("Generated chunk (%d,%d) with %d stones", cx, cy, len(stones))
    return chunk_data


def _noise_concentration(x, y):
    """Deterministic noise value 0.0-1.0 for world tile (x, y).

    Uses layered hash-based noise at multiple frequencies to create
    natural-looking concentration fields. Core stones later boost
    nearby values via _boost_concentration_near_cores().
    """
    base_seed = settings.world_seed or 42
    val = 0.0
    amp = 1.0
    total_amp = 0.0
    for octave in range(3):
        freq = 1 << octave  # 1, 2, 4
        h = hashlib.md5(f"{base_seed}:{x * freq}:{y * freq}:{octave}".encode()).digest()
        n = struct.unpack("<H", h[:2])[0] / 65535.0
        val += n * amp
        total_amp += amp
        amp *= 0.5
    raw = val / total_amp  # 0.0-1.0
    return round(raw * 0.4, 4)  # base noise is low; cores boost it


def _boost_concentration_near_cores():
    """After stones are placed, boost concentration near core positions."""
    sigma = 4.0
    core_positions = []
    for s in WORLD.get("stones", []):
        if s.get("_true_type") == "core":
            core_positions.append(tuple(s["position"]))
    if not core_positions:
        return
    conc = WORLD.setdefault("concentration_map", {})
    boosted = set()
    for px, py in core_positions:
        for dx in range(-8, 9):
            for dy in range(-8, 9):
                cell = (px + dx, py + dy)
                if cell in boosted:
                    continue
                d = abs(dx) + abs(dy)
                boost = math.exp(-(d**2) / (sigma**2))
                if cell in conc:
                    conc[cell] = min(1.0, conc[cell] + boost * 0.6)
                else:
                    conc[cell] = round(boost * 0.6, 4)
                boosted.add(cell)


def get_concentration(x, y):
    """Get concentration at (x, y), generating the chunk if needed."""
    cx, cy = _chunk_key(x, y)
    _ensure_chunk(cx, cy)
    return WORLD.get("concentration_map", {}).get((x, y), 0.0)


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
        "description": "Analyze an unknown stone at current tile to reveal its true type. Costs 3 fuel units (~0.86% battery).",
    },
    {
        "name": "dig",
        "description": "Dig at current tile to extract a stone. Costs 6 fuel units (~1.71% battery). Stone must be analyzed first.",
    },
    {
        "name": "pickup",
        "description": "Pick up an extracted stone at current tile into inventory. Costs 2 fuel units (~0.57% battery).",
    },
    {
        "name": "analyze_ground",
        "description": "Analyze ground concentration at current tile to detect nearby core deposits. Costs 3 fuel units (~0.86% battery). Returns a 0.0-1.0 reading.",
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
            "rover-mock": _make_rover(0, 0),
            "rover-mistral": _make_rover(0, 0),
            "drone-mistral": _make_drone(0, 0),
        },
        "stones": [],
        "chunks": {},
        "concentration_map": {},
        "drone_scans": [],
        "tick": 0,
        "bounds": {"min_x": -3, "max_x": 3, "min_y": -3, "max_y": 3},
        "mission": {
            "status": "running",
            "target_type": TARGET_STONE_TYPE,
            "target_count": TARGET_STONE_COUNT,
            "collected_count": 0,
        },
    }
    return world


def _init_world_chunks():
    """Generate starting chunks around origin after WORLD is initialized."""
    # Generate the origin chunk and immediate neighbors
    for cx in range(-1, 2):
        for cy in range(-1, 2):
            _ensure_chunk(cx, cy)
    _boost_concentration_near_cores()


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
    """Check if a stone is present at the agent's current position."""
    agent = WORLD["agents"].get(agent_id)
    if agent is None:
        return {"stone": None}
    x, y = agent["position"]
    for stone in WORLD.get("stones", []):
        if stone["position"] == [x, y]:
            return {"stone": {"type": stone["type"], "extracted": stone.get("extracted", False)}}
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
            return {"ok": False, "error": "Drones cannot analyze stones"}
        result = _execute_analyze(agent_id, agent)
        if result["ok"]:
            record_memory(
                agent_id,
                f"Analyzed stone at ({result['position'][0]},{result['position'][1]}), type={result['stone']['type']}",
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
                f"Dug out {result['stone']['type']} stone at ({result['position'][0]},{result['position'][1]})",
            )
    elif action_name == "pickup":
        if is_drone:
            return {"ok": False, "error": "Drones cannot pick up stones"}
        result = _execute_pickup(agent_id, agent)
        if result["ok"]:
            record_memory(
                agent_id,
                f"Picked up {result['stone']['type']} stone at ({result['position'][0]},{result['position'][1]}), inventory={result['inventory_count']}",
            )
    elif action_name == "scan":
        result = _execute_scan(agent_id, agent)
        if result["ok"]:
            record_memory(
                agent_id,
                f"Scanned area around ({result['position'][0]},{result['position'][1]}), peak concentration={result['peak']:.3f}",
            )
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
    """Analyze an unknown stone at the current tile to reveal its true type."""
    if agent["battery"] < BATTERY_COST_ANALYZE:
        return {"ok": False, "error": "Not enough battery to analyze"}

    x, y = agent["position"]
    stone = _find_stone_at(x, y)
    if stone is None:
        return {"ok": False, "error": f"No stone at ({x}, {y})"}
    if stone.get("analyzed"):
        return {"ok": False, "error": f"Stone at ({x}, {y}) already analyzed"}

    agent["battery"] = max(0.0, agent["battery"] - BATTERY_COST_ANALYZE)
    stone["analyzed"] = True
    stone["type"] = stone["_true_type"]
    logger.info("Agent %s analyzed stone at (%d,%d), type=%s", agent_id, x, y, stone["type"])
    return {"ok": True, "position": [x, y], "stone": {"type": stone["type"]}}


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
    """Dig at current tile to extract a buried stone."""
    if agent["battery"] < BATTERY_COST_DIG:
        return {"ok": False, "error": "Not enough battery to dig"}

    x, y = agent["position"]
    stone = _find_stone_at(x, y)
    if stone is None:
        return {"ok": False, "error": f"No stone at ({x}, {y})"}
    if not stone.get("analyzed"):
        return {"ok": False, "error": "Stone not yet analyzed (analyze first)"}
    if stone.get("extracted"):
        return {"ok": False, "error": f"Stone at ({x}, {y}) already extracted"}

    agent["battery"] = max(0.0, agent["battery"] - BATTERY_COST_DIG)
    stone["extracted"] = True
    logger.info("Agent %s dug at (%d,%d), extracted %s", agent_id, x, y, stone["type"])
    return {"ok": True, "position": [x, y], "stone": {"type": stone["type"]}}


def _execute_pickup(agent_id, agent):
    """Pick up an extracted stone into the agent's inventory."""
    if agent["battery"] < BATTERY_COST_PICKUP:
        return {"ok": False, "error": "Not enough battery to pick up"}

    x, y = agent["position"]
    stone = _find_stone_at(x, y)
    if stone is None:
        return {"ok": False, "error": f"No stone at ({x}, {y})"}
    if not stone.get("analyzed"):
        return {"ok": False, "error": "Stone not yet analyzed (analyze first)"}
    if not stone.get("extracted"):
        return {"ok": False, "error": f"Stone at ({x}, {y}) not yet extracted (dig first)"}

    agent["battery"] = max(0.0, agent["battery"] - BATTERY_COST_PICKUP)
    agent.setdefault("inventory", []).append({"type": stone["type"]})
    WORLD["stones"].remove(stone)
    logger.info("Agent %s picked up %s at (%d,%d)", agent_id, stone["type"], x, y)
    return {
        "ok": True,
        "position": [x, y],
        "stone": {"type": stone["type"]},
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


def charge_rover(rover_id):
    """Station-initiated charge: recharge a rover that is co-located with the station."""
    agent = WORLD["agents"].get(rover_id)
    if agent is None:
        return {"ok": False, "error": f"Unknown agent: {rover_id}"}
    if agent.get("type") != "rover":
        return {"ok": False, "error": f"{rover_id} is not a rover"}
    result = _execute_charge(rover_id, agent)
    if result["ok"]:
        record_memory(
            rover_id,
            f"Station charged battery {result['battery_before']:.0%} -> {result['battery_after']:.0%}",
        )
    return result


def check_mission_status():
    """Update mission collected_count and detect success/failure.

    Returns a mission event dict if the status changed, or None.
    """
    mission = WORLD["mission"]
    if mission["status"] in ("success", "failed"):
        return None

    # Count target stones across all rover inventories
    station = WORLD["agents"].get("station")
    station_pos = station["position"] if station else [0, 0]
    collected = 0
    delivered = 0
    for agent in WORLD["agents"].values():
        if agent.get("type") != "rover":
            continue
        for stone in agent.get("inventory", []):
            if stone["type"] == mission["target_type"]:
                collected += 1
                if agent["position"] == station_pos:
                    delivered += 1
    mission["collected_count"] = collected

    # Success: enough target stones delivered to station
    if delivered >= mission["target_count"]:
        mission["status"] = "success"
        logger.info(
            "Mission SUCCESS: delivered %d/%d %s stones to station",
            delivered,
            mission["target_count"],
            mission["target_type"],
        )
        return {"status": "success", "collected": collected, "delivered": delivered}

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
            tasks.append(
                f"⚠️ LOW BATTERY ({agent['battery']:.0%}) — RETURN TO STATION at ({sp[0]},{sp[1]}) immediately! "
                f"Need {cost:.0%} to get back."
            )
            agent["tasks"] = tasks
            return

    # Already collected target stone → return to station
    has_target = any(s["type"] == target_type for s in inventory)
    if has_target:
        station = WORLD["agents"].get("station")
        sp = station["position"] if station else [0, 0]
        if [x, y] == sp:
            tasks.append("Deliver stone at station (mission complete)")
        else:
            tasks.append(f"Return to station at ({sp[0]},{sp[1]}) to complete mission")
        agent["tasks"] = tasks
        return

    # Stone at current tile → analyze, dig, or pickup (priority order)
    stone_here = _find_stone_at(x, y)
    if stone_here:
        if not stone_here.get("analyzed"):
            tasks.append(f"Analyze unknown stone at current tile ({x},{y})")
        elif not stone_here.get("extracted"):
            tasks.append(f"Dig {stone_here['type']} stone at current tile ({x},{y})")
        else:
            tasks.append(f"Pick up {stone_here['type']} stone at current tile ({x},{y})")
        agent["tasks"] = tasks
        return

    # Known stones on revealed tiles → navigate to nearest
    # Prefer: unknown stones (potential cores) > known target type > known basalt
    known_stones = []
    for stone in WORLD.get("stones", []):
        sp = tuple(stone["position"])
        if sp in revealed_set:
            dist = abs(sp[0] - x) + abs(sp[1] - y)
            if stone["type"] == "unknown":
                priority = 0
            elif stone["type"] == target_type:
                priority = 1
            else:
                priority = 2
            known_stones.append((priority, dist, stone))
    known_stones.sort(key=lambda t: (t[0], t[1]))

    if known_stones:
        _priority, dist, stone = known_stones[0]
        sx, sy = stone["position"]
        hint = _direction_hint(sx - x, sy - y)
        label = stone["type"] if stone["type"] != "unknown" else "unknown"
        tasks.append(f"Navigate to {label} stone at ({sx},{sy}) — {hint}, {dist} tiles")

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
        tasks.append("Explore unvisited tiles to find stones")

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

    # Stone at current tile
    ground = check_ground(agent_id)
    stone_info = ground["stone"]
    if stone_info:
        if stone_info["type"] == "unknown":
            stone_line = "unknown (needs analyze to reveal type)"
        elif stone_info["extracted"]:
            stone_line = f"{stone_info['type']} (extracted — ready for pickup)"
        else:
            stone_line = f"{stone_info['type']} (analyzed, buried — needs dig)"
    else:
        stone_line = "none"

    # Raw stone object — convert to StoneInfo or None
    raw_stone = _find_stone_at(x, y)
    stone_here = StoneInfo(**raw_stone) if raw_stone else None

    # Visible stones on revealed tiles (not at current position)
    revealed_set = {tuple(c) for c in agent.get("revealed", [])}
    visible_stones = []
    for stone in WORLD.get("stones", []):
        sp = tuple(stone["position"])
        if sp in revealed_set and list(sp) != [x, y]:
            dist = abs(sp[0] - x) + abs(sp[1] - y)
            status = "extracted" if stone.get("extracted") else "buried"
            hint = _direction_hint(sp[0] - x, sp[1] - y)
            visible_stones.append(
                f"{stone['type']} ({status}) at ({sp[0]},{sp[1]}) — {hint}, {dist} tiles"
            )

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
            target_type=world_mission.get("target_type", "core"),
            target_count=world_mission.get("target_count", 2),
            collected_count=world_mission.get("collected_count", 0),
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
        rovers.append(RoverSummary(
            id=aid,
            position=list(agent["position"]),
            battery=agent["battery"],
            mission=AgentMission(**agent["mission"]),
            visited_count=len(agent.get("visited", [])),
        ))

    stones = []
    for s in WORLD.get("stones", []):
        stones.append(StoneInfo(type=s["type"], position=list(s["position"])))

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
    # Filter stones to only those on revealed cells and strip hidden _true_type
    visible = []
    for s in snap["stones"]:
        if tuple(s["position"]) in revealed:
            s.pop("_true_type", None)
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
