"""Rover & drone agents — reasoners (sync decision engines) and loops (BaseAgent subclasses).

Reasoners return action dicts, never mutate world (except storing last_context).
Loops own the full observe/reason/act/broadcast cycle via BaseAgent.tick().
"""

import asyncio
import json
import logging
import random

from mistralai import Mistral, SDKError

from .base_agent import BaseAgent
from .broadcast import broadcaster
from .config import settings
from .protocol import make_message
from .world import World, world as default_world
from .world import GRID_W, GRID_H, DIRECTIONS, MAX_MOVE_DISTANCE, MAX_MOVE_DISTANCE_DRONE
from .world import FUEL_CAPACITY_ROVER, FUEL_CAPACITY_DRONE, DRONE_REVEAL_RADIUS
from .world import BATTERY_COST_MOVE, BATTERY_COST_MOVE_DRONE, BATTERY_COST_DIG
from .world import BATTERY_COST_ANALYZE, BATTERY_COST_SCAN, BATTERY_COST_NOTIFY
from .world import MAX_INVENTORY_ROVER
from .world import check_ground, direction_hint
from .world import set_agent_model
from .world import execute_action, get_snapshot, charge_agent, next_tick

logger = logging.getLogger(__name__)

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

ROVER_TOOLS = [
    MOVE_TOOL,
    ANALYZE_TOOL,
    DIG_TOOL,
    DEPLOY_SOLAR_PANEL_TOOL,
    USE_SOLAR_BATTERY_TOOL,
    NOTIFY_TOOL,
]


# ── Rover Reasoners (sync decision engines, read from WORLD) ──


class MistralRoverReasoner:
    """Rover reasoner that decides via Mistral LLM. Returns action dict, does not execute."""

    def __init__(self, agent_id="rover-mistral", model="mistral-small-latest", world: World | None = None):
        self.agent_id = agent_id
        self.model = model
        self._client = None
        self._world = world or default_world

    def _get_client(self):
        if self._client is None:
            if not settings.mistral_api_key:
                raise RuntimeError("MISTRAL_API_KEY not set")
            self._client = Mistral(api_key=settings.mistral_api_key)
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
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H and (nx, ny) not in visited_set:
                unvisited_dirs.append(name)

        # Vein at current tile
        ground = check_ground(self.agent_id)
        stone_info = ground["stone"]
        if stone_info:
            if stone_info["type"] == "unknown":
                stone_line = "unknown vein (needs analyze to reveal grade and quantity)"
            else:
                stone_line = f"{stone_info.get('grade', '?')} vein, qty={stone_info.get('quantity', 0)} (analyzed — needs dig)"
        else:
            stone_line = "none"

        # Mission target
        world_mission = self._world.get_mission()
        target_quantity = world_mission.get("target_quantity", 100)
        inventory_full = len(inventory) >= MAX_INVENTORY_ROVER

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
            "- CRITICAL: Once you have collected the target quantity of basalt, STOP exploring and RETURN TO STATION IMMEDIATELY.\n"
            "- Prefer unvisited tiles when exploring. Don't backtrack aimlessly.\n"
            "- Ground is auto-scanned after every move. No need to check manually.\n"
            "- Follow your current tasks list. It tells you exactly what to do next.".format(
                sx=station_pos[0], sy=station_pos[1]
            )
        )

        parts.append(
            f"\n== Mission ==\n"
            f"Objective: {mission['objective']}\n"
            f"Target: collect {target_quantity} units of basalt and deliver to station.\n"
            f"Your inventory: {len(inventory)}/{MAX_INVENTORY_ROVER} veins"
            + (
                "\n🏁 INVENTORY FULL — RETURN TO STATION NOW TO DELIVER!"
                if inventory_full
                else ""
            )
        )

        tasks = agent.get("tasks", [])
        if tasks:
            parts.append("\n== Current Tasks ==")
            for i, task in enumerate(tasks, 1):
                parts.append(f"{i}. {task}")
        else:
            parts.append("\n== Current Tasks ==\n1. Explore unvisited tiles to find veins")

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
            + (
                "\n⚠️ BATTERY CRITICAL — return to station now!"
                if battery_critical
                else ""
            )
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
            f"Grid: {GRID_W}x{GRID_H}\n"
            f"Tiles visited: {len(agent.get('visited', []))}\n"
            f"Unvisited neighbors: {', '.join(unvisited_dirs) if unvisited_dirs else 'none'}\n"
            f"Vein here: {stone_line}"
        )
        if visible_stones:
            parts.append("Visible veins nearby:")
            for vs in visible_stones:
                parts.append(f"  - {vs}")

        if memory:
            recent = memory[-5:]
            parts.append("\n== Recent actions ==")
            for entry in recent:
                parts.append(f"- {entry}")

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
            response = client.chat.complete(
                model=self.model,
                messages=messages,
                tools=ROVER_TOOLS,
            )
            choice = response.choices[0]

            thinking = choice.message.content or None
            action = None

            if thinking:
                logger.info("Rover thinking: %s", thinking)

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
                ):
                    action = {"name": name, "params": args}
                else:
                    logger.warning("%s called unknown tool %r, ignoring", self.agent_id, name)

            if action is None:
                logger.warning(
                    "%s returned no valid tool action (thinking=%r), using fallback",
                    self.agent_id,
                    thinking,
                )
                return self._fallback_turn("No valid tool action from model")

            return {"thinking": thinking, "action": action}
        except (SDKError, ConnectionError, TimeoutError, RuntimeError) as exc:
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
            valid.append((name, nx, ny))
            if (nx, ny) not in visited_set:
                unvisited.append((name, nx, ny))
        candidates = unvisited if unvisited else valid
        direction, tx, ty = random.choice(candidates)
        thinking = f"LLM fallback: {reason}. Moving {direction} to ({tx},{ty})."
        return {
            "thinking": thinking,
            "action": {"name": "move", "params": {"direction": direction}},
        }


