"""Rover & drone agents — reasoners (sync decision engines) and loops (BaseAgent subclasses).

Reasoners return action dicts, never mutate world (except storing last_context).
Loops own the full observe/reason/act/broadcast cycle via BaseAgent.tick().
"""

import asyncio
import json
import logging
import random
import re
import time

from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError, InferenceTimeoutError
from mistralai import SDKError

from .base_agent import BaseAgent
from .broadcast import broadcaster
from .config import settings
from .llm import get_mistral_client
from .llm_utils import safe_get_choice
from .protocol import make_message
from .world import World, world as default_world
from .world import DIRECTIONS, MAX_MOVE_DISTANCE, MAX_MOVE_DISTANCE_DRONE, MAX_MOVE_DISTANCE_HAULER
from .world import (
    FUEL_CAPACITY_ROVER,
    FUEL_CAPACITY_DRONE,
    FUEL_CAPACITY_HAULER,
    DRONE_REVEAL_RADIUS,
    UPGRADES,
)
from .world import (
    BATTERY_COST_MOVE,
    BATTERY_COST_MOVE_DRONE,
    BATTERY_COST_MOVE_HAULER,
    BATTERY_COST_DIG,
    BATTERY_COST_COLLECT_GAS,
)
from .world import BATTERY_COST_ANALYZE, BATTERY_COST_SCAN, BATTERY_COST_NOTIFY
from .world import BATTERY_COST_GATHER_ICE
from .world import MAX_INVENTORY_ROVER, MAX_INVENTORY_HAULER
from .world import BATTERY_COST_INVESTIGATE, BATTERY_COST_USE_REFINERY
from .world import check_ground, direction_hint, best_drone_hotspot, observe_rover
from .world import get_drone_intel_for_rover, get_unread_messages, send_agent_message
from .world import set_agent_model
from .world import (
    execute_action,
    get_snapshot,
    charge_agent,
    next_tick,
    update_geysers,
    update_tasks,
)
from .world import check_storm_tick, get_storm_info, update_goal_confidence
from .world import record_memory
from .world import is_obstacle_at
from .world import detect_move_hazards
from .station import StationAgent
from .training_logger import training_logger
from .training_models import TrainingTurn, TurnWorldSnapshot

logger = logging.getLogger(__name__)

STRUCTURED_REASONING_PROMPT = "\n\nBefore acting, output: SITUATION: <state> | OPTIONS: <a, b> | DECISION: <choice + why> | RISK: low/medium/high"


async def _auto_confirm_gate(host, agent_id: str, action_name: str, params: dict) -> dict | None:
    """Check for hazardous conditions before a move and request confirmation if needed.

    Returns None if the action should proceed (no hazards, confirmed, or feature disabled).
    Returns a result dict ``{"ok": False, "error": ...}`` if the move was denied or timed out.
    """
    from .host import CONFIRM_DEFAULT_TIMEOUT

    # Only gate move actions
    if action_name != "move":
        return None

    # Check config toggle
    if not settings.auto_confirm_enabled:
        return None

    # Compute destination and cost (mirrors execute_action logic)
    direction = params.get("direction")
    delta = DIRECTIONS.get(direction)
    if delta is None:
        return None  # Let execute_action handle the invalid direction error

    world_state = default_world.state
    agent = world_state["agents"].get(agent_id)
    if agent is None:
        return None

    is_drone = agent.get("type") == "drone"
    is_hauler = agent.get("type") == "hauler"

    if is_drone:
        max_dist = MAX_MOVE_DISTANCE_DRONE
        move_cost_per_tile = BATTERY_COST_MOVE_DRONE
    elif is_hauler:
        max_dist = MAX_MOVE_DISTANCE_HAULER
        move_cost_per_tile = BATTERY_COST_MOVE_HAULER
    else:
        from .world import _effective_fuel_capacity

        max_dist = MAX_MOVE_DISTANCE
        move_cost_per_tile = 1 / _effective_fuel_capacity(agent)

    distance = max(1, min(max_dist, int(params.get("distance", 1))))

    from . import storm as storm_mod

    storm_mult = storm_mod.get_battery_multiplier(world_state)
    cost = move_cost_per_tile * distance * storm_mult

    ox, oy = agent["position"]
    dest_x = ox + delta[0] * distance
    dest_y = oy + delta[1] * distance

    hazards = detect_move_hazards(agent_id, dest_x, dest_y, cost)
    if not hazards:
        return None

    # Build combined hazard message
    agent_type = agent.get("type", "rover")
    question = (
        f"{agent_type.capitalize()} {agent_id} is about to move to ({dest_x},{dest_y}). "
        + " ".join(hazards)
        + " Allow this move?"
    )

    request_id = host.create_confirm(agent_id, question, CONFIRM_DEFAULT_TIMEOUT)

    # Build context for UI
    storm_info_ctx = get_storm_info()
    confirm_ctx = {
        "position": list(agent["position"]),
        "battery": agent["battery"],
        "destination": [dest_x, dest_y],
        "hazards": hazards,
        "storm_phase": storm_info_ctx.get("phase"),
        "storm_intensity": storm_info_ctx.get("intensity"),
    }
    confirm_msg = make_message(
        source=agent_id,
        type="event",
        name="confirm_request",
        payload={
            "request_id": request_id,
            "agent_id": agent_id,
            "question": question,
            "timeout": CONFIRM_DEFAULT_TIMEOUT,
            "context": confirm_ctx,
            "auto": True,
        },
    )
    await host.broadcast(confirm_msg.to_dict())

    # Wait for operator response
    confirmed = False
    try:
        entry = host.get_pending_confirm(request_id)
        await asyncio.wait_for(entry["event"].wait(), timeout=CONFIRM_DEFAULT_TIMEOUT)
        confirmed = entry["response"] is True
    except asyncio.TimeoutError:
        timeout_msg = make_message(
            source="world",
            type="event",
            name="confirm_timeout",
            payload={"request_id": request_id, "agent_id": agent_id},
        )
        await host.broadcast(timeout_msg.to_dict())
    finally:
        host.cleanup_confirm(request_id)

    status = "approved" if confirmed else "denied"
    record_memory(agent_id, f"Auto-confirm {status}: {question}")

    if confirmed:
        return None  # Proceed with the move

    return {
        "ok": False,
        "error": f"Move denied by operator (auto-confirm {status}): {'; '.join(hazards)}",
        "auto_confirm_denied": True,
    }


def _build_turn_snapshot(agent_state: dict, world) -> TurnWorldSnapshot:
    """Build a TurnWorldSnapshot from agent state and world model."""
    station = world.get_agents().get("station")
    station_pos = (
        station["position"]
        if station
        and isinstance(station.get("position"), (list, tuple))
        and len(station["position"]) >= 2
        else [0, 0]
    )
    pos = agent_state.get("position", [0, 0])
    if not isinstance(pos, (list, tuple)) or len(pos) < 2:
        pos = [0, 0]
    x, y = pos[0], pos[1]
    dist = abs(x - station_pos[0]) + abs(y - station_pos[1])
    mission = world.get_mission()
    battery = agent_state.get("battery", 0)
    if not isinstance(battery, (int, float)):
        battery = 0
    return TurnWorldSnapshot(
        agent_position=[x, y],
        agent_battery=battery,
        agent_inventory=agent_state.get("inventory", [])
        if isinstance(agent_state.get("inventory"), list)
        else [],
        agent_memory=agent_state.get("memory", [])[-5:]
        if isinstance(agent_state.get("memory"), list)
        else [],
        agent_tasks=agent_state.get("tasks", [])
        if isinstance(agent_state.get("tasks"), list)
        else [],
        visible_stones=[],
        mission_status=mission.get("status", "running") if isinstance(mission, dict) else "running",
        collected_quantity=mission.get("collected", 0) if isinstance(mission, dict) else 0,
        target_quantity=mission.get("target_quantity", 100) if isinstance(mission, dict) else 100,
        distance_to_station=dist,
        goal_confidence=agent_state.get("goal_confidence", 0.5)
        if isinstance(agent_state.get("goal_confidence"), (int, float))
        else 0.5,
    )


def _parse_structured_thinking(raw_thinking: str) -> dict:
    """Extract structured reasoning fields from LLM output."""
    result = {"situation": "", "options": [], "decision": "", "risk": "low"}
    if not raw_thinking:
        return result
    for field in ("situation", "decision", "risk"):
        m = re.search(rf"(?i)^{field}:\s*(.+)$", raw_thinking, re.MULTILINE)
        if m:
            result[field] = m.group(1).strip()
    m = re.search(r"(?i)^OPTIONS:\s*(.+)$", raw_thinking, re.MULTILINE)
    if m:
        result["options"] = [o.strip() for o in m.group(1).split(",") if o.strip()]
    if result["risk"] not in ("low", "medium", "high"):
        logger.debug("Unrecognized risk level %r, defaulting to 'low'", result["risk"])
        result["risk"] = "low"
    return result


TASK_SEPARATOR = "---TASK---"


def parse_task_separator(text):
    """Split LLM text on ---TASK--- separator.

    Returns (thinking, task) where task is None if no separator found.
    """
    if not text:
        return (None, None)
    if TASK_SEPARATOR in text:
        parts = text.split(TASK_SEPARATOR, 1)
        thinking = parts[0].strip() or None
        task = parts[1].strip() or None
        return (thinking, task)
    return (text.strip() or None, None)


MOVE_TOOL = {
    "type": "function",
    "function": {
        "name": "move",
        "description": f"Move the rover 1-{MAX_MOVE_DISTANCE} tiles in a cardinal direction. Costs 1 fuel unit per tile (~{BATTERY_COST_MOVE:.2%} battery).",
        "parameters": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["north", "south", "east", "west"],
                    "description": "Direction to move: north, south, east, or west.",
                },
                "distance": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_MOVE_DISTANCE,
                    "description": f"Number of tiles to move (1-{MAX_MOVE_DISTANCE}). Default 1.",
                },
            },
            "required": ["direction"],
        },
    },
}

DIG_TOOL = {
    "type": "function",
    "function": {
        "name": "dig",
        "description": f"Dig and collect an analyzed vein at current tile into inventory. Costs 6 fuel units (~{BATTERY_COST_DIG:.2%} battery). The vein must be analyzed first.",
        "parameters": {"type": "object", "properties": {}},
    },
}

ANALYZE_TOOL = {
    "type": "function",
    "function": {
        "name": "analyze",
        "description": f"Analyze an unknown vein at current tile to reveal its grade (low/medium/high/rich/pristine) and basalt quantity. Costs 3 fuel units (~{BATTERY_COST_ANALYZE:.2%} battery). Must be done before dig/pickup.",
        "parameters": {"type": "object", "properties": {}},
    },
}

DEPLOY_SOLAR_PANEL_TOOL = {
    "type": "function",
    "function": {
        "name": "deploy_solar_panel",
        "description": f"Deploy a solar panel at current tile. The panel stores {BATTERY_COST_MOVE * 100 * 25:.0f}% charge that can be used later with use_solar_battery. Costs 1 fuel unit to deploy. Limited supply.",
        "parameters": {"type": "object", "properties": {}},
    },
}

USE_SOLAR_BATTERY_TOOL = {
    "type": "function",
    "function": {
        "name": "use_solar_battery",
        "description": "Use a deployed solar panel at current tile to recharge battery. The panel must be active (not depleted).",
        "parameters": {"type": "object", "properties": {}},
    },
}

NOTIFY_TOOL = {
    "type": "function",
    "function": {
        "name": "notify",
        "description": f"Send a radio message to station. Costs {BATTERY_COST_NOTIFY:.0%} battery. Use to report discoveries, request help, or share status updates.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to send to station.",
                },
            },
            "required": ["message"],
        },
    },
}

NOTIFY_PEER_TOOL = {
    "type": "function",
    "function": {
        "name": "notify_peer",
        "description": f"Send a direct message to another rover. Costs {BATTERY_COST_NOTIFY:.0%} battery. Use to share discoveries, coordinate, or warn peers.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_id": {
                    "type": "string",
                    "description": "The agent ID of the rover to message (e.g., 'rover-2', 'rover-large').",
                },
                "message": {
                    "type": "string",
                    "description": "The message to send to the peer rover.",
                },
            },
            "required": ["target_id", "message"],
        },
    },
}

INVESTIGATE_STRUCTURE_TOOL = {
    "type": "function",
    "function": {
        "name": "investigate_structure",
        "description": f"Investigate an adjacent abandoned structure (building or vehicle) to reveal its details and activate it. Must be within 1 tile. Costs ~{BATTERY_COST_INVESTIGATE:.2%} battery.",
        "parameters": {"type": "object", "properties": {}},
    },
}

