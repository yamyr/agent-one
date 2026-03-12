"""Preset simulation scenarios for the Mars mission.

Each preset defines overrides for world state and agent configuration,
allowing one-click switching between different challenge modes.
"""

from __future__ import annotations

import copy
import logging

logger = logging.getLogger(__name__)

# ── Preset Definitions ──────────────────────────────────────────────────────

PRESETS: dict[str, dict] = {
    "default": {
        "name": "default",
        "description": "Standard simulation — balanced resources, normal storm frequency.",
        "world_overrides": {},
        "agent_overrides": {},
        "active_agents": None,
    },
    "storm_survival": {
        "name": "storm_survival",
        "description": (
            "Frequent intense storms with limited battery. "
            "Tests agent resilience and return-to-base decision making."
        ),
        "world_overrides": {
            "storm": {
                "next_storm_tick": 5,
            },
        },
        "agent_overrides": {
            "*rover*": {"battery": 0.5},
            "*hauler*": {"battery": 0.6},
            "*drone*": {"battery": 0.5},
        },
        "active_agents": "rover-mistral,drone-mistral,station-loop,hauler-mistral",
    },
    "resource_race": {
        "name": "resource_race",
        "description": (
            "Multiple rovers compete to collect abundant resources. "
            "Full battery start with lower delivery target for fast-paced gameplay."
        ),
        "world_overrides": {
            "mission": {
                "target_quantity": 150,
            },
        },
        "agent_overrides": {
            "*rover*": {"battery": 1.0},
            "*hauler*": {"battery": 1.0},
            "*drone*": {"battery": 1.0},
        },
        "active_agents": (
            "rover-mistral,rover-2,rover-large,rover-medium,"
            "drone-mistral,station-loop,hauler-mistral"
        ),
    },
    "exploration": {
        "name": "exploration",
        "description": (
            "Emphasis on discovery with a high delivery target. "
            "Agents must explore far from base to find enough resources."
        ),
        "world_overrides": {
            "mission": {
                "target_quantity": 600,
            },
        },
        "agent_overrides": {
            "*rover*": {"battery": 0.8},
            "*drone*": {"battery": 1.0},
        },
        "active_agents": "rover-mistral,drone-mistral,station-loop,hauler-mistral",
    },
    "cooperative": {
        "name": "cooperative",
        "description": (
            "Multiple rovers with peer messaging encouraged. "
            "Shared objectives require coordination and resource sharing."
        ),
        "world_overrides": {
            "mission": {
                "target_quantity": 500,
            },
        },
        "agent_overrides": {
            "*rover*": {"battery": 0.7},
            "*hauler*": {"battery": 0.8},
            "*drone*": {"battery": 0.8},
        },
        "active_agents": (
            "rover-mistral,rover-2,rover-large,drone-mistral,station-loop,hauler-mistral"
        ),
    },
    "demo_timeline": {
        "name": "demo_timeline",
        "description": (
            "Scripted demo scenario with pre-defined events at specific ticks. "
            "Storms, resource spawns, and battery drains occur on a fixed schedule "
            "for deterministic demos and walkthroughs."
        ),
        "world_overrides": {
            "mission": {
                "target_quantity": 200,
            },
        },
        "agent_overrides": {
            "*rover*": {"battery": 1.0},
            "*hauler*": {"battery": 1.0},
            "*drone*": {"battery": 1.0},
        },
        "active_agents": "rover-mistral,drone-mistral,station-loop,hauler-mistral",
    },
}


def _agent_matches_pattern(agent_id: str, pattern: str) -> bool:
    """Check if an agent ID matches a simple wildcard pattern.

    Supports '*' as prefix/suffix wildcard:
      - '*rover*' matches 'rover-mistral', 'rover-2', etc.
      - '*drone*' matches 'drone-mistral'
      - 'rover-mistral' matches exactly 'rover-mistral'
    """
    if "*" not in pattern:
        return agent_id == pattern
    # Strip leading/trailing '*' and check containment
    core = pattern.strip("*")
    return core in agent_id


def apply_preset(preset_name: str, world_dict: dict) -> dict:
    """Apply a preset's overrides to the given world dict.

    Args:
        preset_name: Key in PRESETS dict.
        world_dict: The WORLD dict to modify in-place.

    Returns:
        The preset definition dict.

    Raises:
        ValueError: If preset_name is not found in PRESETS.
    """
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_name!r}")

    preset = PRESETS[preset_name]

    # Apply world overrides (shallow merge per top-level key)
    for key, overrides in preset.get("world_overrides", {}).items():
        if key in world_dict and isinstance(world_dict[key], dict) and isinstance(overrides, dict):
            world_dict[key].update(overrides)
        else:
            world_dict[key] = copy.deepcopy(overrides)

    # Apply agent overrides
    agent_overrides = preset.get("agent_overrides", {})
    agents = world_dict.get("agents", {})
    for pattern, overrides in agent_overrides.items():
        for agent_id, agent_state in agents.items():
            if _agent_matches_pattern(agent_id, pattern):
                agent_state.update(overrides)

    logger.info("Applied preset %r to world", preset_name)
    return preset


def list_presets() -> list[dict]:
    """Return a list of preset summaries (name + description) for API responses."""
    return [{"name": p["name"], "description": p["description"]} for p in PRESETS.values()]
