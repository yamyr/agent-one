"""Agent reasoners using Mistral's Agents API (beta).

Uses client.beta.agents.create() and client.beta.conversations.start()
instead of chat.complete(). Provides rover, drone, and station reasoners.
"""

import json
import logging
import random

from .agent import (
    ROVER_TOOLS,
    DRONE_TOOLS,
    STRUCTURED_REASONING_PROMPT,
    RoverLoop,
    DroneLoop,
    StationLoop,
)
from .config import settings
from .llm import get_mistral_client
from .world import World, world as default_world, set_agent_model
from .world import (
    BATTERY_COST_MOVE_DRONE,
    BATTERY_COST_SCAN,
    FUEL_CAPACITY_DRONE,
    MAX_MOVE_DISTANCE_DRONE,
    DRONE_REVEAL_RADIUS,
)
from .station import STATION_TOOLS
from .models import StationContext
from .world import DIRECTIONS, MAX_MOVE_DISTANCE, FUEL_CAPACITY_ROVER
from .world import (
    BATTERY_COST_MOVE,
    BATTERY_COST_DIG,
    BATTERY_COST_ANALYZE,
    BATTERY_COST_NOTIFY,
    MAX_INVENTORY_ROVER,
    UPGRADES,
)
from .world import check_ground, direction_hint, best_drone_hotspot, observe_rover
from .world import get_drone_intel_for_rover, get_unread_messages, is_obstacle_at, get_storm_info

logger = logging.getLogger(__name__)


def _create_mistral_client():
    """Create a Mistral client using the configured API key."""
    return get_mistral_client()


def _parse_conversation_response(response, agent_id: str) -> tuple:
    """Parse ConversationResponse.outputs into (thinking, actions).

    Returns a tuple of (thinking: str | None, actions: list[dict]).
    Each action dict has {"name": str, "params": dict}.
    """
    thinking = None
    actions = []

    for output in response.outputs:
        if hasattr(output, "content"):  # MessageOutputEntry
            thinking = output.content
        elif hasattr(output, "tool_name"):  # FunctionCallEntry
            name = output.tool_name
            args = (
                json.loads(output.arguments)
                if isinstance(output.arguments, str)
                else output.arguments
            )
            actions.append({"name": name, "params": args or {}})
        # AgentHandoffEntry, ToolExecutionEntry — log and ignore
        else:
            logger.warning("Ignoring output type for %s: %s", agent_id, type(output).__name__)

    return thinking, actions


class AgentsApiRoverReasoner:
    """Rover reasoner via Mistral Agents API. Returns action dict, does not execute."""

    def __init__(
        self, agent_id="rover-agents-api", model="mistral-small-latest", world: World | None = None
    ):
        self.agent_id = agent_id
        self.model = model
        self._client = None
        self._mistral_agent_id = None
        self._world = world or default_world
        self._conversation_id = None

    def _get_client(self):
        if self._client is None:
            self._client = _create_mistral_client()
        return self._client

    def _get_or_create_agent(self) -> str:
        """Lazy-init Mistral Agent via Agents API. Caches agent ID."""
        if self._mistral_agent_id is not None:
            return self._mistral_agent_id
        client = self._get_client()
        agent = client.beta.agents.create(
            model=self.model,
            name=self.agent_id,
            description="Mars rover agent for the Agent One simulation",
            instructions=self._build_context(),
            tools=ROVER_TOOLS,
        )
        self._mistral_agent_id = agent.id
        return self._mistral_agent_id

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
        """Single-shot Agents API call. Returns {thinking, action} dict."""
        try:
            agent_id = self._get_or_create_agent()
            client = self._get_client()
            context = self._build_context()
            self._world.set_agent_last_context(self.agent_id, context)

            inputs = [
                {
                    "role": "user",
                    "content": "Observe your surroundings and decide your next move.",
                }
            ]

            if self._conversation_id is not None and settings.agents_api_persist_threads:
                response = client.beta.conversations.append(
                    conversation_id=self._conversation_id,
                    inputs=inputs,
                )
            else:
                response = client.beta.conversations.start(
                    agent_id=agent_id,
                    inputs=inputs,
                    handoff_execution="client",
                )
                if settings.agents_api_persist_threads:
                    self._conversation_id = response.conversation_id

            # Parse response using shared helper
            thinking, actions = _parse_conversation_response(response, self.agent_id)
            action = actions[0] if actions else None
            if action is None:
                return self._fallback_turn(f"No function call in response (thinking={thinking!r})")

            return {"thinking": thinking, "action": action}

        except Exception as exc:
            logger.exception("Agents API turn failed for %s, using fallback", self.agent_id)
            return self._fallback_turn(f"Agents API unavailable ({type(exc).__name__})")

    def _fallback_turn(self, reason):
        try:
            agent = self._world.get_agent(self.agent_id)
        except KeyError:
            # Agent not registered in world — return a safe default move
            direction = random.choice(list(DIRECTIONS.keys()))
            return {
                "thinking": f"LLM fallback: {reason}. Agent not in world, moving {direction}.",
                "action": {"name": "move", "params": {"direction": direction}},
            }
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


