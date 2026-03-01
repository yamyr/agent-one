"""Station agent — LLM-powered, event-driven. Assigns missions and reacts to field reports."""

import json
import logging

from mistralai import Mistral

from .config import settings
from .models import StationContext
from .world import assign_mission, charge_agent

logger = logging.getLogger(__name__)

ASSIGN_MISSION_TOOL = {
    "type": "function",
    "function": {
        "name": "assign_mission",
        "description": "Assign a mission objective to a rover agent.",
        "parameters": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "The rover agent to assign (e.g. 'rover-mistral').",
                },
                "objective": {
                    "type": "string",
                    "description": "The mission objective for the rover.",
                },
            },
            "required": ["agent_id", "objective"],
        },
    },
}

BROADCAST_ALERT_TOOL = {
    "type": "function",
    "function": {
        "name": "broadcast_alert",
        "description": "Broadcast an alert message to all agents.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The alert message to broadcast.",
                },
            },
            "required": ["message"],
        },
    },
}

CHARGE_AGENT_TOOL = {
    "type": "function",
    "function": {
        "name": "charge_agent",
        "description": "Recharge an agent's battery. The agent must be co-located with the station. Adds 20% charge per call (70 fuel units).",
        "parameters": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "The agent to charge (e.g. 'rover-mistral', 'drone-mistral').",
                },
            },
            "required": ["agent_id"],
        },
    },
}

STATION_TOOLS = [ASSIGN_MISSION_TOOL, BROADCAST_ALERT_TOOL, CHARGE_AGENT_TOOL]

SYSTEM_PROMPT = (
    "You are the Mars base station. You coordinate the Mars mission.\n"
    "Your role is to assign missions to all field agents, respond to field reports, "
    "and recharge agents when they return to the station.\n"
    "\n"
    "AGENT TYPES:\n"
    "- Rovers: ground units that explore, analyze veins, dig basalt, and deliver to station.\n"
    "- Drones: aerial scouts that fly fast and scan for basalt deposits. They cannot dig.\n"
    "\n"
    "The mission goal is to collect basalt from veins. Each vein has a grade "
    "(low/medium/high/rich/pristine) that determines basalt quantity.\n"
    "Rovers must deliver enough basalt to the station to meet the target quantity.\n"
    "Keep responses short (1-2 sentences of reasoning, then act).\n"
    "Always assign missions to all available agents when defining the initial mission.\n"
    "When an agent arrives at the station with low battery, charge it.\n"
    "\n"
    "DRONE COORDINATION:\n"
    "- When you have multiple drones, send each to a DIFFERENT sector of the map.\n"
    "- Divide the grid into quadrants or sectors and assign one drone per sector.\n"
    "- This maximizes scan coverage and avoids redundant overlapping scans.\n"
)


def _build_world_summary(context: StationContext):
    """Build a text summary of current world state for the station's context."""
    lines = [f"Grid: {context.grid_w}x{context.grid_h}"]
    if context.tick:
        lines.append(f"Tick: {context.tick}")
    if context.mission_status:
        lines.append(
            f"Mission status: {context.mission_status} ({context.collected_quantity}/{context.target_quantity})"
        )
    for rover in context.rovers:
        x, y = rover.position
        label = "drone" if rover.agent_type == "drone" else "rover"
        lines.append(
            f"  {rover.id} ({label}): pos=({x},{y}) battery={rover.battery:.0%} "
            f'mission="{rover.mission.objective}" visited={rover.visited_count}'
        )
    lines.append(f"Veins on map: {len(context.stones)}")
    for s in context.stones:
        grade_str = f" grade={s.grade}" if s.grade != "unknown" else ""
        qty_str = f" qty={s.quantity}" if s.quantity > 0 else ""
        lines.append(f"  {s.type}{grade_str}{qty_str} at ({s.position[0]}, {s.position[1]})")
    return "\n".join(lines)


def _parse_tool_calls(tool_calls):
    """Parse tool calls from LLM response into action dicts. Does NOT execute them."""
    actions = []
    for tc in tool_calls:
        name = tc.function.name
        args = (
            json.loads(tc.function.arguments)
            if isinstance(tc.function.arguments, str)
            else tc.function.arguments
        )

        if name == "assign_mission":
            actions.append({"name": "assign_mission", "params": args})
        elif name == "broadcast_alert":
            actions.append({"name": "broadcast_alert", "params": args})
        elif name == "charge_agent":
            actions.append({"name": "charge_agent", "params": args})
    return actions


