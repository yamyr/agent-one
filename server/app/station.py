"""Station agent — LLM-powered, event-driven. Assigns missions and reacts to field reports."""

import json
import logging

from mistralai import Mistral

from .config import settings
from .models import StationContext
from .world import assign_mission, charge_rover

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

CHARGE_ROVER_TOOL = {
    "type": "function",
    "function": {
        "name": "charge_rover",
        "description": "Recharge a rover's battery. The rover must be co-located with the station. Adds 20% charge per call (70 fuel units).",
        "parameters": {
            "type": "object",
            "properties": {
                "rover_id": {
                    "type": "string",
                    "description": "The rover agent to charge (e.g. 'rover-mistral').",
                },
            },
            "required": ["rover_id"],
        },
    },
}

STATION_TOOLS = [ASSIGN_MISSION_TOOL, BROADCAST_ALERT_TOOL, CHARGE_ROVER_TOOL]

SYSTEM_PROMPT = (
    "You are the Mars base station. You coordinate the Mars mission.\n"
    "Your role is to assign missions to rover agents, respond to field reports, "
    "and recharge rovers when they return to the station.\n"
    "You have one rover available: 'rover-mistral' and one drone: 'drone-mistral'.\n"
    "The mission goal is to collect basalt from veins. Each vein has a grade "
    "(low/medium/high/rich/pristine) that determines basalt quantity.\n"
    "Rovers must deliver enough basalt to the station to meet the target quantity.\n"
    "Keep responses short (1-2 sentences of reasoning, then act).\n"
    "Always assign missions to at least one rover when defining the initial mission.\n"
    "When a rover arrives at the station with low battery, charge it.\n"
)


def _build_world_summary(context: StationContext):
    """Build a text summary of current world state for the station's context."""
    lines = [f"Grid: {context.grid_w}x{context.grid_h}"]
    for rover in context.rovers:
        x, y = rover.position
        lines.append(
            f"  {rover.id}: pos=({x},{y}) battery={rover.battery:.0%} "
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
        elif name == "charge_rover":
            actions.append({"name": "charge_rover", "params": args})
    return actions


def execute_action(action):
    """Execute a station action on WORLD. Returns result dict."""
    name = action["name"]
    params = action["params"]
    if name == "assign_mission":
        return assign_mission(params["agent_id"], params["objective"])
    elif name == "charge_rover":
        return charge_rover(params["rover_id"])
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
        return SYSTEM_PROMPT + "\n== Current world state ==\n" + _build_world_summary(context)

    def _call_llm(self, user_message, context: StationContext):
        """Single LLM call with tools. Returns {thinking, actions} dict.

        Wraps the Mistral API call in try/except so the station agent
        degrades gracefully on API failures instead of crashing.
        """
        client = self._get_client()
        ctx_text = self._build_context(context)
        messages = [
            {"role": "system", "content": ctx_text},
            {"role": "user", "content": user_message},
        ]
        logger.info("Station LLM call: %s", user_message[:80])
        try:
            response = client.chat.complete(
                model=self.model,
                messages=messages,
                tools=STATION_TOOLS,
            )
            choice = response.choices[0]
            thinking = choice.message.content or None
            actions = []

            if thinking:
                logger.info("Station thinking: %s", thinking)

            if choice.message.tool_calls:
                actions = _parse_tool_calls(choice.message.tool_calls)

            return {"thinking": thinking, "actions": actions, "context_text": ctx_text}
        except Exception:
            logger.exception("Station LLM call failed: %s", user_message[:80])
            return {"thinking": None, "actions": [], "context_text": ""}

    def define_mission(self, context: StationContext):
        """Called at startup to define initial missions for rovers."""
        return self._call_llm(
            "The mission is starting. Review the world state and assign initial "
            "missions to the rovers. Consider the vein locations and grid layout.",
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