# Backward-compat aliases
RoverAgent = MistralRoverReasoner


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

    def __init__(self, agent_id="drone-mistral", model="mistral-small-latest", world: World | None = None):
        self.agent_id = agent_id
        self.model = model
        self._client = None
        self._world = world or default_world
        self._mock_fallback = MockDroneAgent(agent_id=agent_id, world=self._world)

    def _get_client(self):
        if self._client is None:
            if not settings.mistral_api_key:
                raise RuntimeError("MISTRAL_API_KEY not set")
            self._client = Mistral(api_key=settings.mistral_api_key)
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

        visited_set = {tuple(p) for p in agent.get("visited", [])}
        unvisited_dirs = []
        for name, (dx, dy) in DIRECTIONS.items():
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H and (nx, ny) not in visited_set:
                unvisited_dirs.append(name)

        scanned_positions = {tuple(s["position"]) for s in self._world.get_drone_scans()}
        total_tiles = GRID_W * GRID_H
        coverage = len(scanned_positions) / total_tiles * 100

        parts = []

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
            "- Try to cover the map systematically. Don't scan the same area twice.\n"
            "- Prioritize scanning unexplored areas far from previous scan positions.\n"
            "\n"
            "RADIO (notify tool):\n"
            f"- Costs 2 fuel units (~{BATTERY_COST_NOTIFY:.2%} battery). Use it — your scan findings are critical.\n"
            "- Notify station after every scan that finds a hotspot (peak > 0.5).\n"
            "  Include the position and peak reading so station can dispatch rovers.\n"
            "- Notify station when you have completed a sweep of a region.\n"
            "- Notify station if your battery is low and you cannot cover remaining areas.\n"
            "- You are the eyes of the mission. Rovers are blind without your reports.\n"
            "\n"
            "RULES:\n"
            f"- Battery: move costs 1 fuel unit/tile (~{BATTERY_COST_MOVE_DRONE:.2%}), scan costs 2 fuel units (~{BATTERY_COST_SCAN:.2%}), notify costs 2 fuel units (~{BATTERY_COST_NOTIFY:.2%}). You can fly up to {MAX_MOVE_DISTANCE_DRONE} tiles per move.\n"
            "- Station is at ({sx},{sy}). Return when battery is low for recharge.\n"
            "- ALWAYS keep enough battery to return to station.\n"
            "- Follow your current tasks list.".format(sx=station_pos[0], sy=station_pos[1])
        )

        parts.append(
            f"\n== Mission ==\n"
            f"Objective: {mission['objective']}\n"
            f"Scan coverage: {coverage:.0f}% of map"
        )

        tasks = agent.get("tasks", [])
        if tasks:
            parts.append("\n== Current Tasks ==")
            for i, task in enumerate(tasks, 1):
                parts.append(f"{i}. {task}")
        else:
            parts.append(
                "\n== Current Tasks ==\n1. Scan current area, then fly to unscanned regions"
            )

        parts.append(
            f"\n== State ==\n"
            f"Position: ({x}, {y})\n"
            f"Battery: {battery:.0%} ({moves_on_battery} moves remaining, {FUEL_CAPACITY_DRONE} fuel capacity)\n"
            f"Distance to station: {dist_to_station} tiles\n"
            f"Tiles visited: {len(agent.get('visited', []))}\n"
            f"Scans performed: {len(self._world.get_drone_scans())}"
        )

        parts.append(
            f"\n== Environment ==\n"
            f"Grid: {GRID_W}x{GRID_H}\n"
            f"Unvisited neighbors: {', '.join(unvisited_dirs) if unvisited_dirs else 'none'}\n"
            f"Already scanned here: {'yes' if (x, y) in scanned_positions else 'no'}"
        )

        hot_scans = []
        for scan in self._world.get_drone_scans()[-5:]:
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
            response = client.chat.complete(
                model=self.model,
                messages=messages,
                tools=DRONE_TOOLS,
            )
            choice = response.choices[0]

            thinking = choice.message.content or None
            action = None

            if thinking:
                logger.info("Drone thinking: %s", thinking)

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
                logger.warning(
                    "%s returned no valid tool action, using fallback",
                    self.agent_id,
                )
                return self._fallback_turn("No valid tool action from model")

            return {"thinking": thinking, "action": action}
        except (SDKError, ConnectionError, TimeoutError, RuntimeError) as exc:
            logger.exception("Drone LLM turn failed for %s, using fallback", self.agent_id)
            return self._fallback_turn(f"LLM unavailable ({type(exc).__name__})")

    def _fallback_turn(self, reason):
        fallback = self._mock_fallback.run_turn()
        fallback_thinking = fallback.get("thinking") or ""
        prefix = f"LLM fallback: {reason}. "
        fallback["thinking"] = (prefix + fallback_thinking).strip()
        return fallback


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

        turn = await asyncio.to_thread(self._reasoner.run_turn)
        next_tick()
        messages = []

        if turn["thinking"]:
            msg = make_message(
                source=self.agent_id,
                type="event",
                name="thinking",
                payload={"text": turn["thinking"]},
            )
            messages.append(msg)

        if turn["action"]:
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

                # Emit notify event for station routing
                if turn["action"]["name"] == "notify" and result.get("message"):
                    notify_msg = make_message(
                        source=self.agent_id,
                        type="event",
                        name="notify",
                        payload={"message": result["message"], "position": result["position"]},
                    )
                    messages.append(notify_msg)

                # Don't check mission success/failure during abort
                if mission_status != "aborted":
                    mission_event = result.get("mission")
                    if mission_event:
                        mission_msg = make_message(
                            source="world",
                            type="event",
                            name="mission_" + mission_event["status"],
                            payload=mission_event,
                        )
                        messages.append(mission_msg)

                task_text = result.get("task_update")
                if task_text:
                    task_msg = make_message(
                        source=self.agent_id,
                        type="event",
                        name="task_update",
                        payload={"task": task_text},
                    )
                    messages.append(task_msg)

        for msg in messages:
            await host.broadcast(msg.to_dict())

        await broadcaster.send(make_message("world", "event", "state", get_snapshot()).to_dict())

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
                    name="charge_rover",
                    payload=charge_result,
                )
                await host.broadcast(charge_msg.to_dict())


