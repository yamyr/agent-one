"""Rover agents — LLM-powered and mock. Return action dicts, never mutate world."""

import json
import logging
import random

from mistralai import Mistral

from .config import settings
from .world import WORLD, GRID_W, GRID_H, DIRECTIONS, check_ground

logger = logging.getLogger(__name__)

MOVE_TOOL = {
    "type": "function",
    "function": {
        "name": "move",
        "description": "Move the rover one tile in a cardinal direction.",
        "parameters": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["north", "south", "east", "west"],
                    "description": "Direction to move: north, south, east, or west.",
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

    def __init__(self, agent_id="rover-mistral", model="mistral-small-latest"):
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
        """Assemble LLM context from current agent state (sensor readings)."""
        agent = WORLD["agents"][self.agent_id]
        x, y = agent["position"]
        mission = agent["mission"]

        visited = agent.get("visited", [])
        visited_set = {tuple(p) for p in visited}
        unvisited_dirs = []
        for name, (dx, dy) in DIRECTIONS.items():
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H and (nx, ny) not in visited_set:
                unvisited_dirs.append(name)

        ground = check_ground(self.agent_id)
        stone_here = ground["stone"]
        inventory = agent.get("inventory", [])

        system = (
            "You are Rover-1, an autonomous Mars rover.\n"
            "You explore the terrain, find stones, dig them out, and pick them up.\n"
            "Keep responses short (1-2 sentences of reasoning, then act).\n"
            "\n"
            f"Mission: {mission['objective']}\n"
            "\n"
            "== Sensor readings ==\n"
            f"Position: ({x}, {y})\n"
            f"Grid bounds: {GRID_W}x{GRID_H} (0-indexed)\n"
            f"Battery: {agent['battery']:.0%}\n"
            f"Tiles visited: {len(visited)}\n"
            f"Unvisited neighbors: {', '.join(unvisited_dirs) if unvisited_dirs else 'none'}\n"
            f"Stone at current tile: {stone_here['type'] if stone_here else 'none'}\n"
            f"Inventory: {len(inventory)} stones ({', '.join(s['type'] for s in inventory) if inventory else 'empty'})\n"
        )
        return system

    def run_turn(self):
        """Single-shot LLM call. Returns {thinking, action} dict."""
        client = self._get_client()

        messages = [
            {"role": "system", "content": self._build_context()},
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

    def __init__(self, agent_id="rover-mock"):
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

        thinking = f"I'm at ({x}, {y}). I'll move {direction} to ({tx}, {ty})."
        action = {"name": "move", "params": {"direction": direction}}

        return {"thinking": thinking, "action": action}
