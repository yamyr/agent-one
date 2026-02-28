"""In-memory world state for the Mars simulation."""

import copy
import logging

logger = logging.getLogger(__name__)

WORLD = {
    "zones": ["Z01", "Z02", "Z03", "Z04", "Z05"],
    "agents": {
        "rover-mock": {"position": "Z01", "battery": 1.0},
        "rover-mistral": {"position": "Z01", "battery": 1.0},
    },
}


def move_agent(agent_id, target_zone):
    """Move an agent to a target zone. Returns result dict."""
    agent = WORLD["agents"].get(agent_id)
    if agent is None:
        return {"ok": False, "error": f"Unknown agent: {agent_id}"}

    if target_zone not in WORLD["zones"]:
        return {"ok": False, "error": f"Unknown zone: {target_zone}"}

    old_zone = agent["position"]
    if old_zone == target_zone:
        return {"ok": False, "error": f"Already at {target_zone}"}

    agent["position"] = target_zone
    logger.info("Agent %s moved %s -> %s", agent_id, old_zone, target_zone)
    return {"ok": True, "from": old_zone, "to": target_zone}


def get_snapshot():
    """Return a deep copy of the current world state."""
    return copy.deepcopy(WORLD)
