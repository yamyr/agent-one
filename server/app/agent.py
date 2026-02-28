"""Rover agents — LLM-powered and mock. Return action dicts, never mutate world."""

import json
import logging
import random

from mistralai import Mistral, SDKError

from .config import settings
from .models import RoverContext

logger = logging.getLogger(__name__)

GRID_W, GRID_H = 20, 20
MAX_MOVE_DISTANCE = 3
DIRECTIONS = {
    "north": (0, 1),
    "south": (0, -1),
    "east": (1, 0),
    "west": (-1, 0),
}

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

    def _build_context(self, ctx: RoverContext):
        """Assemble LLM context from typed RoverContext."""
        x, y = ctx.agent.position
        mission = ctx.agent.mission
        battery = ctx.agent.battery
        inventory = ctx.agent.inventory
        memory = ctx.agent.memory
        station_pos = ctx.world.station_position
        dist_to_station = abs(x - station_pos[0]) + abs(y - station_pos[1])
        moves_on_battery = int(battery / 0.02)
        unvisited_dirs = ctx.computed.unvisited_dirs
        stone_line = ctx.computed.stone_line
        target_type = ctx.world.target_type
        target_count = ctx.world.target_count
        collected = ctx.world.collected_count
        tasks = ctx.agent.tasks
        visible_stones = ctx.computed.visible_stones
        ground_readings = ctx.agent.ground_readings
        grid_w = ctx.world.grid_w
        grid_h = ctx.world.grid_h
        visited_count = ctx.agent.visited_count

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
            f"Objective: {mission.objective}\n"
            f"Target: collect {target_count} {target_type} stones ({collected}/{target_count} done)"
        )

        # Current tasks
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
            + (f" ({', '.join(s.type for s in inventory)})" if inventory else "")
        )

        # Environment
        parts.append(
            f"\n== Environment ==\n"
            f"Grid: {grid_w}x{grid_h}\n"
            f"Tiles visited: {visited_count}\n"
            f"Unvisited neighbors: {', '.join(unvisited_dirs) if unvisited_dirs else 'none'}\n"
            f"Stone here: {stone_line}"
        )
        if visible_stones:
            parts.append("Visible stones nearby:")
            for vs in visible_stones:
                parts.append(f"  - {vs}")

        # Ground concentration readings
        if ground_readings:
            parts.append("Ground concentration readings:")
            for pos, val in ground_readings.items():
                parts.append(f"  - ({pos}): {val:.3f}")

        # Short-term memory
        if memory:
            recent = memory[-5:]
            parts.append("\n== Recent actions ==")
            for entry in recent:
                parts.append(f"- {entry}")

        return "\n".join(parts)

    def run_turn(self, context: RoverContext):
        """Single-shot LLM call. Returns {thinking, action} dict."""
        try:
            client = self._get_client()
            ctx_text = self._build_context(context)

            messages = [
                {"role": "system", "content": ctx_text},
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
                return self._fallback_turn("No valid tool action from model", context)

            return {"thinking": thinking, "action": action}
        except (SDKError, ConnectionError, TimeoutError, RuntimeError) as exc:
            logger.exception("Rover LLM turn failed for %s, using fallback", self.agent_id)
            return self._fallback_turn(f"LLM unavailable ({type(exc).__name__})", context)

    def _fallback_turn(self, reason, context):
        fallback = self._mock_fallback.run_turn(context)
        fallback_thinking = fallback.get("thinking") or ""
        prefix = f"LLM fallback: {reason}. "
        fallback["thinking"] = (prefix + fallback_thinking).strip()
        return fallback


class MockRoverAgent:
    """Mock rover that explores, collects stones, and returns to station — no LLM calls."""

    def __init__(self, agent_id="rover-mock"):
        self.agent_id = agent_id

    def run_turn(self, context: RoverContext):
        """Decide next action from typed RoverContext."""
        x, y = context.agent.position
        battery = context.agent.battery
        mission = context.agent.mission
        target_type = context.world.target_type
        inventory = context.agent.inventory
        station_pos = context.world.station_position
        stone_here = context.computed.stone_here
        visited = context.agent.visited
        grid_w = context.world.grid_w
        grid_h = context.world.grid_h

        # Check for stone at current tile — analyze, dig, or pickup
        if stone_here:
            if not stone_here.analyzed:
                thinking = f"I'm at ({x}, {y}). Found an unknown stone — analyzing."
                return {"thinking": thinking, "action": {"name": "analyze", "params": {}}}
            elif not stone_here.extracted:
                thinking = f"I'm at ({x}, {y}). Found a {stone_here.type} stone — digging."
                return {"thinking": thinking, "action": {"name": "dig", "params": {}}}
            else:
                thinking = f"I'm at ({x}, {y}). Stone extracted — picking up."
                return {"thinking": thinking, "action": {"name": "pickup", "params": {}}}

        # If carrying target stone, navigate toward station
        has_target = any(s.type == target_type for s in inventory)
        if has_target:
            sp = station_pos
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
        visited_set = {tuple(p) for p in visited}
        valid = []
        unvisited = []
        for name, (ddx, ddy) in DIRECTIONS.items():
            nx, ny = x + ddx, y + ddy
            if 0 <= nx < grid_w and 0 <= ny < grid_h:
                valid.append((name, nx, ny))
                if (nx, ny) not in visited_set:
                    unvisited.append((name, nx, ny))

        candidates = unvisited if unvisited else valid
        direction, tx, ty = random.choice(candidates)

        thinking = f"I'm at ({x}, {y}). I'll move {direction} to ({tx}, {ty})."
        action = {"name": "move", "params": {"direction": direction}}

        return {"thinking": thinking, "action": action}