class AgentsApiDroneReasoner:
    """Drone scout reasoner via Mistral Agents API. Returns action dict, does not execute."""

    def __init__(
        self, agent_id="drone-agents-api", model="mistral-small-latest", world: World | None = None
    ):
        self.agent_id = agent_id
        self.model = model
        self._client = None
        self._mistral_agent_id = None
        self._world = world or default_world
        self._conversation_id = None

    def _get_client(self):
        if self._client is None:
            self._client = _create_mistral_client()
        return self._client

    def _get_or_create_agent(self) -> str:
        """Lazy-init Mistral Agent via Agents API. Caches agent ID."""
        if self._mistral_agent_id is not None:
            return self._mistral_agent_id
        client = self._get_client()
        agent = client.beta.agents.create(
            model=self.model,
            name=self.agent_id,
            description="Mars drone scout agent for the Agent One simulation",
            instructions=self._build_context(),
            tools=DRONE_TOOLS,
        )
        self._mistral_agent_id = agent.id
        return self._mistral_agent_id

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

        # Nearest unscanned area hint
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
            + (
                "\n\u26a0\ufe0f BATTERY CRITICAL — return to station now!"
                if battery_critical
                else ""
            )
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
                    parts.append("\u26a0\ufe0f HOTSPOT — notify station before moving!")

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
        """Single-shot Agents API call. Returns {thinking, action} dict."""
        try:
            agent_id = self._get_or_create_agent()
            client = self._get_client()
            context = self._build_context()
            self._world.set_agent_last_context(self.agent_id, context)

            inputs = [
                {
                    "role": "user",
                    "content": "Observe your surroundings and decide your next action.",
                }
            ]

            if self._conversation_id is not None and settings.agents_api_persist_threads:
                response = client.beta.conversations.append(
                    conversation_id=self._conversation_id,
                    inputs=inputs,
                )
            else:
                response = client.beta.conversations.start(
                    agent_id=agent_id,
                    inputs=inputs,
                    handoff_execution="client",
                )
                if settings.agents_api_persist_threads:
                    self._conversation_id = response.conversation_id

            # Parse response using shared helper
            thinking, actions = _parse_conversation_response(response, self.agent_id)
            action = actions[0] if actions else None

            if action is None:
                return self._fallback_turn(f"No function call in response (thinking={thinking!r})")

            return {"thinking": thinking, "action": action}

        except Exception as exc:
            logger.exception("Agents API turn failed for %s, using fallback", self.agent_id)
            return self._fallback_turn(f"Agents API unavailable ({type(exc).__name__})")

    def _fallback_turn(self, reason=""):
        """Random drone action (move or scan) when API is unavailable."""
        try:
            agent = self._world.get_agent(self.agent_id)
        except KeyError:
            # Agent not registered — default to scan
            return {
                "thinking": f"LLM fallback: {reason}. Agent not in world, scanning.",
                "action": {"name": "scan", "params": {}},
            }
        x, y = agent["position"]
        # Drone can move or scan; prefer scanning unscanned tiles
        scanned_positions = {tuple(s["position"]) for s in self._world.get_drone_scans()}
        if (x, y) not in scanned_positions:
            return {
                "thinking": f"LLM fallback: {reason}. Current position unscanned, scanning.",
                "action": {"name": "scan", "params": {}},
            }
        # Move toward nearest unscanned area
        direction = random.choice(list(DIRECTIONS.keys()))
        return {
            "thinking": f"LLM fallback: {reason}. Moving {direction} to find unscanned area.",
            "action": {"name": "move", "params": {"direction": direction}},
        }