def execute_action(action):
    """Execute a station action on WORLD. Returns result dict."""
    name = action["name"]
    params = action["params"]
    if name == "assign_mission":
        return assign_mission(params["agent_id"], params["objective"])
    elif name == "charge_agent":
        return charge_agent(params["agent_id"])
    elif name == "broadcast_alert":
        return {"ok": True, "message": params["message"]}
    return {"ok": False, "error": f"Unknown station action: {name}"}


class StationAgent:
    """Event-driven station agent. Called on startup and on specific events."""

    def __init__(self, agent_id="station", model="mistral-small-latest"):
        self.agent_id = agent_id
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not settings.mistral_api_key:
                raise RuntimeError("MISTRAL_API_KEY not set")
            self._client = Mistral(api_key=settings.mistral_api_key)
        return self._client

    def _build_context(self, context: StationContext):
        parts = [SYSTEM_PROMPT, "\n== Current world state ==\n" + _build_world_summary(context)]
        if context.memory:
            parts.append("\n== Field Reports (memory) ==")
            for entry in context.memory:
                parts.append(f"- {entry}")
        return "\n".join(parts)

    def _call_llm(self, user_message, context: StationContext):
        """Single LLM call with tools. Returns {thinking, actions} dict."""
        client = self._get_client()
        ctx_text = self._build_context(context)
        messages = [
            {"role": "system", "content": ctx_text},
            {"role": "user", "content": user_message},
        ]
        logger.info("Station LLM call: %s", user_message[:80])
        effective_model = settings.fine_tuned_agent_model or self.model
        response = client.chat.complete(
            model=effective_model,
            messages=messages,
            tools=STATION_TOOLS,
        )
        from .training import collector

        collector.record_agent_interaction(
            agent_id=self.agent_id,
            agent_type="station",
            messages=messages,
            tools=STATION_TOOLS,
            response=response,
        )
        choice = response.choices[0]
        thinking = choice.message.content or None
        actions = []

        if thinking:
            logger.info("Station thinking: %s", thinking)

        if choice.message.tool_calls:
            actions = _parse_tool_calls(choice.message.tool_calls)

        return {"thinking": thinking, "actions": actions, "context_text": ctx_text}

    def define_mission(self, context: StationContext):
        """Called at startup to define initial missions for all field agents."""
        rover_count = sum(1 for r in context.rovers if r.agent_type != "drone")
        drone_count = sum(1 for r in context.rovers if r.agent_type == "drone")
        agent_hint = f" You have {rover_count} rover(s) and {drone_count} drone(s)."
        if drone_count > 0 and rover_count > 0:
            agent_hint += (
                " Assign rovers and drones to DIFFERENT sectors so they don't overlap."
                " Mention specific directions in each objective (e.g. 'Scout north and east sectors',"
                " 'Explore south and west quadrant')."
            )
        if drone_count > 1:
            agent_hint += f" You have {drone_count} drones — send each to a different sector."
        return self._call_llm(
            "The mission is starting. Review the world state and assign initial "
            "missions to ALL agents (rovers and drones)." + agent_hint,
            context,
        )

    def handle_event(self, event, context: StationContext):
        """Called when a relevant field event occurs (e.g. vein found)."""
        prompt = (
            f"Field report from {event['source']}: {event['name']}\n"
            f"Details: {json.dumps(event.get('payload', {}))}\n"
            "Decide how to respond. You may reassign missions or broadcast alerts."
        )
        return self._call_llm(prompt, context)

    def evaluate_situation(self, context: StationContext, events: list[dict]):
        """Periodic evaluation of recent field events. Called by StationLoop."""
        if events:
            event_lines = "\n".join(
                f"- {e.get('source', '?')}: {e.get('name', '?')} — {json.dumps(e.get('payload', {}))}"
                for e in events[-10:]
            )
        else:
            event_lines = "(no recent events)"
        prompt = (
            f"Tick {context.tick} — periodic situation evaluation.\n"
            f"Recent field events:\n{event_lines}\n"
            "Evaluate the situation. Reassign missions, broadcast alerts, or charge rovers as needed."
        )
        return self._call_llm(prompt, context)
