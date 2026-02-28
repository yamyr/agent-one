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
    MAX_MOVE_DISTANCE_DRONE,
    FUEL_CAPACITY_ROVER,
    FUEL_CAPACITY_DRONE,
    BATTERY_COST_MOVE,
    BATTERY_COST_MOVE_DRONE,
    BATTERY_COST_DIG,
    BATTERY_COST_PICKUP,
    BATTERY_COST_ANALYZE,
    BATTERY_COST_ANALYZE_GROUND,
    BATTERY_COST_SCAN,
    BATTERY_SAFETY_MARGIN,
    RETURN_TO_BASE_THRESHOLD,
    check_ground,
    _direction_hint,
    _find_stone_at,
)

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
        "description": f"Dig at current tile to extract a buried stone. Costs 6 fuel units (~{BATTERY_COST_DIG:.2%} battery). The stone must be present and not yet extracted.",
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
        "description": f"Analyze an unknown stone at current tile to reveal its true type (core or basalt). Costs 3 fuel units (~{BATTERY_COST_ANALYZE:.2%} battery). Must be done before dig/pickup.",
        "parameters": {"type": "object", "properties": {}},
    },
}

ANALYZE_GROUND_TOOL = {
    "type": "function",
    "function": {
        "name": "analyze_ground",
        "description": f"Analyze ground concentration at current tile to detect nearby core deposits. Returns a 0.0-1.0 reading (higher = closer to cores). Costs 3 fuel units (~{BATTERY_COST_ANALYZE_GROUND:.2%} battery).",
        "parameters": {"type": "object", "properties": {}},
    },
}

DEPLOY_SOLAR_PANEL_TOOL = {
    "type": "function",
    "function": {
        "name": "deploy_solar_panel",
        "description": "Deploy a solar panel at current tile. Creates a single-use battery pack (25% capacity) that rovers can later consume with use_solar_battery. Each rover carries 2 panels. Costs 1 fuel unit.",
        "parameters": {"type": "object", "properties": {}},
    },
}

USE_SOLAR_BATTERY_TOOL = {
    "type": "function",
    "function": {
        "name": "use_solar_battery",
        "description": "Consume the battery from a deployed solar panel at current tile to recharge. Adds up to 25% battery. Panel is depleted after use. Must be at a tile with an active (non-depleted) solar panel.",
        "parameters": {"type": "object", "properties": {}},
    },
}

