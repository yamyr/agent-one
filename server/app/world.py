"""In-memory world state for the Mars simulation."""

import copy
import logging
import random

logger = logging.getLogger(__name__)

GRID_W, GRID_H = 20, 20

DIRECTIONS = {
    "north": (0, -1),
    "south": (0, 1),
    "east": (1, 0),
    "west": (-1, 0),
}

BATTERY_COST_MOVE = 0.02
BATTERY_COST_DIG = 0.06
BATTERY_COST_PICKUP = 0.02
CHARGE_RATE = 0.20

AGENT_STARTS = {(0, 0), (2, 10), (2, 12)}
STONE_TYPES = ["core", "basalt"]
REVEAL_RADIUS = 2
TARGET_STONE_TYPE = "core"
TARGET_STONE_COUNT = 2


def _generate_stones():
    """Place 5-8 stones at random grid positions, avoiding agent starts."""
    count = random.randint(5, 8)
    stones = []
    occupied = set(AGENT_STARTS)
    while len(stones) < count:
        x = random.randint(0, GRID_W - 1)
        y = random.randint(0, GRID_H - 1)
        if (x, y) in occupied:
            continue
        occupied.add((x, y))
        stones.append({"position": [x, y], "type": random.choice(STONE_TYPES)})
    return stones


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


WORLD = {
    "grid": {"w": GRID_W, "h": GRID_H},
    "agents": {
        "station": {
            "position": [0, 0],
            "type": "station",
            "battery": 1.0,
            "mission": {"objective": "Coordinate Mars mission", "plan": []},
            "visited": [[0, 0]],
        },
        "rover-mock": {
            "position": [2, 10],
            "battery": 1.0,
            "mission": {"objective": "Explore the terrain", "plan": []},
            "visited": [[2, 10]],
            "revealed": _init_revealed(2, 10),
            "inventory": [],
            "type": "rover",
            "tools": [
                {"name": "move", "description": "Move one tile in a cardinal direction (north/south/east/west)."},
                {"name": "check_ground", "description": "Scan current tile for rocks or minerals."},
                {"name": "dig", "description": "Dig at current tile to extract a stone (costs 3x move battery)."},
                {"name": "pickup", "description": "Pick up an extracted stone at current tile into inventory."},
                {"name": "charge", "description": "Recharge battery at the station (must be co-located)."},
            ],
        },
        "rover-mistral": {
            "position": [2, 12],
            "battery": 1.0,
            "mission": {"objective": "Explore the terrain", "plan": []},
            "visited": [[2, 12]],
            "revealed": _init_revealed(2, 12),
            "inventory": [],
            "type": "rover",
            "tools": [
                {"name": "move", "description": "Move one tile in a cardinal direction (north/south/east/west)."},
                {"name": "check_ground", "description": "Scan current tile for rocks or minerals."},
                {"name": "dig", "description": "Dig at current tile to extract a stone (costs 3x move battery)."},
                {"name": "pickup", "description": "Pick up an extracted stone at current tile into inventory."},
                {"name": "charge", "description": "Recharge battery at the station (must be co-located)."},
            ],
        },
    },
    "stones": _generate_stones(),
    "mission": {
        "status": "running",
        "target_type": TARGET_STONE_TYPE,
        "target_count": TARGET_STONE_COUNT,
        "collected_count": 0,
    },
}


def check_ground(agent_id):
    """Check if a stone is present at the agent's current position."""
    agent = WORLD["agents"].get(agent_id)
    if agent is None:
        return {"stone": None}
    x, y = agent["position"]
    for stone in WORLD.get("stones", []):
        if stone["position"] == [x, y]:
            return {"stone": {"type": stone["type"]}}
    return {"stone": None}


def move_agent(agent_id, x, y):
    """Move an agent to target (x, y). Low-level position update only."""
    agent = WORLD["agents"].get(agent_id)
    if agent is None:
        return {"ok": False, "error": f"Unknown agent: {agent_id}"}

    if not (0 <= x < GRID_W and 0 <= y < GRID_H):
        return {"ok": False, "error": f"Out of bounds: ({x}, {y})"}

    ox, oy = agent["position"]
    dist = abs(x - ox) + abs(y - oy)
    if dist == 0:
        return {"ok": False, "error": f"Already at ({x}, {y})"}
    if dist != 1:
        return {"ok": False, "error": f"Not adjacent: ({ox}, {oy}) -> ({x}, {y})"}

    agent["position"] = [x, y]
    logger.info("Agent %s moved (%d,%d) -> (%d,%d)", agent_id, ox, oy, x, y)
    return {"ok": True, "from": [ox, oy], "to": [x, y]}


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

        ox, oy = agent["position"]
        tx, ty = ox + delta[0], oy + delta[1]
        result = move_agent(agent_id, tx, ty)
        if result["ok"]:
            agent["battery"] = max(0.0, agent["battery"] - BATTERY_COST_MOVE)
            if [tx, ty] not in agent["visited"]:
                agent["visited"].append([tx, ty])
            _expand_revealed(agent, tx, ty)
            result["ground"] = check_ground(agent_id)
    elif action_name == "dig":
        result = _execute_dig(agent_id, agent)
    elif action_name == "pickup":
        result = _execute_pickup(agent_id, agent)
    elif action_name == "charge":
        result = _execute_charge(agent_id, agent)
    else:
        return {"ok": False, "error": f"Unknown action: {action_name}"}

    if result["ok"]:
        mission_event = check_mission_status()
        if mission_event:
            result["mission"] = mission_event

    return result


def _find_stone_at(x, y):
    """Find a stone at the given position, or None."""
    for stone in WORLD.get("stones", []):
        if stone["position"] == [x, y]:
            return stone
    return None


def _execute_dig(agent_id, agent):
    """Dig at current tile to extract a buried stone."""
    if agent["battery"] < BATTERY_COST_DIG:
        return {"ok": False, "error": "Not enough battery to dig"}

    x, y = agent["position"]
    stone = _find_stone_at(x, y)
    if stone is None:
        return {"ok": False, "error": f"No stone at ({x}, {y})"}
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


def check_mission_status():
    """Update mission collected_count and detect success/failure.

    Returns a mission event dict if the status changed, or None.
    """
    mission = WORLD["mission"]
    if mission["status"] in ("success", "failed"):
        return None

    # Count target stones across all rover inventories
    collected = 0
    for agent in WORLD["agents"].values():
        for stone in agent.get("inventory", []):
            if stone["type"] == mission["target_type"]:
                collected += 1
    mission["collected_count"] = collected

    # Success: collected enough target stones
    if collected >= mission["target_count"]:
        mission["status"] = "success"
        logger.info("Mission SUCCESS: collected %d/%d %s stones",
                     collected, mission["target_count"], mission["target_type"])
        return {"status": "success", "collected": collected}

    # Failure: all rovers have zero battery and none are at the station
    station = WORLD["agents"].get("station")
    station_pos = station["position"] if station else None
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
    # Filter stones to only those on revealed cells
    snap["stones"] = [s for s in snap["stones"] if tuple(s["position"]) in revealed]
    return snap