class AgentsApiStationReasoner:
    """Station reasoner via Mistral Agents API. Event-driven with 3-method interface."""

    def __init__(self, agent_id="station-agents-api", model="mistral-small-latest"):
        self.agent_id = agent_id
        self.model = model
        self._client = None
        self._mistral_agent_id = None
        self._conversation_id = None

    def _get_client(self):
        if self._client is None:
            self._client = _create_mistral_client()
        return self._client

    def _get_or_create_agent(self) -> str:
        """Lazy-init Mistral Agent via Agents API. Caches agent ID."""
        if self._mistral_agent_id is not None:
            return self._mistral_agent_id
        client = self._get_client()
        agent = client.beta.agents.create(
            model=self.model,
            name=self.agent_id,
            description="Mars base station coordinator for the Agent One simulation",
            instructions=(
                "You are the Mars base station. You coordinate the Mars mission.\n"
                "Your role is to assign missions to all field agents, respond to field reports, "
                "and recharge agents when they return to the station.\n"
                "\n"
                "AGENT TYPES:\n"
                "- Rovers: ground units that explore, analyze veins, dig basalt, and deliver to station.\n"
                "- Drones: aerial scouts that fly fast and scan for basalt deposits. They cannot dig.\n"
                "- Haulers: heavy transport vehicles that collect cargo from rovers and bring it to station.\n"
                "\n"
                "The mission goal is to collect basalt from veins. Each vein has a grade "
                "(low/medium/high/rich/pristine) that determines basalt quantity.\n"
                "Rovers must deliver enough basalt to the station to meet the target quantity.\n"
                "Keep responses short (1-2 sentences of reasoning, then act).\n"
                "Always assign missions to all available agents when defining the initial mission.\n"
                "When an agent arrives at the station with low battery, charge it.\n"
                "If an agent is critically low, stuck, or in danger, issue a recall command."
            ),
            tools=STATION_TOOLS,
        )
        self._mistral_agent_id = agent.id
        return self._mistral_agent_id

    def _build_context(self, station_ctx: StationContext) -> str:
        """Build text summary of world state for the station."""
        from .station import SYSTEM_PROMPT, _build_world_summary

        parts = [SYSTEM_PROMPT, "\n== Current world state ==\n" + _build_world_summary(station_ctx)]
        if station_ctx.memory:
            parts.append("\n== Field Reports (memory) ==")
            for entry in station_ctx.memory:
                parts.append(f"- {entry}")
        return "\n".join(parts)

    def _call_agents_api(self, user_message: str, station_ctx: StationContext) -> dict:
        """Single Agents API call with station context. Returns {thinking, actions, context_text}."""
        try:
            agent_id = self._get_or_create_agent()
            client = self._get_client()
            ctx_text = self._build_context(station_ctx)

            inputs = [{"role": "user", "content": ctx_text + "\n\n" + user_message}]

            if self._conversation_id is not None and settings.agents_api_persist_threads:
                response = client.beta.conversations.append(
                    conversation_id=self._conversation_id,
                    inputs=inputs,
                )
            else:
                response = client.beta.conversations.start(
                    agent_id=agent_id,
                    inputs=inputs,
                    handoff_execution="client",
                )
                if settings.agents_api_persist_threads:
                    self._conversation_id = response.conversation_id

            # Parse response — station can return MULTIPLE actions
            thinking, actions = _parse_conversation_response(response, self.agent_id)

            return {"thinking": thinking, "actions": actions, "context_text": ctx_text}

        except Exception as exc:
            logger.exception("Agents API station call failed: %s", exc)
            return self._fallback_actions()

    def define_mission(self, station_ctx: StationContext) -> dict:
        """Called at startup to define initial missions for all field agents."""
        rover_count = sum(1 for r in station_ctx.rovers if r.agent_type != "drone")
        drone_count = sum(1 for r in station_ctx.rovers if r.agent_type == "drone")
        agent_hint = f" You have {rover_count} rover(s) and {drone_count} drone(s)."
        if drone_count > 0 and rover_count > 0:
            agent_hint += (
                " Assign rovers and drones to DIFFERENT sectors so they don't overlap."
                " Mention specific directions in each objective (e.g. 'Scout north and east sectors',"
                " 'Explore south and west quadrant')."
            )
        if drone_count > 1:
            agent_hint += f" You have {drone_count} drones — send each to a different sector."
        return self._call_agents_api(
            "The mission is starting. Review the world state and assign initial "
            "missions to ALL agents (rovers and drones)." + agent_hint,
            station_ctx,
        )

    def handle_event(self, station_ctx: StationContext, event_data: dict) -> dict:
        """Called when a relevant field event occurs (e.g. vein found)."""
        prompt = (
            f"Field report from {event_data['source']}: {event_data['name']}\n"
            f"Details: {json.dumps(event_data.get('payload', {}))}\n"
            "Decide how to respond. You may reassign missions or broadcast alerts."
        )
        return self._call_agents_api(prompt, station_ctx)

    def evaluate_situation(self, station_ctx: StationContext, events: list[dict]) -> dict:
        """Periodic evaluation of recent field events."""
        if events:
            event_lines = "\n".join(
                f"- {e.get('source', '?')}: {e.get('name', '?')} — {json.dumps(e.get('payload', {}))}"
                for e in events[-10:]
            )
        else:
            event_lines = "(no recent events)"
        prompt = (
            f"Tick {station_ctx.tick} — periodic situation evaluation.\n"
            f"Recent field events:\n{event_lines}\n"
            "Evaluate the situation. Reassign missions, broadcast alerts, or charge rovers as needed."
        )
        return self._call_agents_api(prompt, station_ctx)

    def _fallback_actions(self) -> dict:
        """Return empty actions when API is unavailable."""
        return {"thinking": "Fallback: no API key", "actions": [], "context_text": ""}


class RoverAgentsApiLoop(RoverLoop):
    """Rover loop wired to AgentsApiRoverReasoner."""

    def __init__(
        self, agent_id: str = "rover-agents-api", interval: float = 3.0, world: World | None = None
    ):
        super().__init__(agent_id=agent_id, interval=interval, world=world)
        self._reasoner = AgentsApiRoverReasoner(agent_id=self.agent_id, world=self._world)
        set_agent_model(self.agent_id, "agents-api")


class DroneAgentsApiLoop(DroneLoop):
    """Drone loop wired to AgentsApiDroneReasoner."""

    def __init__(self, interval: float = 2.0, world: World | None = None):
        super().__init__(agent_id="drone-agents-api", interval=interval, world=world)
        self._reasoner = AgentsApiDroneReasoner(agent_id=self.agent_id, world=self._world)
        set_agent_model(self.agent_id, "agents-api")


class StationAgentsApiLoop(StationLoop):
    """Station loop wired to AgentsApiStationReasoner."""

    def __init__(self, interval: float = 20.0, world: World | None = None):
        super().__init__(interval=interval, world=world)
        # Override the station agent with the Agents API version
        self._station = AgentsApiStationReasoner()