USE_REFINERY_TOOL = {
    "type": "function",
    "function": {
        "name": "use_refinery",
        "description": f"Use an active refinery to process basalt from your inventory, gaining +50% bonus quantity. Must be adjacent to an investigated refinery. Costs ~{BATTERY_COST_USE_REFINERY:.2%} battery. Requires basalt in inventory.",
        "parameters": {"type": "object", "properties": {}},
    },
}

GATHER_ICE_TOOL = {
    "type": "function",
    "function": {
        "name": "gather_ice",
        "description": f"Gather ice at current tile and store it in inventory as type 'ice'. No analyze required. Costs 4 fuel units (~{BATTERY_COST_GATHER_ICE:.2%} battery).",
        "parameters": {"type": "object", "properties": {}},
    },
}

HARVEST_ICE_TOOL = {
    "type": "function",
    "function": {
        "name": "harvest_ice",
        "description": "Harvest ice at current tile. Ice deposits appear near ice mountains. Costs 4 fuel units. Ice can be delivered to station for water recycling.",
        "parameters": {"type": "object", "properties": {}},
    },
}

RECYCLE_ICE_TOOL = {
    "type": "function",
    "function": {
        "name": "recycle_ice",
        "description": "Recycle all ice in your inventory into water at the station. Must be at station. Each ice unit produces 2 water units. Costs 3 fuel units.",
        "parameters": {"type": "object", "properties": {}},
    },
}

BUILD_GAS_PLANT_TOOL = {
    "type": "function",
    "function": {
        "name": "build_gas_plant",
        "description": "Build a gas plant on an adjacent geyser (1 tile away). Requires 5 station water and costs 8 fuel units.",
        "parameters": {"type": "object", "properties": {}},
    },
}

COLLECT_GAS_TOOL = {
    "type": "function",
    "function": {
        "name": "collect_gas",
        "description": f"Collect all stored gas from an adjacent gas plant into inventory. Costs ~{BATTERY_COST_COLLECT_GAS:.2%} battery.",
        "parameters": {"type": "object", "properties": {}},
    },
}

UPGRADE_BASE_TOOL = {
    "type": "function",
    "function": {
        "name": "upgrade_base",
        "description": "Spend water and gas to upgrade the station. Must be at station (0,0). Available upgrades: charge_mk2 (50w/20g - double charge rate), extended_fuel (30w/10g - +100 fuel capacity), enhanced_scanner (20w/15g - +1 reveal radius), repair_bay (40w/30g - auto full repair at station).",
        "parameters": {
            "type": "object",
            "properties": {
                "upgrade": {
                    "type": "string",
                    "enum": ["charge_mk2", "extended_fuel", "enhanced_scanner", "repair_bay"],
                    "description": "The upgrade to purchase.",
                },
            },
            "required": ["upgrade"],
        },
    },
}

UPGRADE_BUILDING_TOOL = {
    "type": "function",
    "function": {
        "name": "upgrade_building",
        "description": "Upgrade an adjacent active building to improve its stats. Costs battery and basalt from inventory. Max 3 upgrade levels.",
        "parameters": {"type": "object", "properties": {}},
    },
}

DROP_ITEM_TOOL = {
    "type": "function",
    "function": {
        "name": "drop_item",
        "description": "Drop an inventory item on the ground for haulers to collect.",
        "parameters": {
            "type": "object",
            "properties": {
                "index": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "0-based index of item in inventory to drop.",
                }
            },
            "required": ["index"],
        },
    },
}

REQUEST_CONFIRM_TOOL = {
    "type": "function",
    "function": {
        "name": "request_confirm",
        "description": (
            "Request human confirmation before a high-risk action. "
            "Your loop pauses until the human confirms or denies (or timeout). "
            "Use before entering storm zones, crossing hazard tiles, "
            "or moving with very low battery. Do NOT use for routine moves."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Clear question for the human operator (e.g., 'Cross hazard zone during active storm? Battery at 35%.').",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Seconds to wait for response (default 30, max 120).",
                },
            },
            "required": ["question"],
        },
    },
}


ROVER_TOOLS = [
    MOVE_TOOL,
    ANALYZE_TOOL,
    DIG_TOOL,
    DEPLOY_SOLAR_PANEL_TOOL,
    USE_SOLAR_BATTERY_TOOL,
    NOTIFY_TOOL,
    NOTIFY_PEER_TOOL,
    INVESTIGATE_STRUCTURE_TOOL,
    USE_REFINERY_TOOL,
    GATHER_ICE_TOOL,
    RECYCLE_ICE_TOOL,
    BUILD_GAS_PLANT_TOOL,
    COLLECT_GAS_TOOL,
    UPGRADE_BASE_TOOL,
    UPGRADE_BUILDING_TOOL,
    DROP_ITEM_TOOL,
    REQUEST_CONFIRM_TOOL,
]

HAULER_MOVE_TOOL = {
    "type": "function",
    "function": {
        "name": "move",
        "description": f"Move the hauler 1-{MAX_MOVE_DISTANCE_HAULER} tiles in a cardinal direction. Costs 1 fuel unit per tile. Haulers are slower but have bigger fuel tanks.",
        "parameters": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["north", "south", "east", "west"],
                },
                "distance": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_MOVE_DISTANCE_HAULER,
                },
            },
            "required": ["direction"],
        },
    },
}

LOAD_CARGO_TOOL = {
    "type": "function",
    "function": {
        "name": "load_cargo",
        "description": "Load materials at current position into cargo. Picks up ice deposits, or collects items left by rovers. Costs 2 fuel units.",
        "parameters": {"type": "object", "properties": {}},
    },
}

UNLOAD_CARGO_TOOL = {
    "type": "function",
    "function": {
        "name": "unload_cargo",
        "description": "Unload all cargo at current position. At station, items are delivered to storage. Costs 1 fuel unit.",
        "parameters": {"type": "object", "properties": {}},
    },
}

HAULER_TOOLS = [
    HAULER_MOVE_TOOL,
    LOAD_CARGO_TOOL,
    UNLOAD_CARGO_TOOL,
    NOTIFY_TOOL,
]


# ── Rover Reasoners (sync decision engines, read from WORLD) ──


