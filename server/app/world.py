"""In-memory world state for the Mars simulation."""

import copy
import logging
import math
import random

from .config import settings

logger = logging.getLogger(__name__)

if settings.world_seed:
    random.seed(settings.world_seed)
    logger.info("World seed: %s", settings.world_seed)

GRID_W, GRID_H = 20, 20

DIRECTIONS = {
    "north": (0, 1),
    "south": (0, -1),
    "east": (1, 0),
    "west": (-1, 0),
}

BATTERY_COST_MOVE = 0.02
BATTERY_COST_DIG = 0.06
BATTERY_COST_PICKUP = 0.02
BATTERY_COST_ANALYZE = 0.03
BATTERY_COST_ANALYZE_GROUND = 0.03
CHARGE_RATE = 0.20
MAX_MOVE_DISTANCE = 3

AGENT_STARTS = {(0, 0), (2, 10), (2, 12)}
STONE_TYPES = ["core", "basalt"]
REVEAL_RADIUS = 5
TARGET_STONE_TYPE = "core"
TARGET_STONE_COUNT = 1
MEMORY_MAX = 8


def _random_free_pos(occupied):
    """Pick a random grid position not in `occupied`."""
    while True:
        x = random.randint(0, GRID_W - 1)
        y = random.randint(0, GRID_H - 1)
        if (x, y) not in occupied:
            return x, y


def _generate_stones():
    """Place 5-8 stones with clustered core placement via preferential attachment.

    Returns (stones, core_positions) tuple.
    All stones start with type='unknown' and a hidden '_true_type'.
    """
    count = random.randint(5, 8)
    stones = []
    occupied = set(AGENT_STARTS)
    core_positions = []

    # Phase 1: guarantee at least one core stone (random placement)
    for _ in range(TARGET_STONE_COUNT):
        x, y = _random_free_pos(occupied)
        occupied.add((x, y))
        core_positions.append((x, y))
        stones.append({
            "position": [x, y],
            "type": "unknown",
            "_true_type": "core",
            "extracted": False,
            "analyzed": False,
        })

    # Phase 2: fill the rest
    while len(stones) < count:
        is_core = random.random() < 0.3
        if is_core and core_positions:
            # Preferential attachment: bias toward existing cores
            candidates = [
                (x, y)
                for x in range(GRID_W) for y in range(GRID_H)
                if (x, y) not in occupied
            ]
            if candidates:
                weights = []
                for cx, cy in candidates:
                    w = sum(1.0 / (1 + abs(cx - px) + abs(cy - py)) for px, py in core_positions)
                    weights.append(w)
                (x, y), = random.choices(candidates, weights=weights, k=1)
            else:
                x, y = _random_free_pos(occupied)
            occupied.add((x, y))
            core_positions.append((x, y))
            stones.append({
                "position": [x, y],
                "type": "unknown",
                "_true_type": "core",
                "extracted": False,
                "analyzed": False,
            })
        else:
            x, y = _random_free_pos(occupied)
            occupied.add((x, y))
            stones.append({
                "position": [x, y],
                "type": "unknown",
                "_true_type": "basalt",
                "extracted": False,
                "analyzed": False,
            })

    return stones, core_positions


def _compute_concentration_map(core_positions):
    """Compute a concentration map based on proximity to core stone positions.

    For each cell, concentration = sum(exp(-d^2 / sigma^2)) for each core,
    where d = manhattan distance. Normalized so max = 1.0.
    """
    sigma = 4.0
    conc = {}
    for x in range(GRID_W):
        for y in range(GRID_H):
            val = sum(
                math.exp(-(abs(x - px) + abs(y - py)) ** 2 / (sigma ** 2))
                for px, py in core_positions
            )
            conc[(x, y)] = val

    max_val = max(conc.values()) if conc else 1.0
    if max_val > 0:
        for key in conc:
            conc[key] /= max_val
    return conc


