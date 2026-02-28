"""Rover agents — LLM-powered and mock. Return action dicts, never mutate world."""

import json
import logging
import random

from mistralai import Mistral

from .config import settings
from .world import (
    WORLD,
    GRID_W,
    GRID_H,
    DIRECTIONS,
    MAX_MOVE_DISTANCE,
    check_ground,
    _direction_hint,
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

ROVER_TOOLS = [MOVE_TOOL, DIG_TOOL, PICKUP_TOOL]


class RoverAgent:
    """Rover agent that reasons via Mistral. Returns action dict, does not execute."""

    def __init__(self, agent_id="rover-mistral", model="magistral-medium-latest"):
        self.agent_id = agent_id
        self.model = model
        self._client = None

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

        # Stone at current tile (with extracted status)
        ground = check_ground(self.agent_id)
        stone_info = ground["stone"]
        if stone_info:
            if stone_info["extracted"]:
                stone_line = f"{stone_info['type']} (extracted — ready for pickup)"
            else:
                stone_line = f"{stone_info['type']} (buried — needs dig)"
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
            "Your job: explore the grid, find stones, dig them out, pick them up.\n"
            "Think step by step but keep it to 1-2 sentences, then call a tool.\n"
            "\n"
            "COORDINATE SYSTEM:\n"
            "- North = Y decreases, South = Y increases\n"
            "- East = X increases, West = X decreases\n"
            "- To reach a tile with HIGHER Y, move SOUTH. To reach LOWER Y, move NORTH.\n"
            "\n"
            "RULES:\n"
            "- Battery is your lifeline. Each move costs 2%/tile, dig costs 6%, pickup costs 2%.\n"
            "- Station is your base at ({sx},{sy}). You can recharge there.\n"
            "- ALWAYS keep enough battery to return to station. If distance_to_station * 2% "
            "approaches your battery, head back immediately.\n"
            "- If you find a stone: dig it, then pickup. Both must happen on the same tile.\n"
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

        # Short-term memory
        if memory:
            recent = memory[-5:]
            parts.append("\n== Recent actions ==")
            for entry in recent:
                parts.append(f"- {entry}")

        return "\n".join(parts)

    def run_turn(self):
        """Single-shot LLM call. Returns {thinking, action} dict."""
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
            if name in ("move", "dig", "pickup"):
                action = {"name": name, "params": args}

        return {"thinking": thinking, "action": action}


class MockRoverAgent:
    """Mock rover that picks a random valid direction each turn — no LLM calls."""

    def __init__(self, agent_id="randy-rover"):
        self.agent_id = agent_id

    def run_turn(self):
        agent = WORLD["agents"][self.agent_id]
        x, y = agent["position"]
        visited_set = {tuple(p) for p in agent.get("visited", [])}

        valid = []
        unvisited = []
        for name, (dx, dy) in DIRECTIONS.items():
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                valid.append((name, nx, ny))
                if (nx, ny) not in visited_set:
                    unvisited.append((name, nx, ny))

        candidates = unvisited if unvisited else valid
        direction, tx, ty = random.choice(candidates)

        context = (
            f"Mock rover at ({x},{y}), battery={agent['battery']:.0%}, "
            f"visited={len(agent.get('visited', []))}, "
            f'mission="{agent["mission"]["objective"]}"'
        )
        agent["last_context"] = context

        thinking = f"I'm at ({x}, {y}). I'll move {direction} to ({tx}, {ty})."
        action = {"name": "move", "params": {"direction": direction}}

        return {"thinking": thinking, "action": action}