class MistralRoverReasoner:
    """Rover reasoner that decides via Mistral LLM. Returns action dict, does not execute."""

    def __init__(
        self, agent_id="rover-mistral", model="mistral-small-latest", world: World | None = None
    ):
        self.agent_id = agent_id
        self.model = model
        self._client = None
        self._world = world or default_world

    def _get_client(self):
        if self._client is None:
            self._client = get_mistral_client()
        return self._client

    def _build_context(self):
        """Assemble LLM context: identity, state, environment, memory."""
        agent = self._world.get_agent(self.agent_id)
        x, y = agent["position"]
        mission = agent["mission"]
        battery = agent["battery"]
        inventory = agent.get("inventory", [])
        memory = agent.get("memory", [])

        station = self._world.get_agents().get("station")
        station_pos = station["position"] if station else [0, 0]
        dist_to_station = abs(x - station_pos[0]) + abs(y - station_pos[1])
        moves_on_battery = int(battery / BATTERY_COST_MOVE)

        # Unvisited neighbors
        visited_set = {tuple(p) for p in agent.get("visited", [])}
        unvisited_dirs = []
        for name, (dx, dy) in DIRECTIONS.items():
            nx, ny = x + dx, y + dy
            if (nx, ny) not in visited_set:
                unvisited_dirs.append(name)

        # Vein at current tile
        ground = check_ground(self.agent_id)
        stone_info = ground["stone"]
        if stone_info:
            if stone_info["type"] == "unknown":
                stone_line = "unknown vein (needs analyze to reveal grade and quantity)"
            elif stone_info["type"] == "ice":
                stone_line = "ice deposit (ready to gather with gather_ice)"
            else:
                stone_line = f"{stone_info.get('grade', '?')} vein, qty={stone_info.get('quantity', 0)} (analyzed — needs dig)"
        else:
            stone_line = "none"

        # Mission target
        world_mission = self._world.get_mission()
        target_quantity = world_mission.get("target_quantity", 100)
        inventory_full = len(inventory) >= MAX_INVENTORY_ROVER
        station_resources = self._world.state.get(
            "station_resources", {"water": 0, "gas": 0, "parts": []}
        )
        station_water = int(station_resources.get("water", 0))
        station_gas = int(station_resources.get("gas", 0))
        station_upgrades = self._world.state.get("station_upgrades", {})

        parts = []

        parts.append(
            f"You are {self.agent_id}, an autonomous Mars rover.\n"
            "Your job: explore the grid, find basalt veins, analyze them, dig them out, pick them up.\n"
            "Think step by step but keep it to 1-2 sentences, then call a tool.\n"
            "\n"
            "COORDINATE SYSTEM:\n"
            "- North = Y increases, South = Y decreases\n"
            "- East = X increases, West = X decreases\n"
            "- To reach a tile with HIGHER Y, move NORTH. To reach LOWER Y, move SOUTH.\n"
            "\n"
            "VEIN WORKFLOW:\n"
            "- Veins start as 'unknown'. You must ANALYZE them first to reveal grade + quantity.\n"
            "- Grades: low, medium, high, rich, pristine. Higher grade = more basalt.\n"
            "- After analyzing: DIG to extract and collect into inventory in one step.\n"
            "\n"
            "RADIO (notify tool):\n"
            f"- Costs 2 fuel units (~{BATTERY_COST_NOTIFY:.2%} battery). Use sparingly — battery is precious.\n"
            "- Notify station when you dig a high/rich/pristine vein so it can track mission progress.\n"
            "- Notify station when your battery is critically low and you might not make it back.\n"
            "- Notify station when you think you have collected enough basalt to meet the target,\n"
            "  so it can decide whether to recall you or send you for more.\n"
            "- Do NOT notify for routine moves or low-grade finds — save fuel for exploration.\n"
            "\n"
            "RULES:\n"
            f"- Battery is your lifeline. Move costs 1 fuel unit/tile (~{BATTERY_COST_MOVE:.2%}), dig 6 units (~{BATTERY_COST_DIG:.2%}), analyze 3 units (~{BATTERY_COST_ANALYZE:.2%}).\n"
            "- Station is your base at ({sx},{sy}). Return there when battery is low — "
            "the station will recharge you automatically.\n"
            "- ALWAYS keep enough battery to return to station. Check 'moves remaining' vs 'distance to station'.\n"
            "  If moves remaining <= distance to station + 5 (safety margin), head back IMMEDIATELY.\n"
            "- But if there is a vein at your CURRENT TILE, analyze/dig it first — it costs no move fuel to stay.\n"
            "- If you find an unknown vein: analyze → dig. Both on the same tile.\n"
            "- Once you have collected enough basalt, RETURN TO STATION to deliver and complete the mission.\n"
            "- Items are AUTO-DELIVERED when you arrive at the station — your inventory is emptied and you can go collect more.\n"
            "- After delivering, head back out to explore and collect more basalt until the mission target is reached.\n"
            "- Prefer unvisited tiles when exploring. Don't backtrack aimlessly.\n"
            "- Ground is auto-scanned after every move. No need to check manually.\n"
            "- Abandoned structures (buildings/vehicles) are scattered near the station. They block movement — plan paths around them.\n"
            "- Use investigate_structure when adjacent (1 tile) to unexplored structures to reveal their contents and activate them.\n"
            "- Use use_refinery when adjacent to an active refinery with basalt in inventory for +50% bonus material extraction.\n"
            "- Solar panel structures and accumulators provide passive charging — stay near them when battery is low.\n"
            "- Follow your current tasks list. It tells you exactly what to do next.\n"
            "\n"
            f"- MOVEMENT EFFICIENCY: You can move up to {MAX_MOVE_DISTANCE} tiles per move action.\n"
            f"  When heading to a known target, ALWAYS set distance={MAX_MOVE_DISTANCE} (or the remaining distance if closer).\n"
            "  Moving 1 tile at a time wastes turns. Use the full distance.\n"
            "\n"
            "HAZARDS:\n"
            "- ICE MOUNTAINS: Impassable terrain. You cannot move onto a mountain tile.\n"
            "  If a move is blocked by a mountain, choose a different direction.\n"
            "- AIR GEYSERS: Cycle through idle → warning → erupting. Avoid erupting geysers.\n"
            "  Standing on an erupting geyser drains 10% battery. Move away from warning geysers.\n"
            "\n"
            "RESOURCES:\n"
            "- ICE DEPOSITS: Found near mountains. Use gather_ice on the same tile to collect ice.\n"
            "- Gather ice when found, deliver to station for auto-conversion (2 ice -> 1 water).\n"
            "- GAS PLANTS: Use build_gas_plant on an adjacent geyser when station has enough water.\n"
            "- Collect gas with collect_gas from adjacent gas plants, then deliver to station.\n"
            "- BASE UPGRADES: At station, use upgrade_base to spend water/gas on upgrades.\n"
            "- BUILDING UPGRADES: Use upgrade_building when adjacent to an active building to improve its level.\n"
            "- Hauler agents transport materials — notify station if your inventory is full and you can't return.".format(
                sx=station_pos[0], sy=station_pos[1]
            )
        )

        mission_state = self._world.state.get("mission", {})
        delivered_so_far = mission_state.get("collected_quantity", 0)
        in_transit = mission_state.get("in_transit_quantity", 0)
        parts.append(
            f"\n== Mission ==\n"
            f"Objective: {mission['objective']}\n"
            f"Target: collect {target_quantity} units of basalt and deliver to station.\n"
            f"Delivered so far: {delivered_so_far}/{target_quantity} units"
            + (f" (+ {in_transit} in transit)" if in_transit else "")
            + f"\nYour inventory: {len(inventory)}/{MAX_INVENTORY_ROVER} veins"
            + ("\n🏁 INVENTORY FULL — RETURN TO STATION NOW TO DEPOSIT!" if inventory_full else "")
        )

        current_task = agent.get("tasks", [None])[0] if agent.get("tasks") else None
        if current_task:
            parts.append(f"\n== Current Task ==\n{current_task}")

        safety_margin = dist_to_station + 5
        battery_critical = moves_on_battery <= safety_margin

        parts.append(
            f"\n== State ==\n"
            f"Position: ({x}, {y})\n"
            f"Battery: {battery:.0%} ({moves_on_battery} moves remaining, {FUEL_CAPACITY_ROVER} fuel capacity)\n"
            f"Distance to station: {dist_to_station} tiles (need {safety_margin} moves to return safely)\n"
            f"Inventory: {len(inventory)}/{MAX_INVENTORY_ROVER} veins"
            + (
                " ("
                + ", ".join(f"{s.get('grade', '?')} qty={s.get('quantity', 0)}" for s in inventory)
                + ")"
                if inventory
                else ""
            )
            + f"\nSolar panels remaining: {agent.get('solar_panels_remaining', 0)}"
            + ("\n⚠️ BATTERY CRITICAL — return to station now!" if battery_critical else "")
        )

        parts.append("\n== Station Upgrades ==")
        parts.append(f"Station resources: water={station_water}, gas={station_gas}")
        purchased_upgrades = []
        for upgrade_name, config in UPGRADES.items():
            level = int(station_upgrades.get(upgrade_name, 0))
            max_level = int(config["max_level"])
            affordable = station_water >= int(config["water"]) and station_gas >= int(config["gas"])
            if level > 0:
                purchased_upgrades.append(f"{upgrade_name} {level}/{max_level}")
            status = (
                "MAXED"
                if level >= max_level
                else ("affordable" if affordable else "not affordable")
            )
            parts.append(
                f"- {upgrade_name}: level {level}/{max_level}, cost {config['water']}w/{config['gas']}g, {status} — {config['description']}"
            )
        parts.append(
            "Purchased upgrades: "
            + (", ".join(purchased_upgrades) if purchased_upgrades else "none")
        )

        # Nearby solar panels
        nearby_panels = []
        for panel in self._world.get_solar_panels():
            px, py = panel["position"]
            pd = abs(px - x) + abs(py - y)
            if pd <= 10:
                status = "depleted" if panel["depleted"] else f"active ({panel['battery']:.0%})"
                nearby_panels.append(f"  - ({px},{py}): {status}, {pd} tiles")
        if nearby_panels:
            parts.append("Nearby solar panels:")
            parts.extend(nearby_panels)

        # Nearby structures
        nearby_structures = []
        for structure in self._world.get_structures():
            sx, sy = structure["position"]
            sd = abs(sx - x) + abs(sy - y)
            if sd <= 10:
                status = "explored/active" if structure["explored"] else "unexplored"
                label = structure["type"].replace("_", " ").title()
                cat = structure.get("category", "unknown")
                nearby_structures.append(
                    f"  - {label} ({cat}, {status}) at ({sx},{sy}), {sd} tiles"
                )
        if nearby_structures:
            parts.append("Nearby structures (buildings/vehicles — block movement):")
            parts.extend(nearby_structures)

        # Visible veins (on revealed tiles)
        revealed_set = {tuple(c) for c in agent.get("revealed", [])}
        visible_stones = []
        for stone in self._world.get_stones():
            sp = tuple(stone["position"])
            if sp in revealed_set and list(sp) != [x, y]:
                dist = abs(sp[0] - x) + abs(sp[1] - y)
                status = "analyzed" if stone.get("analyzed") else "unknown"
                hint = direction_hint(sp[0] - x, sp[1] - y)
                grade_info = stone.get("grade", "unknown")
                qty_info = stone.get("quantity", 0)
                label = (
                    f"{stone['type']} {grade_info}"
                    if stone["type"] != "unknown"
                    else "unknown vein"
                )
                if qty_info > 0:
                    label += f" qty={qty_info}"
                visible_stones.append(
                    f"{label} ({status}) at ({sp[0]},{sp[1]}) — {hint}, {dist} tiles"
                )

        parts.append(
            f"\n== Environment ==\n"
            f"World: chunk-based (infinite terrain)\n"
            f"Tiles visited: {len(agent.get('visited', []))}\n"
            f"Unvisited neighbors: {', '.join(unvisited_dirs) if unvisited_dirs else 'none'}\n"
            f"Vein here: {stone_line}"
        )
        if visible_stones:
            parts.append("Visible veins nearby:")
            for vs in visible_stones:
                parts.append(f"  - {vs}")

        nearby_ice = []
        for deposit in self._world.state.get("ice_deposits", []):
            pos = deposit.get("position", [])
            if len(pos) != 2:
                continue
            ix, iy = int(pos[0]), int(pos[1])
            if (ix, iy) not in revealed_set:
                continue
            if [ix, iy] == [x, y]:
                continue
            qty = int(deposit.get("quantity", 0))
            if qty <= 0 or deposit.get("gathered"):
                continue
            dist = abs(ix - x) + abs(iy - y)
            hint = direction_hint(ix - x, iy - y)
            nearby_ice.append(f"ice deposit qty={qty} at ({ix},{iy}) - {hint}, {dist} tiles")

        parts.append("\n== ICE & RESOURCES ==")
        parts.append(f"Station resources: water={station_water}, gas={station_gas}")
        if nearby_ice:
            parts.append("Nearby ice deposits:")
            for ice_line in nearby_ice[:8]:
                parts.append(f"  - {ice_line}")
        else:
            parts.append("Nearby ice deposits: none visible")
        parts.append(
            "Gather ice when found, deliver to station for water. Build gas plants on geysers when you have water. Collect gas from gas plants."
        )

        # Nearby hazards from world state
        ctx = observe_rover(self.agent_id)
        if ctx.computed.nearby_obstacles:
            parts.append("\n== Hazards ==")
            for obs in ctx.computed.nearby_obstacles:
                dist = abs(obs.position[0] - x) + abs(obs.position[1] - y)
                hint = direction_hint(obs.position[0] - x, obs.position[1] - y)
                if obs.kind == "mountain":
                    parts.append(
                        f"  - ICE MOUNTAIN at ({obs.position[0]},{obs.position[1]}) — {hint}, {dist} tiles (impassable)"
                    )
                elif obs.kind == "geyser":
                    state_warn = " ⚠️ MOVE AWAY!" if obs.state in ("warning", "erupting") else ""
                    parts.append(
                        f"  - AIR GEYSER at ({obs.position[0]},{obs.position[1]}) — {hint}, {dist} tiles, state: {obs.state}{state_warn}"
                    )

        # Drone scan hotspots — areas discovered by aerial scans not yet visited by rover
        hotspot = best_drone_hotspot(x, y, revealed_set)
        if hotspot:
            hx, hy, conc = hotspot
            hdx, hdy = hx - x, hy - y
            hint = direction_hint(hdx, hdy)
            dist = abs(hdx) + abs(hdy)
            parts.append(
                f"\n== Drone Scan Hotspots ==\n"
                f"Hotspot at ({hx},{hy}) — {hint}, {dist} tiles (concentration: {conc:.3f})\n"
                "Consider navigating toward this drone-discovered area for potential veins."
            )

        if memory:
            recent = memory[-5:]
            parts.append("\n== Recent actions ==")
            for entry in recent:
                parts.append(f"- {entry}")

        # Storm awareness
        storm_info = get_storm_info()
        if storm_info["phase"] != "clear":
            parts.append("\n== DUST STORM ==")
            if storm_info["phase"] == "warning":
                parts.append(
                    "STATUS: Storm approaching! Prepare to seek shelter or return to base."
                )
            elif storm_info["phase"] == "active":
                parts.append(
                    f"STATUS: ACTIVE STORM — intensity {storm_info['intensity']:.0%}\n"
                    f"Battery drain multiplier: {storm_info['battery_multiplier']:.1f}x\n"
                    f"Move failure chance: {storm_info['move_fail_chance']:.0%}\n"
                    "CAUTION: Moves may randomly fail. Battery drains faster. "
                    "Consider returning to station if battery is below 80%."
                )

        # Human confirmation guidance
        parts.append(
            "\n== HUMAN CONFIRMATION ==\n"
            "You have a request_confirm tool to ask the human operator before risky actions.\n"
            "WHEN TO USE:\n"
            "- Before entering tiles near an active dust storm\n"
            "- Before crossing hazard tiles (erupting geysers, unstable terrain)\n"
            "- Before moving when battery is below 15%\n"
            "WHEN NOT TO USE:\n"
            "- Do NOT use for routine moves in safe areas\n"
            "- Do NOT use every turn — only for genuinely dangerous situations\n"
            "Example: request_confirm(question='Cross hazard zone during active storm? Battery at 35%.')"
        )

        # --- Strategic Insights ---
        sm = agent.get("strategic_memory", [])
        if sm:
            parts.append("# Strategic Insights (from past experience)")
            for s in sm:
                parts.append(f"- [tick {s['tick']}] {s['insight']}")

        # Urgent commands from Host inbox
        pending = agent.get("pending_commands", [])
        if pending:
            parts.append("\n== URGENT COMMANDS ==")
            for cmd in pending:
                if cmd["name"] == "recall":
                    reason = cmd.get("payload", {}).get("reason", "No reason given")
                    parts.append(f"RECALL: Return to station immediately. Reason: {reason}")
                elif cmd["name"] == "assign_mission":
                    objective = cmd.get("payload", {}).get("objective", "")
                    parts.append(f"NEW MISSION: {objective}")
                else:
                    parts.append(f"{cmd['name'].upper()}: {cmd.get('payload', {})}")

        # Drone intel: hotspots from drone scans
        drone_intel = get_drone_intel_for_rover(self.agent_id)
        if drone_intel:
            parts.append("\n== DRONE INTEL (high-concentration scan results) ==")
            for di in drone_intel:
                parts.append(
                    f"  \U0001f4e1 [{di['position'][0]},{di['position'][1]}] "
                    f"concentration={di['concentration']} "
                    f"(scanned by {di['scanned_by']} at tick {di['tick']})"
                )
            parts.append("Consider moving toward high-concentration sites.")

        # Peer rover IDs for notify_peer
        peer_rovers = [
            aid
            for aid, a in self._world.get_agents().items()
            if aid != self.agent_id and a.get("type") not in ("station", "drone")
        ]
        if peer_rovers:
            parts.append(
                "\nPEER COMMUNICATION (notify_peer tool):\n"
                f"- Costs {BATTERY_COST_NOTIFY:.0%} battery (same as station radio).\n"
                f"- Available peers: {', '.join(peer_rovers)}\n"
                "- Share rich/pristine vein locations with nearby rovers.\n"
                "- Warn peers about hazards (erupting geysers, storms) in your area.\n"
                "- Coordinate exploration: tell peers which direction you're heading to avoid overlap.\n"
                "- Do NOT spam peers — only message when you have genuinely useful intel."
            )

        # Incoming messages from other agents
        incoming = get_unread_messages(self.agent_id)
        if incoming:
            parts.append("\n== INCOMING MESSAGES ==")
            for msg in incoming:
                parts.append(
                    f"  \U0001f4e8 From {msg['from']} (tick {msg['tick']}): {msg['message']}"
                )

        parts.append(STRUCTURED_REASONING_PROMPT)

        return "\n".join(parts)

    def run_turn(self):
        """Single-shot LLM call. Returns {thinking, action} dict."""
        try:
            client = self._get_client()
            context = self._build_context()
            self._world.set_agent_last_context(self.agent_id, context)

            messages = [
                {"role": "system", "content": context},
                {"role": "user", "content": "Observe your surroundings and decide your next move."},
            ]

            logger.info("Calling Mistral (%s) for %s", self.model, self.agent_id)
            effective_model = settings.fine_tuned_agent_model or self.model
            response = client.chat.complete(
                model=effective_model,
                messages=messages,
                tools=ROVER_TOOLS,
            )
            from .training import collector

            collector.record_agent_interaction(
                agent_id=self.agent_id,
                agent_type="rover",
                messages=messages,
                tools=ROVER_TOOLS,
                response=response,
            )
            choice = safe_get_choice(response, "rover")
            thinking = choice.message.content or None
            action = None

            if choice.message.tool_calls:
                tc = choice.message.tool_calls[0]
                name = tc.function.name
                args = (
                    json.loads(tc.function.arguments)
                    if isinstance(tc.function.arguments, str)
                    else tc.function.arguments
                )
                if name in (
                    "move",
                    "dig",
                    "analyze",
                    "deploy_solar_panel",
                    "use_solar_battery",
                    "notify",
                    "notify_peer",
                    "investigate_structure",
                    "use_refinery",
                    "gather_ice",
                    "harvest_ice",
                    "recycle_ice",
                    "build_gas_plant",
                    "upgrade_base",
                    "collect_gas",
                    "upgrade_building",
                    "drop_item",
                    "request_confirm",
                ):
                    action = {"name": name, "params": args}
                else:
                    logger.warning("%s called unknown tool %r, ignoring", self.agent_id, name)

            if action is None:
                raise RuntimeError(
                    f"{self.agent_id} returned no valid tool action (thinking={thinking!r})"
                )

            if thinking:
                logger.info("Rover thinking: %s", thinking)

            return {"thinking": thinking, "action": action}
        except (
            SDKError,
            ConnectionError,
            TimeoutError,
            RuntimeError,
            json.JSONDecodeError,
            asyncio.TimeoutError,
        ) as exc:
            logger.exception("Rover LLM turn failed for %s, using fallback", self.agent_id)
            return self._fallback_turn(f"LLM unavailable ({type(exc).__name__})")

    def _fallback_turn(self, reason):
        agent = self._world.get_agent(self.agent_id)
        x, y = agent["position"]
        # Default: explore unvisited tiles (inline fallback — no mock rover)
        visited_set = {tuple(p) for p in agent.get("visited", [])}
        unvisited = []
        valid = []
        for name, (dx, dy) in DIRECTIONS.items():
            nx, ny = x + dx, y + dy
            # Skip tiles blocked by mountains
            obs = is_obstacle_at(nx, ny)
            if obs and obs["kind"] == "mountain":
                continue
            valid.append((name, nx, ny))
            if (nx, ny) not in visited_set:
                unvisited.append((name, nx, ny))
        candidates = unvisited if unvisited else valid
        if not candidates:
            # All neighbors are mountains — try any direction
            direction = random.choice(list(DIRECTIONS.keys()))
            dx, dy = DIRECTIONS[direction]
            return {
                "thinking": f"LLM fallback: {reason}. All neighbors blocked, trying {direction}.",
                "action": {"name": "move", "params": {"direction": direction}},
            }
        direction, tx, ty = random.choice(candidates)
        thinking = f"LLM fallback: {reason}. Moving {direction} to ({tx},{ty})."
        return {
            "thinking": thinking,
            "action": {"name": "move", "params": {"direction": direction}},
        }