def _cells_in_radius(cx, cy, radius):
    """Return set of (x, y) tuples within Manhattan distance `radius` of (cx, cy), clamped to grid."""
    cells = set()
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if abs(dx) + abs(dy) <= radius:
                x, y = cx + dx, cy + dy
                if 0 <= x < GRID_W and 0 <= y < GRID_H:
                    cells.add((x, y))
    return cells


def _init_revealed(cx, cy):
    """Build initial revealed set for an agent starting at (cx, cy)."""
    return [[x, y] for x, y in sorted(_cells_in_radius(cx, cy, REVEAL_RADIUS))]


def _expand_revealed(agent, cx, cy):
    """Add newly visible cells around (cx, cy) to the agent's revealed list."""
    current = {tuple(c) for c in agent.get("revealed", [])}
    for cell in _cells_in_radius(cx, cy, REVEAL_RADIUS):
        if cell not in current:
            agent.setdefault("revealed", []).append(list(cell))


_ROVER_TOOL_DEFS = [
    {
        "name": "move",
        "description": "Move 1-3 tiles in a cardinal direction (north/south/east/west). Costs 2% battery per tile. Ground is auto-scanned after each move.",
    },
    {"name": "analyze", "description": "Analyze an unknown stone at current tile to reveal its true type. Costs 3% battery."},
    {"name": "dig", "description": "Dig at current tile to extract a stone (costs 6% battery). Stone must be analyzed first."},
    {"name": "pickup", "description": "Pick up an extracted stone at current tile into inventory."},
    {"name": "analyze_ground", "description": "Analyze ground concentration at current tile to detect nearby core deposits. Costs 3% battery. Returns a 0.0-1.0 reading."},
]


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
    stones, core_positions = _generate_stones()
    return {
        "grid": {"w": GRID_W, "h": GRID_H},
        "agents": {
            "station": {
                "position": [0, 0],
                "type": "station",
                "battery": 1.0,
                "mission": {"objective": "Coordinate Mars mission", "plan": []},
                "visited": [[0, 0]],
            },
            "rover-mock": _make_rover(2, 10),
            "rover-mistral": _make_rover(2, 12),
        },
        "stones": stones,
        "concentration_map": _compute_concentration_map(core_positions),
        "mission": {
            "status": "running",
            "target_type": TARGET_STONE_TYPE,
            "target_count": TARGET_STONE_COUNT,
            "collected_count": 0,
        },
    }


WORLD = _build_initial_world()


def reset_world():
    """Reset WORLD to initial state. Re-seeds RNG if world_seed is set."""
    fresh = _build_initial_world()
    WORLD.clear()
    WORLD.update(fresh)
    logger.info("World reset")


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
    """Move an agent to target (x, y). Must be a straight cardinal line, up to MAX_MOVE_DISTANCE tiles."""
    agent = WORLD["agents"].get(agent_id)
    if agent is None:
        return {"ok": False, "error": f"Unknown agent: {agent_id}"}

    if not (0 <= x < GRID_W and 0 <= y < GRID_H):
        return {"ok": False, "error": f"Out of bounds: ({x}, {y})"}

    ox, oy = agent["position"]
    dx, dy = x - ox, y - oy
    dist = abs(dx) + abs(dy)
    if dist == 0:
        return {"ok": False, "error": f"Already at ({x}, {y})"}
    if dist > MAX_MOVE_DISTANCE:
        return {"ok": False, "error": f"Too far: {dist} tiles (max {MAX_MOVE_DISTANCE})"}
    if dx != 0 and dy != 0:
        return {"ok": False, "error": f"Not a straight line: ({ox}, {oy}) -> ({x}, {y})"}

    agent["position"] = [x, y]
    logger.info("Agent %s moved (%d,%d) -> (%d,%d)", agent_id, ox, oy, x, y)
    return {"ok": True, "from": [ox, oy], "to": [x, y], "distance": dist}


