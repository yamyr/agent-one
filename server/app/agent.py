"""Rover agents — LLM-powered and mock. Return action dicts, never mutate world."""

import json
import logging
import random

from mistralai import Mistral, SDKError

from .config import settings
from .world import (
    WORLD,
    GRID_W,
    GRID_H,
    DIRECTIONS,
    MAX_MOVE_DISTANCE,
    check_ground,
    _direction_hint,
    _find_stone_at,
)

logger = logging.getLogger(__name__)

MOVE_TOOL = {
    "type": "function",
    "function": {
        "name": "move",
        "description": f"Move the rover 1-{MAX_MOVE_DISTANCE} tiles in a cardinal direction. Costs 2% battery per tile.",
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
        "description": "Dig at current tile to extract a buried stone. Costs 6% battery. The stone must be present and not yet extracted.",
        "parameters": {"type": "object", "properties": {}},
    },
}

PICKUP_TOOL = {
    "type": "function",
    "function": {
        "name": "pickup",
        "description": "Pick up an extracted stone at current tile into inventory. The stone must have been dug out first.",
        "parameters": {"type": "object", "properties": {}},
    },
}

ANALYZE_TOOL = {
    "type": "function",
    "function": {
        "name": "analyze",
        "description": "Analyze an unknown stone at current tile to reveal its true type (core or basalt). Costs 3% battery. Must be done before dig/pickup.",
        "parameters": {"type": "object", "properties": {}},
    },
}

ANALYZE_GROUND_TOOL = {
    "type": "function",
    "function": {
        "name": "analyze_ground",
        "description": "Analyze ground concentration at current tile to detect nearby core deposits. Returns a 0.0-1.0 reading (higher = closer to cores). Costs 3% battery.",
        "parameters": {"type": "object", "properties": {}},
    },
}

ROVER_TOOLS = [MOVE_TOOL, ANALYZE_TOOL, DIG_TOOL, PICKUP_TOOL, ANALYZE_GROUND_TOOL]


class RoverAgent:
    """Rover agent that reasons via Mistral. Returns action dict, does not execute."""

    def __init__(self, agent_id="rover-mistral", model="mistral-small-latest"):
        self.agent_id = agent_id
        self.model = model
        self._client = None
        self._mock_fallback = MockRoverAgent(agent_id=agent_id)

    def _get_client(self):
        if self._client is None:
            if not settings.mistral_api_key:
                raise RuntimeError("MISTRAL_API_KEY not set")
            self._client = Mistral(api_key=settings.mistral_api_key)
        return self._client

    def _build_context(self):
        """Assemble LLM context: identity, state, environment, memory."""
        agent = WORLD["agents"][self.agent_id]
        x, y = agent["position"]
        mission = agent["mission"]
        battery = agent["battery"]
        inventory = agent.get("inventory", [])
        memory = agent.get("memory", [])

        # Station distance
        station = WORLD["agents"].get("station")
        station_pos = station["position"] if station else [0, 0]
        dist_to_station = abs(x - station_pos[0]) + abs(y - station_pos[1])
        moves_on_battery = int(battery / 0.02)

        # Unvisited neighbors
        visited_set = {tuple(p) for p in agent.get("visited", [])}
        unvisited_dirs = []
        for name, (dx, dy) in DIRECTIONS.items():
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H and (nx, ny) not in visited_set:
                unvisited_dirs.append(name)

        # Stone at current tile (with analyzed/extracted status)
        ground = check_ground(self.agent_id)
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

        # Mission target
        world_mission = WORLD.get("mission", {})
        target_type = world_mission.get("target_type", "core")
        target_count = world_mission.get("target_count", 2)
        collected = world_mission.get("collected_count", 0)

        parts = []

        # Identity & behavior
        parts.append(
            f"You are {self.agent_id}, an autonomous Mars rover.\n"
            "Your job: explore the grid, find stones, analyze them, dig them out, pick them up.\n"
            "Think step by step but keep it to 1-2 sentences, then call a tool.\n"
            "\n"
            "COORDINATE SYSTEM:\n"
            "- North = Y increases, South = Y decreases\n"
            "- East = X increases, West = X decreases\n"
            "- To reach a tile with HIGHER Y, move NORTH. To reach LOWER Y, move SOUTH.\n"
            "\n"
            "STONE WORKFLOW:\n"
            "- Stones start as 'unknown'. You must ANALYZE them first to reveal their true type.\n"
            "- After analyzing: DIG to extract, then PICKUP to collect.\n"
            "- Use analyze_ground to read concentration (0.0-1.0). Higher = closer to core deposits.\n"
            "\n"
            "RULES:\n"
            "- Battery is your lifeline. Move costs 2%/tile, dig 6%, analyze 3%, pickup 2%.\n"
            "- Station is your base at ({sx},{sy}). Return there when battery is low — "
            "the station will recharge you automatically.\n"
            "- ALWAYS keep enough battery to return to station. If distance_to_station * 2% "
            "approaches your battery, head back immediately.\n"
            "- If you find an unknown stone: analyze → dig → pickup. All on the same tile.\n"
            "- Once you have collected all target stones, RETURN TO STATION to complete the mission.\n"
            "- Prefer unvisited tiles when exploring. Don't backtrack aimlessly.\n"
            "- Ground is auto-scanned after every move. No need to check manually.\n"
            "- Follow your current tasks list. It tells you exactly what to do next.".format(
                sx=station_pos[0], sy=station_pos[1]
            )
        )

        # Mission objective
        parts.append(
            f"\n== Mission ==\n"
            f"Objective: {mission['objective']}\n"
            f"Target: collect {target_count} {target_type} stones ({collected}/{target_count} done)"
        )

        # Current tasks
        tasks = agent.get("tasks", [])
        if tasks:
            parts.append("\n== Current Tasks ==")
            for i, task in enumerate(tasks, 1):
                parts.append(f"{i}. {task}")
        else:
            parts.append("\n== Current Tasks ==\n1. Explore unvisited tiles to find stones")

        # Internal state
        parts.append(
            f"\n== State ==\n"
            f"Position: ({x}, {y})\n"
            f"Battery: {battery:.0%} ({moves_on_battery} moves remaining)\n"
            f"Distance to station: {dist_to_station} tiles\n"
            f"Safety margin: {'OK' if moves_on_battery > dist_to_station + 3 else 'LOW — consider returning'}\n"
            f"Inventory: {len(inventory)} stones"
            + (f" ({', '.join(s['type'] for s in inventory)})" if inventory else "")
        )

        # Visible stones (on revealed tiles)
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

        # Environment
        parts.append(
            f"\n== Environment ==\n"
            f"Grid: {GRID_W}x{GRID_H}\n"
            f"Tiles visited: {len(agent.get('visited', []))}\n"
            f"Unvisited neighbors: {', '.join(unvisited_dirs) if unvisited_dirs else 'none'}\n"
            f"Stone here: {stone_line}"
        )
        if visible_stones:
            parts.append("Visible stones nearby:")
            for vs in visible_stones:
                parts.append(f"  - {vs}")

        # Ground concentration readings
        readings = agent.get("ground_readings", {})
        if readings:
            parts.append("Ground concentration readings:")
            for pos, val in readings.items():
                parts.append(f"  - ({pos}): {val:.3f}")

        # Short-term memory
        if memory:
            recent = memory[-5:]
            parts.append("\n== Recent actions ==")
            for entry in recent:
                parts.append(f"- {entry}")

        return "\n".join(parts)

    def run_turn(self):
        """Single-shot LLM call. Returns {thinking, action} dict."""
        try:
            client = self._get_client()
            context = self._build_context()
            WORLD["agents"][self.agent_id]["last_context"] = context

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
                if name in ("move", "dig", "pickup", "analyze", "analyze_ground"):
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
        fallback = self._mock_fallback.run_turn()
        fallback_thinking = fallback.get("thinking") or ""
        prefix = f"LLM fallback: {reason}. "
        fallback["thinking"] = (prefix + fallback_thinking).strip()
        return fallback