class HaulerAgent:
    """Hauler reasoner that decides via Mistral LLM."""

    def __init__(
        self, agent_id="hauler-mistral", model="mistral-small-latest", world: World | None = None
    ):
        self.agent_id = agent_id
        self.model = model
        self._client = None
        self._world = world or default_world

    def _get_client(self):
        if self._client is None:
            self._client = get_mistral_client()
        return self._client

    def _build_context(self):
        agent = self._world.get_agent(self.agent_id)
        x, y = agent["position"]
        battery = agent["battery"]
        inventory = agent.get("inventory", [])
        memory = agent.get("memory", [])

        station = self._world.get_agents().get("station")
        station_pos = station["position"] if station else [0, 0]
        dist_to_station = abs(x - station_pos[0]) + abs(y - station_pos[1])
        moves_on_battery = int(battery / BATTERY_COST_MOVE_HAULER)

        resources = self._world.state.get("resources", {})
        water_total = int(resources.get("water", 0))
        gas_total = int(resources.get("gas", 0))
        cargo_drops = self._world.state.get("cargo_drops", [])

        rover_status = []
        rovers_with_items = []
        for rid, rover in self._world.get_agents().items():
            if rover.get("type") != "rover":
                continue
            rx, ry = rover["position"]
            inv = rover.get("inventory", [])
            inv_count = len(inv)
            distance = abs(rx - x) + abs(ry - y)
            rover_status.append((distance, rid, rx, ry, inv_count))
            if inv_count > 0:
                rovers_with_items.append((distance, rid, rx, ry, inv_count))

        rover_status.sort(key=lambda item: item[0])
        rovers_with_items.sort(key=lambda item: item[0])

        parts = []
        parts.append(
            (
                "You are {agent_id}, an autonomous Mars hauler vehicle.\n"
                "Your job: transport inventory items from field rovers to the station at ({sx},{sy}).\n"
                "\n"
                "WORKFLOW:\n"
                "1. Check which rovers have items in their inventory (listed under Nearby Rovers).\n"
                "2. Move toward the nearest rover with items.\n"
                "3. When at the same position as a rover, use load_cargo to take their items.\n"
                "4. You can also use load_cargo to collect ice deposits at your current tile.\n"
                "5. When your inventory has items, return to station and use unload_cargo.\n"
                "\n"
                "RULES:\n"
                "- Battery is your lifeline. Move costs 1 fuel unit/tile.\n"
                "- Station is at ({sx},{sy}). Return there when battery is low.\n"
                "- You can carry up to {max_inventory} items (much more than a rover's 3).\n"
                "- ALWAYS keep enough battery to return to station.\n"
                "- Coordinate with station using notify after major pickup or delivery updates.\n"
                "- If no rovers have items, patrol near active rovers and stay ready for pickup."
            ).format(
                agent_id=self.agent_id,
                sx=station_pos[0],
                sy=station_pos[1],
                max_inventory=MAX_INVENTORY_HAULER,
            )
        )

        parts.append(
            f"\n== State ==\n"
            f"Position: ({x}, {y})\n"
            f"Battery: {battery:.0%} ({moves_on_battery} moves remaining, {FUEL_CAPACITY_HAULER} fuel capacity)\n"
            f"Distance to station: {dist_to_station} tiles\n"
            f"Inventory: {len(inventory)}/{MAX_INVENTORY_HAULER} items\n"
            f"Move range: up to {MAX_MOVE_DISTANCE_HAULER} tiles per move"
        )

        parts.append(
            f"\n== Mission Resources ==\nWater total: {water_total}\nGas total: {gas_total}"
        )

        parts.append("\n== Cargo Drops ==")
        nearby_drops = []
        for drop in cargo_drops:
            pos = drop.get("position", [0, 0])
            items = drop.get("items", [])
            if not items:
                continue
            dx = abs(pos[0] - x) + abs(pos[1] - y)
            nearby_drops.append((dx, pos, len(items)))
        nearby_drops.sort(key=lambda item: item[0])
        if nearby_drops:
            for distance, pos, item_count in nearby_drops[:8]:
                parts.append(
                    f"- Drop at ({pos[0]},{pos[1]}) with {item_count} items, distance {distance}"
                )
        else:
            parts.append("- none")

        parts.append("\n== Nearby Rovers ==")
        if rover_status:
            for distance, rid, rx, ry, inv_count in rover_status:
                marker = "*" if inv_count > 0 else "-"
                parts.append(
                    f"{marker} {rid} at ({rx},{ry}) - inventory {inv_count}/{MAX_INVENTORY_ROVER}, distance {distance}"
                )
        else:
            parts.append("- none")

        parts.append("\n== Rovers With Cargo ==")
        if rovers_with_items:
            for distance, rid, rx, ry, inv_count in rovers_with_items:
                parts.append(
                    f"- {rid} at ({rx},{ry}) carrying {inv_count} items, distance {distance}"
                )
        else:
            parts.append("- none")

        if memory:
            parts.append("\n== Recent actions ==")
            for entry in memory[-5:]:
                parts.append(f"- {entry}")

        parts.append(STRUCTURED_REASONING_PROMPT)
        return "\n".join(parts)

    def run_turn(self):
        try:
            client = self._get_client()
            context = self._build_context()
            self._world.set_agent_last_context(self.agent_id, context)

            messages = [
                {"role": "system", "content": context},
                {
                    "role": "user",
                    "content": "Observe your surroundings and decide your next action.",
                },
            ]

            logger.info("Calling Mistral (%s) for %s", self.model, self.agent_id)
            effective_model = settings.fine_tuned_agent_model or self.model
            response = client.chat.complete(
                model=effective_model,
                messages=messages,
                tools=HAULER_TOOLS,
            )

            choice = safe_get_choice(response, "hauler")
            thinking = choice.message.content or None
            action = None

            if choice.message.tool_calls:
                tc = choice.message.tool_calls[0]
                name = tc.function.name
                args = (
                    json.loads(tc.function.arguments)
                    if isinstance(tc.function.arguments, str)
                    else tc.function.arguments
                )
                if name in ("move", "load_cargo", "unload_cargo", "notify"):
                    action = {"name": name, "params": args}
                else:
                    logger.warning("%s called unknown tool %r, ignoring", self.agent_id, name)

            if action is None:
                raise RuntimeError(
                    f"{self.agent_id} returned no valid tool action (thinking={thinking!r})"
                )

            if thinking:
                logger.info("Hauler thinking: %s", thinking)

            return {"thinking": thinking, "action": action}
        except (
            SDKError,
            ConnectionError,
            TimeoutError,
            RuntimeError,
            json.JSONDecodeError,
            asyncio.TimeoutError,
        ) as exc:
            logger.exception("Hauler LLM turn failed for %s, using fallback", self.agent_id)
            return self._fallback_turn(f"LLM unavailable ({type(exc).__name__})")

    def _fallback_turn(self, reason):
        agent = self._world.get_agent(self.agent_id)
        x, y = agent["position"]
        inventory = agent.get("inventory", [])
        station = self._world.get_agents().get("station")
        station_pos = station["position"] if station else [0, 0]

        if inventory and [x, y] != station_pos:
            dx, dy = station_pos[0] - x, station_pos[1] - y
            if abs(dx) >= abs(dy):
                direction = "east" if dx > 0 else "west"
                distance = max(1, min(abs(dx), MAX_MOVE_DISTANCE_HAULER))
            else:
                direction = "north" if dy > 0 else "south"
                distance = max(1, min(abs(dy), MAX_MOVE_DISTANCE_HAULER))
            return {
                "thinking": f"LLM fallback: {reason}. Returning to station with cargo.",
                "action": {
                    "name": "move",
                    "params": {"direction": direction, "distance": distance},
                },
            }

        if inventory and [x, y] == station_pos:
            return {
                "thinking": f"LLM fallback: {reason}. At station with cargo, unloading now.",
                "action": {"name": "unload_cargo", "params": {}},
            }

        return {
            "thinking": f"LLM fallback: {reason}. Attempting cargo pickup at current position.",
            "action": {"name": "load_cargo", "params": {}},
        }


# Backward-compat aliases
RoverAgent = MistralRoverReasoner


class HuggingFaceRoverReasoner(MistralRoverReasoner):
    """Rover reasoner using HuggingFace Inference API. Inherits context/fallback from Mistral variant."""

    def __init__(self, agent_id="rover-huggingface", model=None, world: World | None = None):
        super().__init__(
            agent_id=agent_id,
            model=model or settings.huggingface_model or "Qwen/Qwen2.5-72B-Instruct",
            world=world,
        )

    def _get_client(self):
        if self._client is None:
            if not settings.hugging_face_read:
                raise RuntimeError("HUGGING_FACE_READ not set")
            self._client = InferenceClient(token=settings.hugging_face_read, provider="auto")
        return self._client

    def run_turn(self):
        """Single-shot LLM call via HuggingFace. Returns {thinking, action} dict."""
        try:
            client = self._get_client()
            context = self._build_context()
            self._world.set_agent_last_context(self.agent_id, context)

            messages = [
                {"role": "system", "content": context},
                {"role": "user", "content": "Observe your surroundings and decide your next move."},
            ]

            logger.info("Calling HuggingFace (%s) for %s", self.model, self.agent_id)
            response = client.chat_completion(
                model=self.model,
                messages=messages,
                tools=ROVER_TOOLS,
                tool_choice="auto",
            )
            choice = safe_get_choice(response, "hf-rover")
            thinking = choice.message.content or None
            action = None

            if choice.message.tool_calls:
                tc = choice.message.tool_calls[0]
                name = tc.function.name
                args = (
                    json.loads(tc.function.arguments)
                    if isinstance(tc.function.arguments, str)
                    else tc.function.arguments
                )
                if name in (
                    "move",
                    "dig",
                    "analyze",
                    "deploy_solar_panel",
                    "use_solar_battery",
                    "notify",
                    "notify_peer",
                    "gather_ice",
                    "harvest_ice",
                    "recycle_ice",
                    "build_gas_plant",
                    "collect_gas",
                    "upgrade_base",
                    "investigate_structure",
                    "use_refinery",
                    "upgrade_building",
                    "drop_item",
                    "request_confirm",
                ):
                    action = {"name": name, "params": args}
                else:
                    logger.warning("%s called unknown tool %r, ignoring", self.agent_id, name)

            if action is None:
                raise RuntimeError(
                    f"{self.agent_id} returned no valid tool action (thinking={thinking!r})"
                )

            if thinking:
                logger.info("Rover thinking: %s", thinking)

            return {"thinking": thinking, "action": action}
        except (
            HfHubHTTPError,
            InferenceTimeoutError,
            ConnectionError,
            TimeoutError,
            RuntimeError,
            json.JSONDecodeError,
            asyncio.TimeoutError,
        ) as exc:
            logger.exception("Rover LLM turn failed for %s, using fallback", self.agent_id)
            return self._fallback_turn(f"LLM unavailable ({type(exc).__name__})")