ROVER_TOOLS = [MOVE_TOOL, ANALYZE_TOOL, DIG_TOOL, PICKUP_TOOL, ANALYZE_GROUND_TOOL, DEPLOY_SOLAR_PANEL_TOOL, USE_SOLAR_BATTERY_TOOL]


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
        moves_on_battery = int(battery / BATTERY_COST_MOVE)

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
            f"- Battery is your lifeline. Move costs 1 fuel unit/tile (~{BATTERY_COST_MOVE:.2%}), dig 6 units (~{BATTERY_COST_DIG:.2%}), analyze 3 units (~{BATTERY_COST_ANALYZE:.2%}), pickup 2 units (~{BATTERY_COST_PICKUP:.2%}).\n"
            "- Station is your base at ({sx},{sy}). Return there when battery is low — "
            "the station will recharge you automatically.\n"
            "- ALWAYS keep enough battery to return to station. When your battery drops to 67% or below, \n"
            "head back to station IMMEDIATELY — this is the return-to-base threshold.\n"
            "- SOLAR PANELS: You carry 2 solar panels. Deploy them (deploy_solar_panel) when you're exploring\n"
            "far from station and your battery is getting low (~40-50%). Place them at strategic locations\n"
            "along your exploration route so you can recharge on the way back. Each panel has a 25% battery pack.\n"
            "Use use_solar_battery when you're at a panel tile and need charge. Panels are single-use.\n"
            "Consider the environment: deploy panels at intersections of exploration paths or near stone deposits.\n"
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
            f"Battery: {battery:.0%} ({moves_on_battery} moves remaining, {FUEL_CAPACITY_ROVER} fuel capacity)\n"
            f"Distance to station: {dist_to_station} tiles\n"
            f"Safety margin: {'OK' if battery > RETURN_TO_BASE_THRESHOLD else 'LOW — return to station immediately'}\n"
            f"Inventory: {len(inventory)} stones"
            + (f" ({', '.join(s['type'] for s in inventory)})" if inventory else "")
        )

        # Solar panel info
        panels_remaining = agent.get("solar_panels_remaining", 0)
        nearby_panels = []
        for panel in WORLD.get("solar_panels", []):
            pd = abs(panel["position"][0] - x) + abs(panel["position"][1] - y)
            if pd <= 15:
                status = "depleted" if panel["depleted"] else f"{panel['battery']:.0%} charge"
                nearby_panels.append(f"  ({panel['position'][0]},{panel['position'][1]}) — {status}, {pd} tiles away")
        parts.append(f"Solar panels remaining: {panels_remaining}")
        if nearby_panels:
            parts.append("Nearby solar panels:")
            for np in nearby_panels:
                parts.append(np)

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
            f"solar_panels={agent.get('solar_panels_remaining', 0)}, "
            f'mission="{agent["mission"]["objective"]}"'
        )
        agent["last_context"] = context

        # If standing on an active solar panel and battery < 100%, use it
        for panel in WORLD.get("solar_panels", []):
            if panel["position"] == [x, y] and not panel["depleted"] and agent["battery"] < 1.0:
                thinking = f"I'm at ({x}, {y}). 🔋 Found solar panel — using battery to recharge!"
                return {"thinking": thinking, "action": {"name": "use_solar_battery", "params": {}}}

        # CRITICAL: battery safety — return to base if battery is low
        from .world import must_return_to_base, _nearest_solar_panel

        if must_return_to_base(agent):
            # Check for a nearby solar panel first
            panel = _nearest_solar_panel(x, y)
            if panel:
                px, py = panel["position"]
                panel_dist = abs(px - x) + abs(py - y)
                panel_cost = panel_dist * BATTERY_COST_MOVE
                if agent["battery"] > panel_cost + BATTERY_SAFETY_MARGIN:
                    dx, dy = px - x, py - y
                    if abs(dx) >= abs(dy) and dx != 0:
                        direction = "east" if dx > 0 else "west"
                        distance = min(abs(dx), MAX_MOVE_DISTANCE)
                    elif dy != 0:
                        direction = "north" if dy > 0 else "south"
                        distance = min(abs(dy), MAX_MOVE_DISTANCE)
                    else:
                        direction = "north"
                        distance = 1
                    thinking = f"I'm at ({x}, {y}). 🔋 LOW BATTERY — heading to solar panel at ({px},{py})!"
                    return {
                        "thinking": thinking,
                        "action": {"name": "move", "params": {"direction": direction, "distance": distance}},
                    }

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
                direction = "north"
                distance = 1
            thinking = f"I'm at ({x}, {y}). ⚠️ LOW BATTERY ({agent['battery']:.0%}) — must return to station!"
            return {
                "thinking": thinking,
                "action": {"name": "move", "params": {"direction": direction, "distance": distance}},
            }

        # Deploy solar panel when battery getting low and far from any charge source
        station = WORLD["agents"].get("station")
        sp = station["position"] if station else [0, 0]
        dist_to_station = abs(x - sp[0]) + abs(y - sp[1])
        panels_remaining = agent.get("solar_panels_remaining", 0)
        if panels_remaining > 0 and agent["battery"] < 0.45 and dist_to_station >= 8:
            # Don't deploy if there's already a panel nearby
            existing_nearby = False
            for panel in WORLD.get("solar_panels", []):
                if not panel["depleted"]:
                    pd = abs(panel["position"][0] - x) + abs(panel["position"][1] - y)
                    if pd < 8:
                        existing_nearby = True
                        break
            if not existing_nearby:
                thinking = f"I'm at ({x}, {y}). Battery at {agent['battery']:.0%}, {dist_to_station} tiles from station. Deploying solar panel!"
                return {"thinking": thinking, "action": {"name": "deploy_solar_panel", "params": {}}}

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
            dx, dy = sp[0] - x, sp[1] - y
            if dx != 0:
                direction = "east" if dx > 0 else "west"
                distance = min(abs(dx), MAX_MOVE_DISTANCE)
            elif dy != 0:
                direction = "north" if dy > 0 else "south"
                distance = min(abs(dy), MAX_MOVE_DISTANCE)
            else:
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

        # Default: explore unvisited tiles (infinite grid — no boundary check)
        visited_set = {tuple(p) for p in agent.get("visited", [])}
        valid = []
        unvisited = []
        for name, (ddx, ddy) in DIRECTIONS.items():
            nx, ny = x + ddx, y + ddy
            valid.append((name, nx, ny))
            if (nx, ny) not in visited_set:
                unvisited.append((name, nx, ny))

        candidates = unvisited if unvisited else valid
        direction, tx, ty = random.choice(candidates)

        thinking = f"I'm at ({x}, {y}). I'll move {direction} to ({tx}, {ty})."
        action = {"name": "move", "params": {"direction": direction}}

        return {"thinking": thinking, "action": action}


# ---------------------------------------------------------------------------
# Drone agent (aerial scout)
# ---------------------------------------------------------------------------

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
        "Returns probability values for surrounding tiles indicating likelihood of precious "
        f"stone deposits. Higher values mean closer to core deposits. Costs 2 fuel units (~{BATTERY_COST_SCAN:.2%} battery).",
        "parameters": {"type": "object", "properties": {}},
    },
}

DRONE_TOOLS = [DRONE_MOVE_TOOL, SCAN_TOOL]