class MockRoverAgent:
    """Mock rover that explores, collects stones, and returns to station — no LLM calls."""

    def __init__(self, agent_id="rover-mock"):
        self.agent_id = agent_id

    def run_turn(self):
        agent = WORLD["agents"][self.agent_id]
        x, y = agent["position"]
        mission = WORLD.get("mission", {})
        target_type = mission.get("target_type", "core")

        context = (
            f"Mock rover at ({x},{y}), battery={agent['battery']:.0%}, "
            f"visited={len(agent.get('visited', []))}, "
            f'mission="{agent["mission"]["objective"]}"'
        )
        agent["last_context"] = context

        # Check for stone at current tile — analyze, dig, or pickup
        stone_here = _find_stone_at(x, y)
        if stone_here:
            if not stone_here.get("analyzed"):
                thinking = f"I'm at ({x}, {y}). Found an unknown stone — analyzing."
                return {"thinking": thinking, "action": {"name": "analyze", "params": {}}}
            elif not stone_here.get("extracted"):
                thinking = f"I'm at ({x}, {y}). Found a {stone_here['type']} stone — digging."
                return {"thinking": thinking, "action": {"name": "dig", "params": {}}}
            else:
                thinking = f"I'm at ({x}, {y}). Stone extracted — picking up."
                return {"thinking": thinking, "action": {"name": "pickup", "params": {}}}

        # If carrying target stone, navigate toward station
        has_target = any(s["type"] == target_type for s in agent.get("inventory", []))
        if has_target:
            station = WORLD["agents"].get("station")
            sp = station["position"] if station else [0, 0]
            dx, dy = sp[0] - x, sp[1] - y
            if dx != 0:
                direction = "east" if dx > 0 else "west"
                distance = min(abs(dx), MAX_MOVE_DISTANCE)
            elif dy != 0:
                direction = "north" if dy > 0 else "south"
                distance = min(abs(dy), MAX_MOVE_DISTANCE)
            else:
                # Already at station
                direction = "north"
                distance = 1
            thinking = f"I'm at ({x}, {y}). Carrying target stone, heading to station at ({sp[0]},{sp[1]})."
            return {
                "thinking": thinking,
                "action": {
                    "name": "move",
                    "params": {"direction": direction, "distance": distance},
                },
            }

        # Default: explore unvisited tiles
        visited_set = {tuple(p) for p in agent.get("visited", [])}
        valid = []
        unvisited = []
        for name, (ddx, ddy) in DIRECTIONS.items():
            nx, ny = x + ddx, y + ddy
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                valid.append((name, nx, ny))
                if (nx, ny) not in visited_set:
                    unvisited.append((name, nx, ny))

        candidates = unvisited if unvisited else valid
        direction, tx, ty = random.choice(candidates)

        thinking = f"I'm at ({x}, {y}). I'll move {direction} to ({tx}, {ty})."
        action = {"name": "move", "params": {"direction": direction}}

        return {"thinking": thinking, "action": action}