# ── Drone Reasoners ──


DRONE_MOVE_TOOL = {
    "type": "function",
    "function": {
        "name": "move",
        "description": f"Fly 1-{MAX_MOVE_DISTANCE_DRONE} tiles in a cardinal direction. Costs 1 fuel unit per tile (~{BATTERY_COST_MOVE_DRONE:.2%} battery).",
        "parameters": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["north", "south", "east", "west"],
                    "description": "Direction to fly: north, south, east, or west.",
                },
                "distance": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_MOVE_DISTANCE_DRONE,
                    "description": f"Number of tiles to fly (1-{MAX_MOVE_DISTANCE_DRONE}). Default 1.",
                },
            },
            "required": ["direction"],
        },
    },
}

SCAN_TOOL = {
    "type": "function",
    "function": {
        "name": "scan",
        "description": "Scan the area below to sample concentration readings from sensors. "
        "Returns probability values for surrounding tiles indicating likelihood of "
        f"high-grade basalt vein deposits. Higher values mean closer to rich veins. Costs 2 fuel units (~{BATTERY_COST_SCAN:.2%} battery).",
        "parameters": {"type": "object", "properties": {}},
    },
}

DRONE_TOOLS = [DRONE_MOVE_TOOL, SCAN_TOOL, NOTIFY_TOOL]


class DroneAgent:
    """Drone scout agent powered by Mistral LLM. Moves fast, scans for basalt vein deposits."""

    def __init__(
        self, agent_id="drone-mistral", model="mistral-small-latest", world: World | None = None
    ):
        self.agent_id = agent_id
        self.model = model
        self._client = None
        self._world = world or default_world
        self._mock_fallback = MockDroneAgent(agent_id=agent_id, world=self._world)

    def _get_client(self):
        if self._client is None:
            self._client = get_mistral_client()
        return self._client

    def _build_context(self):
        """Assemble LLM context for the drone scout."""
        agent = self._world.get_agent(self.agent_id)
        x, y = agent["position"]
        mission = agent["mission"]
        battery = agent["battery"]
        memory = agent.get("memory", [])

        station = self._world.get_agents().get("station")
        station_pos = station["position"] if station else [0, 0]
        dist_to_station = abs(x - station_pos[0]) + abs(y - station_pos[1])
        moves_on_battery = int(battery / BATTERY_COST_MOVE_DRONE)

        scanned_positions = {tuple(s["position"]) for s in self._world.get_drone_scans()}

        # Safety margin — same logic as rover
        safety_margin = dist_to_station + 5
        battery_critical = moves_on_battery <= safety_margin

        # Nearest unscanned area hint (same logic as MockDroneAgent)
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

        # Last scan result
        drone_scans = self._world.get_drone_scans()
        last_scan = drone_scans[-1] if drone_scans else None

        parts = []

        # -- Instructions --
        parts.append(
            f"You are {self.agent_id}, an autonomous Mars drone scout.\n"
            "Your job: fly over the terrain and SCAN areas to detect basalt vein deposits.\n"
            "You are a pure scout — you CANNOT dig or pick up veins. Rovers depend on your scan data.\n"
            "Think step by step but keep it to 1-2 sentences, then call a tool.\n"
            "\n"
            "COORDINATE SYSTEM:\n"
            "- North = Y increases, South = Y decreases\n"
            "- East = X increases, West = X decreases\n"
            "\n"
            "SCAN STRATEGY:\n"
            "- Use 'scan' to sample concentration readings at your current position.\n"
            "- Readings range 0.0-1.0. Higher values indicate high-grade basalt veins nearby.\n"
            "- Scan data is shared with rovers automatically — they will navigate to hotspots you find.\n"
            "- Scan outward from station in expanding rings. Cover NEARBY areas first, then push further.\n"
            "- Don't fly far when there are unscanned areas close by. Check 'Nearest unscanned area' below.\n"
            "- Don't scan the same area twice.\n"
            "\n"
            "RADIO (notify tool):\n"
            f"- Costs 2 fuel units (~{BATTERY_COST_NOTIFY:.2%} battery).\n"
            "- MANDATORY: After any scan with peak >= 0.5, you MUST call notify BEFORE moving.\n"
            "  Include the position and peak reading so station can dispatch rovers.\n"
            "- Also notify station when your battery is low or you have completed a sweep.\n"
            "- You are the eyes of the mission. Rovers are blind without your reports.\n"
            "\n"
            "RULES:\n"
            f"- Battery: move costs 3 fuel units/tile (~{BATTERY_COST_MOVE_DRONE:.2%}), scan costs 2 fuel units (~{BATTERY_COST_SCAN:.2%}), notify costs 2 fuel units (~{BATTERY_COST_NOTIFY:.2%}). You can fly up to {MAX_MOVE_DISTANCE_DRONE} tiles per move.\n"
            "- Station is at ({sx},{sy}). Return there when battery is low — "
            "the station will recharge you automatically.\n"
            "- ALWAYS keep enough battery to return to station. Check 'moves remaining' vs 'distance to station'.\n"
            "  If moves remaining <= distance to station + 5 (safety margin), return to station IMMEDIATELY.\n"
            "- Prefer unvisited areas when exploring. Don't backtrack aimlessly.".format(
                sx=station_pos[0], sy=station_pos[1]
            )
        )

        # -- Mission --
        parts.append(
            f"\n== Mission ==\n"
            f"Objective: {mission['objective']}\n"
            f"Scans performed: {len(drone_scans)}"
        )

        current_task = agent.get("tasks", [None])[0] if agent.get("tasks") else None
        if current_task:
            parts.append(f"\n== Current Task ==\n{current_task}")

        # -- State --
        parts.append(
            f"\n== State ==\n"
            f"Position: ({x}, {y})\n"
            f"Battery: {battery:.0%} ({moves_on_battery} moves remaining, {FUEL_CAPACITY_DRONE} fuel capacity)\n"
            f"Distance to station: {dist_to_station} tiles (need {safety_margin} moves to return safely)\n"
            f"Tiles visited: {len(agent.get('visited', []))}"
            + ("\n⚠️ BATTERY CRITICAL — return to station now!" if battery_critical else "")
        )

        # -- Last Scan --
        if last_scan:
            scan_pos = last_scan["position"]
            scan_peak = last_scan["peak"]
            parts.append(
                f"\n== Last Scan ==\n"
                f"Position: ({scan_pos[0]}, {scan_pos[1]}), peak concentration: {scan_peak:.2f}"
            )
            # Check if hotspot was notified
            if scan_peak >= 0.5:
                last_action_was_notify = memory and "notify" in memory[-1].lower()
                if not last_action_was_notify:
                    parts.append("⚠️ HOTSPOT — notify station before moving!")

        # -- Environment --
        parts.append(
            f"\n== Environment ==\n"
            f"Already scanned here: {'yes' if (x, y) in scanned_positions else 'no'}"
        )
        if best_target:
            tx, ty = best_target
            hint = direction_hint(tx - x, ty - y)
            parts.append(f"Nearest unscanned area: ({tx},{ty}) — {hint}, {best_dist} tiles")
        else:
            parts.append("Nearest unscanned area: none within range")

        hot_scans = []
        for scan in drone_scans[-5:]:
            if scan["peak"] > 0.2:
                hot_scans.append(
                    f"  - ({scan['position'][0]},{scan['position'][1]}): peak={scan['peak']:.2f}"
                )
        if hot_scans:
            parts.append("Recent hotspots found:")
            parts.extend(hot_scans)

        if memory:
            recent = memory[-5:]
            parts.append("\n== Recent actions ==")
            for entry in recent:
                parts.append(f"- {entry}")

        # --- Strategic Insights ---
        sm = agent.get("strategic_memory", [])
        if sm:
            parts.append("# Strategic Insights (from past experience)")
            for s in sm:
                parts.append(f"- [tick {s['tick']}] {s['insight']}")

        # -- Urgent commands from Host inbox --
        pending = agent.get("pending_commands", [])
        if pending:
            parts.append("\n== URGENT COMMANDS ==")
            for cmd in pending:
                if cmd["name"] == "recall":
                    reason = cmd.get("payload", {}).get("reason", "No reason given")
                    parts.append(f"RECALL: Return to station immediately. Reason: {reason}")
                elif cmd["name"] == "assign_mission":
                    objective = cmd.get("payload", {}).get("objective", "")
                    parts.append(f"NEW MISSION: {objective}")
                else:
                    parts.append(f"{cmd['name'].upper()}: {cmd.get('payload', {})}")

        parts.append(STRUCTURED_REASONING_PROMPT)

        return "\n".join(parts)

    def run_turn(self):
        """Single-shot LLM call for drone. Returns {thinking, action} dict."""
        try:
            client = self._get_client()
            context = self._build_context()
            self._world.set_agent_last_context(self.agent_id, context)

            messages = [
                {"role": "system", "content": context},
                {
                    "role": "user",
                    "content": "Observe your surroundings and decide your next action.",
                },
            ]

            logger.info("Calling Mistral (%s) for %s", self.model, self.agent_id)
            effective_model = settings.fine_tuned_agent_model or self.model
            response = client.chat.complete(
                model=effective_model,
                messages=messages,
                tools=DRONE_TOOLS,
            )
            from .training import collector

            collector.record_agent_interaction(
                agent_id=self.agent_id,
                agent_type="drone",
                messages=messages,
                tools=DRONE_TOOLS,
                response=response,
            )
            choice = safe_get_choice(response, "drone")
            thinking = choice.message.content or None
            action = None

            if choice.message.tool_calls:
                tc = choice.message.tool_calls[0]
                name = tc.function.name
                args = (
                    json.loads(tc.function.arguments)
                    if isinstance(tc.function.arguments, str)
                    else tc.function.arguments
                )
                if name in ("move", "scan", "notify"):
                    action = {"name": name, "params": args}
                else:
                    logger.warning("%s called unknown tool %r, ignoring", self.agent_id, name)

            if action is None:
                agent = self._world.get_agent(self.agent_id)
                is_first_turn = not agent.get("memory")
                if is_first_turn:
                    logger.warning(
                        "%s returned no tool call on first turn, falling back to scan",
                        self.agent_id,
                    )
                    action = {"name": "scan", "params": {}}
                else:
                    raise RuntimeError(
                        f"{self.agent_id} returned no valid tool action (thinking={thinking!r})"
                    )

            if thinking:
                logger.info("Drone thinking: %s", thinking)

            return {"thinking": thinking, "action": action}
        except (
            SDKError,
            ConnectionError,
            TimeoutError,
            RuntimeError,
            json.JSONDecodeError,
            asyncio.TimeoutError,
        ) as exc:
            logger.exception("Drone LLM turn failed for %s, using fallback", self.agent_id)
            return self._fallback_turn(f"LLM unavailable ({type(exc).__name__})")

    def _fallback_turn(self, reason):
        fallback = self._mock_fallback.run_turn()
        fallback_thinking = fallback.get("thinking") or ""
        prefix = f"LLM fallback: {reason}. "
        fallback["thinking"] = (prefix + fallback_thinking).strip()
        return fallback