def execute_action(agent_id, action_name, params):
    """Engine entry point: execute an action and update world + agent state."""
    agent = WORLD["agents"].get(agent_id)
    if agent is None:
        return {"ok": False, "error": f"Unknown agent: {agent_id}"}

    if action_name == "move":
        direction = params.get("direction")
        delta = DIRECTIONS.get(direction)
        if delta is None:
            return {"ok": False, "error": f"Invalid direction: {direction}"}
        distance = max(1, min(MAX_MOVE_DISTANCE, int(params.get("distance", 1))))

        ox, oy = agent["position"]
        tx, ty = ox + delta[0] * distance, oy + delta[1] * distance
        result = move_agent(agent_id, tx, ty)
        if result["ok"]:
            agent["battery"] = max(0.0, agent["battery"] - BATTERY_COST_MOVE * distance)
            # Mark all intermediate + destination tiles as visited/revealed
            for step in range(1, distance + 1):
                sx, sy = ox + delta[0] * step, oy + delta[1] * step
                if [sx, sy] not in agent["visited"]:
                    agent["visited"].append([sx, sy])
                _expand_revealed(agent, sx, sy)
            result["ground"] = check_ground(agent_id)
            ground = result["ground"]
            if ground["stone"]:
                record_memory(agent_id, f"Moved {direction} {distance} to ({tx},{ty}), found {ground['stone']['type']} stone")
            else:
                record_memory(agent_id, f"Moved {direction} {distance} to ({tx},{ty}), empty ground")
    elif action_name == "analyze":
        result = _execute_analyze(agent_id, agent)
        if result["ok"]:
            record_memory(agent_id, f"Analyzed stone at ({result['position'][0]},{result['position'][1]}), type={result['stone']['type']}")
    elif action_name == "analyze_ground":
        result = _execute_analyze_ground(agent_id, agent)
        if result["ok"]:
            record_memory(agent_id, f"Ground concentration at ({result['position'][0]},{result['position'][1]}): {result['concentration']:.3f}")
    elif action_name == "dig":
        result = _execute_dig(agent_id, agent)
        if result["ok"]:
            record_memory(agent_id, f"Dug out {result['stone']['type']} stone at ({result['position'][0]},{result['position'][1]})")
    elif action_name == "pickup":
        result = _execute_pickup(agent_id, agent)
        if result["ok"]:
            record_memory(agent_id, f"Picked up {result['stone']['type']} stone at ({result['position'][0]},{result['position'][1]}), inventory={result['inventory_count']}")
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
    concentration = WORLD.get("concentration_map", {}).get((x, y), 0.0)
    readings = agent.setdefault("ground_readings", {})
    readings[f"{x},{y}"] = concentration
    logger.info("Agent %s analyzed ground at (%d,%d), concentration=%.2f", agent_id, x, y, concentration)
    return {"ok": True, "position": [x, y], "concentration": round(concentration, 3)}


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
    logger.info("Agent %s charged %.0f%% -> %.0f%%", agent_id, old_battery * 100, agent["battery"] * 100)
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
        record_memory(rover_id, f"Station charged battery {result['battery_before']:.0%} -> {result['battery_after']:.0%}")
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
        logger.info("Mission SUCCESS: delivered %d/%d %s stones to station",
                     delivered, mission["target_count"], mission["target_type"])
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
    x, y = agent["position"]
    mission = WORLD["mission"]
    target_type = mission["target_type"]
    inventory = agent.get("inventory", [])
    revealed_set = {tuple(c) for c in agent.get("revealed", [])}
    tasks = []

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
            # Priority: 0=unknown (might be core), 1=known target, 2=known basalt
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

    if not tasks:
        tasks.append("Explore unvisited tiles to find stones")

    agent["tasks"] = tasks


def assign_mission(agent_id, objective):
    """Set a new mission objective for the given agent."""
    agent = WORLD["agents"].get(agent_id)
    if agent is None:
        return {"ok": False, "error": f"Unknown agent: {agent_id}"}
    agent["mission"]["objective"] = objective
    logger.info("Mission assigned to %s: %s", agent_id, objective)
    return {"ok": True, "agent_id": agent_id, "objective": objective}


def get_snapshot():
    """Return a deep copy of the current world state, filtered by fog-of-war."""
    snap = copy.deepcopy(WORLD)
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
    return snap
