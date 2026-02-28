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

AGENT_STARTS = {(0, 0), (2, 10), (2, 12)}
STONE_TYPES = ["core", "basalt"]


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
            "type": "rover",
            "tools": [
                {"name": "move", "description": "Move one tile in a cardinal direction (north/south/east/west)."},
                {"name": "check_ground", "description": "Scan current tile for rocks or minerals."},
            ],
        },
        "rover-mistral": {
            "position": [2, 12],
            "battery": 1.0,
            "mission": {"objective": "Explore the terrain", "plan": []},
            "visited": [[2, 12]],
            "type": "rover",
            "tools": [
                {"name": "move", "description": "Move one tile in a cardinal direction (north/south/east/west)."},
                {"name": "check_ground", "description": "Scan current tile for rocks or minerals."},
            ],
        },
    },
    "stones": _generate_stones(),
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
            result["ground"] = check_ground(agent_id)
        return result

    return {"ok": False, "error": f"Unknown action: {action_name}"}


def assign_mission(agent_id, objective):
    """Set a new mission objective for the given agent."""
    agent = WORLD["agents"].get(agent_id)
    if agent is None:
        return {"ok": False, "error": f"Unknown agent: {agent_id}"}
    agent["mission"]["objective"] = objective
    logger.info("Mission assigned to %s: %s", agent_id, objective)
    return {"ok": True, "agent_id": agent_id, "objective": objective}


def get_snapshot():
    """Return a deep copy of the current world state."""
    return copy.deepcopy(WORLD)