class HuggingFaceDroneAgent(DroneAgent):
    """Drone agent using HuggingFace Inference API. Inherits context/fallback from Mistral variant."""

    def __init__(self, agent_id="drone-huggingface", model=None, world: World | None = None):
        super().__init__(
            agent_id=agent_id,
            model=model or settings.huggingface_model or "Qwen/Qwen2.5-72B-Instruct",
            world=world,
        )

    def _get_client(self):
        if self._client is None:
            if not settings.hugging_face_read:
                raise RuntimeError("HUGGING_FACE_READ not set")
            self._client = InferenceClient(token=settings.hugging_face_read, provider="auto")
        return self._client

    def run_turn(self):
        """Single-shot LLM call for drone via HuggingFace. Returns {thinking, action} dict."""
        try:
            client = self._get_client()
            context = self._build_context()
            self._world.set_agent_last_context(self.agent_id, context)

            messages = [
                {"role": "system", "content": context},
                {
                    "role": "user",
                    "content": "Observe your surroundings and decide your next action.",
                },
            ]

            logger.info("Calling HuggingFace (%s) for %s", self.model, self.agent_id)
            response = client.chat_completion(
                model=self.model,
                messages=messages,
                tools=DRONE_TOOLS,
                tool_choice="auto",
            )
            choice = safe_get_choice(response, "drone")
            thinking = choice.message.content or None
            action = None

            if choice.message.tool_calls:
                tc = choice.message.tool_calls[0]
                name = tc.function.name
                args = (
                    json.loads(tc.function.arguments)
                    if isinstance(tc.function.arguments, str)
                    else tc.function.arguments
                )
                if name in ("move", "scan", "notify"):
                    action = {"name": name, "params": args}
                else:
                    logger.warning("%s called unknown tool %r, ignoring", self.agent_id, name)

            if action is None:
                agent = self._world.get_agent(self.agent_id)
                is_first_turn = not agent.get("memory")
                if is_first_turn:
                    logger.warning(
                        "%s returned no tool call on first turn, falling back to scan",
                        self.agent_id,
                    )
                    action = {"name": "scan", "params": {}}
                else:
                    raise RuntimeError(
                        f"{self.agent_id} returned no valid tool action (thinking={thinking!r})"
                    )

            if thinking:
                logger.info("Drone thinking: %s", thinking)

            return {"thinking": thinking, "action": action}
        except (
            HfHubHTTPError,
            InferenceTimeoutError,
            ConnectionError,
            TimeoutError,
            RuntimeError,
            json.JSONDecodeError,
            asyncio.TimeoutError,
        ) as exc:
            logger.exception("Drone LLM turn failed for %s, using fallback", self.agent_id)
            return self._fallback_turn(f"LLM unavailable ({type(exc).__name__})")


class MockDroneAgent:
    """Mock drone that systematically scans the map — no LLM calls."""

    def __init__(self, agent_id="drone-mistral", world: World | None = None):
        self.agent_id = agent_id
        self._world = world or default_world

    def run_turn(self):
        agent = self._world.get_agent(self.agent_id)
        x, y = agent["position"]

        context = (
            f"Mock drone at ({x},{y}), battery={agent['battery']:.0%}, "
            f"scans={len(self._world.get_drone_scans())}"
        )
        self._world.set_agent_last_context(self.agent_id, context)

        # Check for recall command — override everything, head to station
        for cmd in agent.get("pending_commands", []):
            if cmd["name"] == "recall":
                station = self._world.get_agents().get("station")
                sp = station["position"] if station else [0, 0]
                dx, dy = sp[0] - x, sp[1] - y
                if dx == 0 and dy == 0:
                    thinking = f"Recall received but already at station ({x}, {y})."
                    return {
                        "thinking": thinking,
                        "action": {"name": "move", "params": {"direction": "north", "distance": 1}},
                    }
                if abs(dx) >= abs(dy):
                    direction = "east" if dx > 0 else "west"
                    distance = min(abs(dx), MAX_MOVE_DISTANCE_DRONE)
                else:
                    direction = "north" if dy > 0 else "south"
                    distance = min(abs(dy), MAX_MOVE_DISTANCE_DRONE)
                reason = cmd.get("payload", {}).get("reason", "emergency")
                thinking = f"RECALL received: {reason}. Heading to station at ({sp[0]},{sp[1]})."
                return {
                    "thinking": thinking,
                    "action": {
                        "name": "move",
                        "params": {"direction": direction, "distance": distance},
                    },
                }

        # Battery safety — mock agent's own reasoning (not engine logic)
        station = self._world.get_agents().get("station")
        sp = station["position"] if station else [0, 0]
        dist = abs(x - sp[0]) + abs(y - sp[1])
        cost_to_return = dist * BATTERY_COST_MOVE_DRONE
        if agent["battery"] <= cost_to_return + 0.06 and [x, y] != sp:
            dx, dy = sp[0] - x, sp[1] - y
            if dx != 0:
                direction = "east" if dx > 0 else "west"
                distance = min(abs(dx), MAX_MOVE_DISTANCE_DRONE)
            elif dy != 0:
                direction = "north" if dy > 0 else "south"
                distance = min(abs(dy), MAX_MOVE_DISTANCE_DRONE)
            else:
                direction = "north"
                distance = 1
            thinking = (
                f"I'm at ({x}, {y}). LOW BATTERY ({agent['battery']:.0%}) — must return to station!"
            )
            return {
                "thinking": thinking,
                "action": {
                    "name": "move",
                    "params": {"direction": direction, "distance": distance},
                },
            }

        # Scan if current position not yet scanned
        scanned_positions = {tuple(s["position"]) for s in self._world.get_drone_scans()}
        if (x, y) not in scanned_positions:
            thinking = f"I'm at ({x}, {y}). Scanning area for concentration readings."
            return {"thinking": thinking, "action": {"name": "scan", "params": {}}}

        # Find nearest unscanned position within a search radius
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

        if best_target:
            tx, ty = best_target
            dx, dy = tx - x, ty - y
            if abs(dx) >= abs(dy):
                direction = "east" if dx > 0 else "west"
                distance = min(abs(dx), MAX_MOVE_DISTANCE_DRONE)
            else:
                direction = "north" if dy > 0 else "south"
                distance = min(abs(dy), MAX_MOVE_DISTANCE_DRONE)
            thinking = (
                f"I'm at ({x}, {y}). Flying {direction} toward unscanned area at ({tx},{ty})."
            )
            return {
                "thinking": thinking,
                "action": {
                    "name": "move",
                    "params": {"direction": direction, "distance": distance},
                },
            }

        # All nearby scanned — explore outward (infinite grid, no boundary check)
        valid = list(DIRECTIONS.keys())
        direction = random.choice(valid)
        thinking = f"I'm at ({x}, {y}). All nearby areas covered, exploring outward."
        return {
            "thinking": thinking,
            "action": {
                "name": "move",
                "params": {"direction": direction, "distance": MAX_MOVE_DISTANCE_DRONE},
            },
        }


# ── Loops (BaseAgent subclasses — own the tick cycle) ──