class DroneAgent:
    """Drone scout agent powered by Mistral LLM. Moves fast, scans for stone deposits."""

    def __init__(self, agent_id="drone-mistral", model="mistral-small-latest"):
        self.agent_id = agent_id
        self.model = model
        self._client = None
        self._mock_fallback = MockDroneAgent(agent_id=agent_id)

    def _get_client(self):
        if self._client is None:
            if not settings.mistral_api_key:
                raise RuntimeError("MISTRAL_API_KEY not set")
            self._client = Mistral(api_key=settings.mistral_api_key)
        return self._client

    def _build_context(self):
        """Assemble LLM context for the drone scout."""
        agent = WORLD["agents"][self.agent_id]
        x, y = agent["position"]
        mission = agent["mission"]
        battery = agent["battery"]
        memory = agent.get("memory", [])

        station = WORLD["agents"].get("station")
        station_pos = station["position"] if station else [0, 0]
        dist_to_station = abs(x - station_pos[0]) + abs(y - station_pos[1])
        moves_on_battery = int(battery / BATTERY_COST_MOVE_DRONE)

        visited_set = {tuple(p) for p in agent.get("visited", [])}
        unvisited_dirs = []
        for name, (dx, dy) in DIRECTIONS.items():
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H and (nx, ny) not in visited_set:
                unvisited_dirs.append(name)

        scanned_positions = {tuple(s["position"]) for s in WORLD.get("drone_scans", [])}
        total_tiles = GRID_W * GRID_H
        coverage = len(scanned_positions) / total_tiles * 100

        parts = []

        parts.append(
            f"You are {self.agent_id}, an autonomous Mars drone scout.\n"
            "Your job: fly over the terrain and SCAN areas to detect concentration of precious stone deposits.\n"
            "You are a pure scout — you CANNOT dig or pick up stones. Rovers depend on your scan data.\n"
            "Think step by step but keep it to 1-2 sentences, then call a tool.\n"
            "\n"
            "COORDINATE SYSTEM:\n"
            "- North = Y increases, South = Y decreases\n"
            "- East = X increases, West = X decreases\n"
            "\n"
            "SCAN STRATEGY:\n"
            "- Use 'scan' to sample concentration readings at your current position.\n"
            "- Readings range 0.0-1.0. Higher values indicate precious stone deposits nearby.\n"
            "- Scan data is shared with rovers automatically — they will navigate to hotspots you find.\n"
            "- Try to cover the map systematically. Don't scan the same area twice.\n"
            "- Prioritize scanning unexplored areas far from previous scan positions.\n"
            "\n"
            "RULES:\n"
            f"- Battery: move costs 1 fuel unit/tile (~{BATTERY_COST_MOVE_DRONE:.2%}), scan costs 2 fuel units (~{BATTERY_COST_SCAN:.2%}). You can fly up to {MAX_MOVE_DISTANCE_DRONE} tiles per move.\n"
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
            f"Safety margin: {'OK' if battery > RETURN_TO_BASE_THRESHOLD else 'LOW — return to station'}\n"
            f"Tiles visited: {len(agent.get('visited', []))}\n"
            f"Scans performed: {len(WORLD.get('drone_scans', []))}"
        )

        parts.append(
            f"\n== Environment ==\n"
            f"Grid: {GRID_W}x{GRID_H}\n"
            f"Unvisited neighbors: {', '.join(unvisited_dirs) if unvisited_dirs else 'none'}\n"
            f"Already scanned here: {'yes' if (x, y) in scanned_positions else 'no'}"
        )

        # Recent high-concentration findings
        hot_scans = []
        for scan in WORLD.get("drone_scans", [])[-5:]:
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
            WORLD["agents"][self.agent_id]["last_context"] = context

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
                if name in ("move", "scan"):
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

    def __init__(self, agent_id="drone-mistral"):
        self.agent_id = agent_id

    def run_turn(self):
        agent = WORLD["agents"][self.agent_id]
        x, y = agent["position"]

        context = (
            f"Mock drone at ({x},{y}), battery={agent['battery']:.0%}, "
            f"scans={len(WORLD.get('drone_scans', []))}"
        )
        agent["last_context"] = context

        # CRITICAL: battery safety — return to base if battery is low
        from .world import must_return_to_base

        if must_return_to_base(agent):
            station = WORLD["agents"].get("station")
            sp = station["position"] if station else [0, 0]
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
            thinking = f"I'm at ({x}, {y}). ⚠️ LOW BATTERY ({agent['battery']:.0%}) — must return to station!"
            return {
                "thinking": thinking,
                "action": {
                    "name": "move",
                    "params": {"direction": direction, "distance": distance},
                },
            }

        # Scan if current position not yet scanned
        scanned_positions = {tuple(s["position"]) for s in WORLD.get("drone_scans", [])}
        if (x, y) not in scanned_positions:
            thinking = f"I'm at ({x}, {y}). Scanning area for concentration readings."
            return {"thinking": thinking, "action": {"name": "scan", "params": {}}}

        # Find nearest unscanned position within a search radius
        from .world import DRONE_REVEAL_RADIUS

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