class RoverMistralLoop(RoverLoop):
    """Rover loop wired to MistralRoverReasoner."""

    def __init__(self, interval: float = 3.0, world: World | None = None):
        super().__init__(agent_id="rover-mistral", interval=interval, world=world)
        self._reasoner = MistralRoverReasoner(agent_id=self.agent_id, world=self._world)
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
            self._world.set_pending_commands(self.agent_id, [
                {"name": "recall", "payload": {"reason": "Mission aborted — return to station"}}
            ])

        turn = await asyncio.to_thread(self._reasoner.run_turn)
        next_tick()
        messages = []

        if turn["thinking"]:
            msg = make_message(
                source=self.agent_id,
                type="event",
                name="thinking",
                payload={"text": turn["thinking"]},
            )
            messages.append(msg)

        if turn["action"]:
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

                # Emit notify event for station routing
                if turn["action"]["name"] == "notify" and result.get("message"):
                    notify_msg = make_message(
                        source=self.agent_id,
                        type="event",
                        name="notify",
                        payload={"message": result["message"], "position": result["position"]},
                    )
                    messages.append(notify_msg)

                task_text = result.get("task_update")
                if task_text:
                    task_msg = make_message(
                        source=self.agent_id,
                        type="event",
                        name="task_update",
                        payload={"task": task_text},
                    )
                    messages.append(task_msg)

        for msg in messages:
            await host.broadcast(msg.to_dict())

        await broadcaster.send(make_message("world", "event", "state", get_snapshot()).to_dict())

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
                    name="charge_rover",
                    payload=charge_result,
                )
                await host.broadcast(charge_msg.to_dict())


class DroneMistralLoop(DroneLoop):
    """Drone loop wired to DroneAgent (Mistral)."""

    def __init__(self, interval: float = 2.0, world: World | None = None):
        super().__init__(agent_id="drone-mistral", interval=interval, world=world)
        self._reasoner = DroneAgent(agent_id=self.agent_id, world=self._world)
        set_agent_model(self.agent_id, self._reasoner.model)