class RoverLoop(BaseAgent):
    """Generic rover tick: inject commands → reason → execute → broadcast."""

    _reasoner: MistralRoverReasoner

    async def tick(self, host) -> None:
        mission_status = self._world.get_mission()["status"]

        # Inject pending commands from inbox into WORLD for reasoner to read
        pending = host.drain_inbox(self.agent_id)
        # During abort, force recall so rover heads to station
        if mission_status == "aborted":
            pending = [
                {"name": "recall", "payload": {"reason": "Mission aborted — return to station"}}
            ]
        self._world.set_pending_commands(self.agent_id, pending if pending else None)

        update_tasks(self.agent_id)

        # If aborted and already at station, stop this agent's loop
        rover = self._world.get_agents().get(self.agent_id)
        station_agent = self._world.get_agents().get("station")
        if (
            mission_status == "aborted"
            and rover
            and station_agent
            and rover["position"] == station_agent["position"]
        ):
            logger.info("Agent %s at station — abort complete", self.agent_id)
            return

        # ── Training: capture pre-state ──
        pre_rover = self._world.get_agents().get(self.agent_id) or {}
        pre_position = list(pre_rover.get("position", [0, 0]))
        pre_battery = pre_rover.get("battery", 1.0)
        pre_confidence = pre_rover.get("goal_confidence", 0.5)
        world_snap = (
            _build_turn_snapshot(pre_rover, self._world) if pre_rover else TurnWorldSnapshot()
        )
        context_text = pre_rover.get("last_context", "")
        t0 = time.monotonic()
        turn = await asyncio.to_thread(self._reasoner.run_turn)
        llm_ms = int((time.monotonic() - t0) * 1000)
        _tick, _power_events, _timeline_events = next_tick()

        # Advance storm lifecycle and broadcast any storm events
        storm_events = check_storm_tick()
        for sevt in storm_events:
            storm_msg = make_message(
                source="world",
                type="event",
                name=sevt["name"],
                payload=sevt["payload"],
            )
            await host.broadcast(storm_msg.to_dict())

        # Broadcast scripted timeline events
        for tevt in _timeline_events:
            tmsg = make_message(
                source="world",
                type="event",
                name=tevt["name"],
                payload=tevt["payload"],
            )
            await host.broadcast(tmsg.to_dict())

        # Broadcast power budget events (warnings + emergency mode transitions)
        for pevt in _power_events:
            ename = pevt["type"]
            payload = {k: v for k, v in pevt.items() if k != "type"}
            power_msg = make_message(source="world", type="event", name=ename, payload=payload)
            await host.broadcast(power_msg.to_dict())
            # Record warnings in station memory so station LLM sees them
            if ename == "power_budget_warning":
                record_memory(
                    "station",
                    f"PowerBudgetWarning: {pevt['agent_id']} battery {pevt['battery']:.0%} "
                    f"below budget {pevt['budget']:.0%}",
                )
            elif ename == "emergency_mode_activated":
                record_memory(
                    "station", "EMERGENCY MODE ACTIVATED — total power demand exceeds capacity"
                )
            elif ename == "emergency_mode_deactivated":
                record_memory("station", "Emergency mode deactivated — power demand normalized")

        geyser_events = update_geysers()
        messages = []

        # Broadcast geyser eruption events
        for ge in geyser_events:
            msg = make_message(
                source="world",
                type="event",
                name="geyser_eruption",
                payload=ge,
            )
            messages.append(msg)

        if turn["thinking"]:
            msg = make_message(
                source=self.agent_id,
                type="event",
                name="thinking",
                payload={
                    "text": turn["thinking"],
                    "structured": _parse_structured_thinking(turn["thinking"]),
                },
            )
            messages.append(msg)

        # ── Human confirmation handling ──
        _confirm_result = None
        if turn["action"] and turn["action"]["name"] == "request_confirm":
            from .host import CONFIRM_DEFAULT_TIMEOUT

            q = turn["action"]["params"].get("question", "Confirm action?")
            t = turn["action"]["params"].get("timeout", CONFIRM_DEFAULT_TIMEOUT)
            t = max(5, min(120, t))
            request_id = host.create_confirm(self.agent_id, q, t)
            # Build context for UI
            rover_state = self._world.get_agents().get(self.agent_id, {})
            storm_info_ctx = get_storm_info()
            confirm_ctx = {
                "position": rover_state.get("position", [0, 0]),
                "battery": rover_state.get("battery", 0),
                "storm_phase": storm_info_ctx.get("phase"),
                "storm_intensity": storm_info_ctx.get("intensity"),
            }
            confirm_msg = make_message(
                source=self.agent_id,
                type="event",
                name="confirm_request",
                payload={
                    "request_id": request_id,
                    "agent_id": self.agent_id,
                    "question": q,
                    "timeout": t,
                    "context": confirm_ctx,
                },
            )
            await host.broadcast(confirm_msg.to_dict())

            confirmed = False
            try:
                entry = host.get_pending_confirm(request_id)
                await asyncio.wait_for(entry["event"].wait(), timeout=t)
                confirmed = entry["response"] is True
            except asyncio.TimeoutError:
                timeout_msg = make_message(
                    source="world",
                    type="event",
                    name="confirm_timeout",
                    payload={"request_id": request_id, "agent_id": self.agent_id},
                )
                await host.broadcast(timeout_msg.to_dict())
            finally:
                host.cleanup_confirm(request_id)

            status = "approved" if confirmed else "denied"
            record_memory(self.agent_id, f"Confirmation {status}: {q}")
            _confirm_result = {"ok": True, "confirmed": confirmed, "question": q}

        if turn["action"] and turn["action"]["name"] != "request_confirm":
            # Auto-confirm gate: check for hazardous move conditions
            _gate_result = await _auto_confirm_gate(
                host, self.agent_id, turn["action"]["name"], turn["action"]["params"]
            )
            if _gate_result is not None:
                result = _gate_result
            else:
                result = execute_action(
                    self.agent_id,
                    turn["action"]["name"],
                    turn["action"]["params"],
                )
            if result["ok"]:
                action_msg = make_message(
                    source=self.agent_id,
                    type="action",
                    name=turn["action"]["name"],
                    payload=result,
                )
                messages.append(action_msg)

                ground = result.get("ground")
                if ground and ground["stone"]:
                    check_msg = make_message(
                        source=self.agent_id,
                        type="event",
                        name="check",
                        payload=ground,
                    )
                    messages.append(check_msg)

                # Save notify to station memory and emit station thinking log
                if turn["action"]["name"] == "notify" and result.get("message"):
                    pos = result["position"]
                    station_state = self._world.get_agents().get("station")
                    if station_state:
                        mem = station_state.setdefault("memory", [])
                        mem.append(
                            f"Radio from {self.agent_id} at ({pos[0]},{pos[1]}): {result['message']}"
                        )
                    station_log = make_message(
                        source="station",
                        type="event",
                        name="thinking",
                        payload={
                            "text": f"Radio from {self.agent_id} at ({pos[0]},{pos[1]}): {result['message']}"
                        },
                    )
                    messages.append(station_log)

                # Broadcast peer message event for UI visualization
                if turn["action"]["name"] == "notify_peer" and result.get("ok"):
                    peer_msg = make_message(
                        source=self.agent_id,
                        type="event",
                        name="peer_message",
                        payload={
                            "target": result["target"],
                            "message": result["message"],
                            "position": result["position"],
                        },
                    )
                    messages.append(peer_msg)

                # Don't check mission success/failure during abort
                if mission_status != "aborted":
                    mission_event = result.get("mission")
                    if mission_event:
                        # Emit deposit events for each delivery
                        for delivery in mission_event.get("deliveries", []):
                            deposit_msg = make_message(
                                source=delivery["agent"],
                                type="event",
                                name="deposit",
                                payload={
                                    "items_deposited": delivery["items_deposited"],
                                    "target_deposited": delivery["target_deposited"],
                                    "delivered_total": mission_event.get("delivered_quantity", 0),
                                },
                            )
                            messages.append(deposit_msg)
                        # Emit mission status change (success/failed only)
                        if mission_event["status"] in ("success", "failed"):
                            mission_msg = make_message(
                                source="world",
                                type="event",
                                name="mission_" + mission_event["status"],
                                payload=mission_event,
                            )
                            messages.append(mission_msg)

        if _confirm_result is not None:
            action_msg = make_message(
                source=self.agent_id,
                type="action",
                name="request_confirm",
                payload=_confirm_result,
            )
            messages.append(action_msg)

        # LLM-owned task: update agent tasks from LLM output
        llm_task = turn.get("task")
        if llm_task is not None:
            agent_state = self._world.get_agent(self.agent_id)
            old_task = agent_state.get("tasks", [None])[0]
            if llm_task != old_task:
                agent_state["tasks"] = [llm_task]
                task_msg = make_message(
                    source=self.agent_id,
                    type="event",
                    name="task_update",
                    payload={"task": llm_task},
                )
                messages.append(task_msg)

        # ── Goal confidence update ──
        _action_ok_for_confidence = False
        _action_name_for_confidence = ""
        if turn["action"]:
            _action_name_for_confidence = turn["action"]["name"]
            for m in messages:
                md = m.to_dict() if hasattr(m, "to_dict") else m
                if md.get("type") == "action" and md.get("name") == _action_name_for_confidence:
                    _action_ok_for_confidence = md.get("payload", {}).get("ok", False)
                    break
        _is_fallback = "fallback" in (turn.get("thinking") or "").lower()
        if turn["action"]:
            if _action_ok_for_confidence:
                if _action_name_for_confidence == "deliver":
                    update_goal_confidence(self.agent_id, 0.10)
                else:
                    update_goal_confidence(self.agent_id, 0.05)
            else:
                update_goal_confidence(self.agent_id, -0.05)
        if _is_fallback:
            update_goal_confidence(self.agent_id, -0.08)
        if storm_events:
            update_goal_confidence(self.agent_id, -0.08)

        for msg in messages:
            await host.broadcast(msg.to_dict())

        await broadcaster.send(make_message("world", "event", "state", get_snapshot()).to_dict())

        # ── Training: log agent turn ──
        action_result_data = {}
        action_ok = False
        action_name = ""
        action_params = {}
        if turn["action"]:
            action_name = turn["action"]["name"]
            action_params = turn["action"]["params"]
            for m in messages:
                md = m.to_dict() if hasattr(m, "to_dict") else m
                if md.get("type") == "action" and md.get("name") == action_name:
                    action_result_data = md.get("payload", {})
                    action_ok = action_result_data.get("ok", False)
                    break
        post_rover = self._world.get_agents().get(self.agent_id) or {}
        is_fallback = _is_fallback
        current_tick = self._world.get_tick()
        training_turn = TrainingTurn(
            tick=current_tick,
            agent_id=self.agent_id,
            agent_type="rover",
            context=context_text,
            world_snapshot=world_snap,
            thinking=turn.get("thinking"),
            action_name=action_name,
            action_params=action_params,
            action_result=action_result_data,
            action_ok=action_ok,
            battery_before=pre_battery,
            battery_after=post_rover.get("battery", 1.0),
            position_before=pre_position,
            position_after=list(post_rover.get("position", [0, 0])),
            goal_confidence_before=pre_confidence,
            goal_confidence_after=post_rover.get("goal_confidence", 0.5),
            model=getattr(self._reasoner, "model", ""),
            is_fallback=is_fallback,
            llm_duration_ms=llm_ms,
        )
        training_logger.log_turn(training_turn)
        training_logger.log_world_snapshot(current_tick, get_snapshot())

        # --- Periodic memory summarization ---
        current_tick = self._world.get_tick()
        if current_tick % 20 == 0:
            from .world import summarize_memories, record_strategic_insight

            prompt = summarize_memories(self.agent_id)
            if prompt:
                try:
                    client = get_mistral_client()
                    resp = await asyncio.to_thread(
                        client.chat.complete,
                        model="mistral-small-latest",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=150,
                    )
                    insight_choice = safe_get_choice(resp, "strategic insight")
                    insight_text = (insight_choice.message.content or "").strip()
                    record_strategic_insight(self.agent_id, insight_text, current_tick)
                    await broadcaster.send(
                        {
                            "type": "event",
                            "name": "insight",
                            "source": self.agent_id,
                            "payload": {"text": insight_text},
                        }
                    )
                    logger.info("Strategic insight for %s: %s", self.agent_id, insight_text)
                except Exception as exc:
                    logger.warning("Memory summarization failed for %s: %s", self.agent_id, exc)

        # Auto-charge rover when it arrives at station
        rover = self._world.get_agents().get(self.agent_id)
        if (
            rover
            and station_agent
            and rover["position"] == station_agent["position"]
            and rover["battery"] < 1.0
        ):
            charge_result = charge_agent(self.agent_id)
            if charge_result["ok"]:
                charge_msg = make_message(
                    source="station",
                    type="action",
                    name="charge_agent",
                    payload=charge_result,
                )
                await host.broadcast(charge_msg.to_dict())


class RoverMistralLoop(RoverLoop):
    """Rover loop wired to MistralRoverReasoner."""

    def __init__(
        self, agent_id: str = "rover-mistral", interval: float = 3.0, world: World | None = None
    ):
        super().__init__(agent_id=agent_id, interval=interval, world=world)
        self._reasoner = MistralRoverReasoner(agent_id=self.agent_id, world=self._world)
        set_agent_model(self.agent_id, self._reasoner.model)


class RoverLargeLoop(RoverLoop):
    """Rover loop wired to MistralRoverReasoner using mistral-large-latest."""

    def __init__(
        self, agent_id: str = "rover-large", interval: float = 3.0, world: World | None = None
    ):
        super().__init__(agent_id=agent_id, interval=interval, world=world)
        self._reasoner = MistralRoverReasoner(
            agent_id=self.agent_id, model="mistral-large-latest", world=self._world
        )
        set_agent_model(self.agent_id, self._reasoner.model)


class RoverMediumLoop(RoverLoop):
    """Rover loop wired to MistralRoverReasoner using mistral-medium-latest."""

    def __init__(
        self, agent_id: str = "rover-medium", interval: float = 3.0, world: World | None = None
    ):
        super().__init__(agent_id=agent_id, interval=interval, world=world)
        self._reasoner = MistralRoverReasoner(
            agent_id=self.agent_id, model="mistral-medium-latest", world=self._world
        )
        set_agent_model(self.agent_id, self._reasoner.model)


class RoverCodestralLoop(RoverLoop):
    """Rover loop wired to MistralRoverReasoner using codestral-latest."""

    def __init__(
        self, agent_id: str = "rover-codestral", interval: float = 3.0, world: World | None = None
    ):
        super().__init__(agent_id=agent_id, interval=interval, world=world)
        self._reasoner = MistralRoverReasoner(
            agent_id=self.agent_id, model="codestral-latest", world=self._world
        )
        set_agent_model(self.agent_id, self._reasoner.model)


class RoverMinistralLoop(RoverLoop):
    """Rover loop wired to MistralRoverReasoner using ministral-8b-latest."""

    def __init__(
        self, agent_id: str = "rover-ministral", interval: float = 3.0, world: World | None = None
    ):
        super().__init__(agent_id=agent_id, interval=interval, world=world)
        self._reasoner = MistralRoverReasoner(
            agent_id=self.agent_id, model="ministral-8b-latest", world=self._world
        )
        set_agent_model(self.agent_id, self._reasoner.model)


class RoverMagistralLoop(RoverLoop):
    """Rover loop wired to MistralRoverReasoner using magistral-small-latest."""

    def __init__(
        self, agent_id: str = "rover-magistral", interval: float = 3.0, world: World | None = None
    ):
        super().__init__(agent_id=agent_id, interval=interval, world=world)
        self._reasoner = MistralRoverReasoner(
            agent_id=self.agent_id, model="magistral-small-latest", world=self._world
        )
        set_agent_model(self.agent_id, self._reasoner.model)


class DroneLoop(BaseAgent):
    """Generic drone tick: reason → execute → broadcast."""

    _reasoner: DroneAgent | MockDroneAgent

    async def tick(self, host) -> None:
        mission_status = self._world.get_mission()["status"]
        drone = self._world.get_agents().get(self.agent_id)
        station_agent = self._world.get_agents().get("station")

        # If aborted and at station, stop this agent
        if (
            mission_status == "aborted"
            and drone
            and station_agent
            and drone["position"] == station_agent["position"]
        ):
            logger.info("Agent %s at station — abort complete", self.agent_id)
            return

        # During abort, force recall so drone heads to station
        if mission_status == "aborted":
            self._world.set_pending_commands(
                self.agent_id,
                [{"name": "recall", "payload": {"reason": "Mission aborted — return to station"}}],
            )

        # ── Training: capture pre-state ──
        _drone_state = self._world.get_agents().get(self.agent_id, {})
        _pre_position = list(_drone_state.get("position", [0, 0]))
        _pre_battery = _drone_state.get("battery", 1.0)
        _pre_confidence = _drone_state.get("goal_confidence", 0.5)
        _t0 = time.monotonic()
        turn = await asyncio.to_thread(self._reasoner.run_turn)
        _llm_ms = int((time.monotonic() - _t0) * 1000)
        _action_result = {}
        _action_ok = False
        _tick, _power_events, _timeline_events = next_tick()
        messages = []

        for tevt in _timeline_events:
            messages.append(
                make_message(
                    source="world", type="event", name=tevt["name"], payload=tevt["payload"]
                )
            )

        if turn["thinking"]:
            msg = make_message(
                source=self.agent_id,
                type="event",
                name="thinking",
                payload={
                    "text": turn["thinking"],
                    "structured": _parse_structured_thinking(turn["thinking"]),
                },
            )
            messages.append(msg)

        if turn["action"]:
            # Auto-confirm gate: check for hazardous move conditions
            _gate_result = await _auto_confirm_gate(
                host, self.agent_id, turn["action"]["name"], turn["action"]["params"]
            )
            if _gate_result is not None:
                result = _gate_result
            else:
                result = execute_action(
                    self.agent_id,
                    turn["action"]["name"],
                    turn["action"]["params"],
                )
            _action_result = result
            _action_ok = result.get("ok", False)
            if result["ok"]:
                action_msg = make_message(
                    source=self.agent_id,
                    type="action",
                    name=turn["action"]["name"],
                    payload=result,
                )
                messages.append(action_msg)

                # Save notify to station memory and emit station thinking log
                if turn["action"]["name"] == "notify" and result.get("message"):
                    pos = result["position"]
                    station_state = self._world.get_agents().get("station")
                    if station_state:
                        mem = station_state.setdefault("memory", [])
                        mem.append(
                            f"Radio from {self.agent_id} at ({pos[0]},{pos[1]}): {result['message']}"
                        )
                    station_log = make_message(
                        source="station",
                        type="event",
                        name="thinking",
                        payload={
                            "text": f"Radio from {self.agent_id} at ({pos[0]},{pos[1]}): {result['message']}"
                        },
                    )
                    messages.append(station_log)

                # Auto-relay high-concentration scan results to all active rovers
                if turn["action"]["name"] == "scan" and result.get("concentration", 0) > 0.5:
                    for rid, rdata in self._world.get_agents().items():
                        if rdata.get("type") != "rover":
                            continue
                        relay_msg = send_agent_message(
                            self.agent_id,
                            rid,
                            f"High concentration {result['concentration']:.2f} at {result.get('position', '?')}",
                        )
                        relay_event = make_message(
                            source=self.agent_id,
                            type="event",
                            name="intel_relay",
                            payload={
                                "from": self.agent_id,
                                "to": rid,
                                "message": relay_msg["message"],
                            },
                        )
                        messages.append(relay_event)

        # LLM-owned task: update agent tasks from LLM output
        llm_task = turn.get("task")
        if llm_task is not None:
            agent_state = self._world.get_agent(self.agent_id)
            old_task = agent_state.get("tasks", [None])[0]
            if llm_task != old_task:
                agent_state["tasks"] = [llm_task]
                task_msg = make_message(
                    source=self.agent_id,
                    type="event",
                    name="task_update",
                    payload={"task": llm_task},
                )
                messages.append(task_msg)

        # ── Goal confidence update (drone) ──
        if turn["action"]:
            if _action_ok:
                update_goal_confidence(self.agent_id, 0.05)
            else:
                update_goal_confidence(self.agent_id, -0.05)
        if turn.get("is_fallback", False):
            update_goal_confidence(self.agent_id, -0.08)

        for msg in messages:
            await host.broadcast(msg.to_dict())

        await broadcaster.send(make_message("world", "event", "state", get_snapshot()).to_dict())

        # ── Training: log drone turn ──
        try:
            _post_drone = self._world.get_agents().get(self.agent_id, {})
            _action = turn.get("action") or {}
            training_turn = TrainingTurn(
                tick=self._world.get_tick(),
                agent_id=self.agent_id,
                agent_type="drone",
                context=getattr(self._reasoner, "last_context", ""),
                world_snapshot=_build_turn_snapshot(_drone_state, self._world),
                thinking=turn.get("thinking"),
                action_name=_action.get("name", ""),
                action_params=_action.get("params", {}),
                action_result=_action_result,
                action_ok=_action_ok,
                battery_before=_pre_battery,
                battery_after=_post_drone.get("battery", 1.0),
                position_before=_pre_position,
                position_after=list(_post_drone.get("position", [0, 0])),
                goal_confidence_before=_pre_confidence,
                goal_confidence_after=_post_drone.get("goal_confidence", 0.5),
                model=getattr(self._reasoner, "model", ""),
                is_fallback=turn.get("is_fallback", False),
                llm_duration_ms=_llm_ms,
            )
            training_logger.log_turn(training_turn)
            training_logger.log_world_snapshot(self._world.get_tick(), get_snapshot())
        except Exception:
            logger.warning("Training turn logging failed for %s", self.agent_id, exc_info=True)

        # Auto-charge drone when at station
        drone = self._world.get_agents().get(self.agent_id)
        if (
            drone
            and station_agent
            and drone["position"] == station_agent["position"]
            and drone["battery"] < 1.0
        ):
            charge_result = charge_agent(self.agent_id)
            if charge_result["ok"]:
                charge_msg = make_message(
                    source="station",
                    type="action",
                    name="charge_agent",
                    payload=charge_result,
                )
                await host.broadcast(charge_msg.to_dict())


class DroneMistralLoop(DroneLoop):
    """Drone loop wired to DroneAgent (Mistral)."""

    def __init__(self, interval: float = 2.0, world: World | None = None):
        super().__init__(agent_id="drone-mistral", interval=interval, world=world)
        self._reasoner = DroneAgent(agent_id=self.agent_id, world=self._world)
        set_agent_model(self.agent_id, self._reasoner.model)


class HaulerLoop(BaseAgent):
    """Generic hauler tick: reason -> execute -> broadcast."""

    _reasoner: HaulerAgent

    async def tick(self, host) -> None:
        mission_status = self._world.get_mission()["status"]

        # Inject pending commands
        pending = host.drain_inbox(self.agent_id)
        if mission_status == "aborted":
            pending = [
                {"name": "recall", "payload": {"reason": "Mission aborted — return to station"}}
            ]
        self._world.set_pending_commands(self.agent_id, pending if pending else None)

        # If aborted and at station, stop
        hauler = self._world.get_agents().get(self.agent_id)
        station_agent = self._world.get_agents().get("station")
        if (
            mission_status == "aborted"
            and hauler
            and station_agent
            and hauler["position"] == station_agent["position"]
        ):
            logger.info("Agent %s at station — abort complete", self.agent_id)
            return

        turn = await asyncio.to_thread(self._reasoner.run_turn)
        _tick, _power_events, _timeline_events = next_tick()

        messages = []
        for tevt in _timeline_events:
            messages.append(
                make_message(
                    source="world", type="event", name=tevt["name"], payload=tevt["payload"]
                )
            )
        if turn["thinking"]:
            messages.append(
                make_message(
                    source=self.agent_id,
                    type="event",
                    name="thinking",
                    payload={
                        "text": turn["thinking"],
                        "structured": _parse_structured_thinking(turn["thinking"]),
                    },
                )
            )

        if turn["action"]:
            # Auto-confirm gate: check for hazardous move conditions
            _gate_result = await _auto_confirm_gate(
                host, self.agent_id, turn["action"]["name"], turn["action"]["params"]
            )
            if _gate_result is not None:
                result = _gate_result
            else:
                result = execute_action(
                    self.agent_id,
                    turn["action"]["name"],
                    turn["action"]["params"],
                )
            if result["ok"]:
                messages.append(
                    make_message(
                        source=self.agent_id,
                        type="action",
                        name=turn["action"]["name"],
                        payload=result,
                    )
                )

                if turn["action"]["name"] == "notify" and result.get("message"):
                    pos = result["position"]
                    station_state = self._world.get_agents().get("station")
                    if station_state:
                        mem = station_state.setdefault("memory", [])
                        mem.append(
                            f"Radio from {self.agent_id} at ({pos[0]},{pos[1]}): {result['message']}"
                        )

        # ── Goal confidence update (hauler) ──
        if turn["action"]:
            _h_result_ok = any(
                (m.to_dict() if hasattr(m, "to_dict") else m).get("type") == "action"
                for m in messages
            )
            if _h_result_ok:
                if turn["action"]["name"] == "deliver":
                    update_goal_confidence(self.agent_id, 0.10)
                else:
                    update_goal_confidence(self.agent_id, 0.05)
            else:
                update_goal_confidence(self.agent_id, -0.05)

        for msg in messages:
            await host.broadcast(msg.to_dict())

        await broadcaster.send(make_message("world", "event", "state", get_snapshot()).to_dict())

        # Auto-charge hauler at station
        station_agent = self._world.get_agents().get("station")
        hauler = self._world.get_agents().get(self.agent_id)
        if (
            hauler
            and station_agent
            and hauler["position"] == station_agent["position"]
            and hauler["battery"] < 1.0
        ):
            charge_result = charge_agent(self.agent_id)
            if charge_result["ok"]:
                await host.broadcast(
                    make_message(
                        source="station",
                        type="action",
                        name="charge_agent",
                        payload=charge_result,
                    ).to_dict()
                )


class RoverHuggingFaceLoop(RoverLoop):
    """Rover loop wired to HuggingFaceRoverReasoner."""

    def __init__(
        self, agent_id: str = "rover-huggingface", interval: float = 3.0, world: World | None = None
    ):
        super().__init__(agent_id=agent_id, interval=interval, world=world)
        self._reasoner = HuggingFaceRoverReasoner(agent_id=self.agent_id, world=self._world)
        set_agent_model(self.agent_id, self._reasoner.model)


class DroneHuggingFaceLoop(DroneLoop):
    """Drone loop wired to HuggingFaceDroneAgent."""

    def __init__(self, interval: float = 2.0, world: World | None = None):
        super().__init__(agent_id="drone-huggingface", interval=interval, world=world)
        self._reasoner = HuggingFaceDroneAgent(agent_id=self.agent_id, world=self._world)
        set_agent_model(self.agent_id, self._reasoner.model)


# ── Station reactive loop ────────────────────────────────────────────────────────


class StationLoop(BaseAgent):
    """Station periodic evaluation loop — monitors field events and coordinates agents."""

    INTERESTING_EVENTS = frozenset(
        {
            "thinking",
            "notify",
            "check",
            "dig",
            "analyze",
            "scan",
            "world_event",
            "mission_success",
            "mission_failed",
            "mission_aborted",
            "charge_agent",
            "deploy_solar_panel",
            "use_solar_battery",
        }
    )

    def __init__(self, interval: float = 20.0, world: World | None = None):
        super().__init__(agent_id="station-loop", interval=interval, world=world)
        self._station = StationAgent()
        self._event_buffer: list[dict] = []

    def buffer_event(self, event: dict):
        """Buffer a field event for next evaluation cycle."""
        self._event_buffer.append(event)
        if len(self._event_buffer) > 50:
            self._event_buffer = self._event_buffer[-50:]

    async def tick(self, host) -> None:
        if not self._event_buffer:
            return

        context = self._world.observe_station()

        # ── Training: capture pre-state ──
        try:
            _agents = self._world.get_agents()
            station_state = _agents.get("station") or {} if isinstance(_agents, dict) else {}
            pre_position = (
                list(station_state.get("position", [0, 0]))
                if isinstance(station_state, dict)
                else [0, 0]
            )
            pre_battery = (
                station_state.get("battery", 1.0) if isinstance(station_state, dict) else 1.0
            )
        except Exception:
            station_state, pre_position, pre_battery = {}, [0, 0], 1.0
        pre_confidence = (
            station_state.get("goal_confidence", 0.5) if isinstance(station_state, dict) else 0.5
        )
        context_text = str(context) if context else ""
        t0 = time.monotonic()
        result = await asyncio.to_thread(
            self._station.evaluate_situation, context, self._event_buffer
        )
        llm_ms = int((time.monotonic() - t0) * 1000)
        self._event_buffer.clear()

        if result.get("thinking"):
            msg = make_message(
                source="station",
                type="event",
                name="thinking",
                payload={"text": result["thinking"]},
            )
            await host.broadcast(msg.to_dict())

        # Execute actions through Host routing (ensures world-effect)
        await host.route_station_actions(result)

        # ── Goal confidence update (station) ──
        _station_actions = result.get("actions", [])
        if _station_actions:
            update_goal_confidence("station", 0.05)

        # ── Training: log station turn ──
        try:
            actions = result.get("actions", [])
            action_name = actions[0]["name"] if actions else ""
            action_params = actions[0].get("params", {}) if actions else {}
            current_tick = self._world.get_tick()
            _post_agents = self._world.get_agents()
            post_station = (
                _post_agents.get("station") or {} if isinstance(_post_agents, dict) else {}
            )
            training_turn = TrainingTurn(
                tick=current_tick,
                agent_id=getattr(self, "agent_id", "station-loop"),
                agent_type="station",
                context=context_text,
                world_snapshot=_build_turn_snapshot(station_state, self._world)
                if isinstance(station_state, dict) and station_state
                else TurnWorldSnapshot(),
                thinking=result.get("thinking"),
                action_name=action_name,
                action_params=action_params,
                action_result={"actions": [a["name"] for a in actions]},
                action_ok=bool(actions),
                battery_before=pre_battery,
                battery_after=post_station.get("battery", 1.0)
                if isinstance(post_station, dict)
                else 1.0,
                position_before=pre_position,
                position_after=list(post_station.get("position", [0, 0]))
                if isinstance(post_station, dict)
                else [0, 0],
                model=getattr(self._station, "model", "")
                if isinstance(getattr(self._station, "model", None), str)
                else "",
                is_fallback=False,
                llm_duration_ms=llm_ms,
                goal_confidence_before=pre_confidence,
                goal_confidence_after=post_station.get("goal_confidence", 0.5)
                if isinstance(post_station, dict)
                else 0.5,
            )
            training_logger.log_turn(training_turn)
            training_logger.log_world_snapshot(current_tick, get_snapshot())
        except Exception:
            logger.warning("Training turn logging failed for station", exc_info=True)


class HaulerMistralLoop(HaulerLoop):
    """Hauler loop wired to HaulerAgent."""

    def __init__(
        self,
        agent_id: str = "hauler-mistral",
        interval: float = settings.hauler_turn_interval_seconds,
        world: World | None = None,
    ):
        super().__init__(agent_id=agent_id, interval=interval, world=world)
        self._reasoner = HaulerAgent(agent_id=self.agent_id, world=self._world)
        set_agent_model(self.agent_id, self._reasoner.model)


HaulerReasoner = HaulerAgent
