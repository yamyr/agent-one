"""Station agent — LLM-powered, event-driven. Assigns missions and reacts to field reports."""

import json
import logging

from mistralai import Mistral

from .config import settings
from .world import WORLD, GRID_W, GRID_H, assign_mission

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
                    "description": "The rover agent to assign (e.g. 'rover-mock', 'rover-mistral').",
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

STATION_TOOLS = [ASSIGN_MISSION_TOOL, BROADCAST_ALERT_TOOL]

SYSTEM_PROMPT = (
    "You are the Mars base station. You coordinate the Mars mission.\n"
    "Your role is to assign missions to rover agents and respond to field reports.\n"
    "You have two rovers available: 'rover-mock' and 'rover-mistral'.\n"
    "Keep responses short (1-2 sentences of reasoning, then act).\n"
    "Always assign missions to at least one rover when defining the initial mission.\n"
)


def _build_world_summary():
    """Build a text summary of current world state for the station's context."""
    lines = [f"Grid: {GRID_W}x{GRID_H}"]
    for aid, agent in WORLD["agents"].items():
        if agent["type"] == "station":
            continue
        x, y = agent["position"]
        lines.append(
            f"  {aid}: pos=({x},{y}) battery={agent['battery']:.0%} "
            f"mission=\"{agent['mission']['objective']}\" visited={len(agent.get('visited', []))}"
        )
    stones = WORLD.get("stones", [])
    lines.append(f"Stones on map: {len(stones)}")
    for s in stones:
        lines.append(f"  {s['type']} at ({s['position'][0]}, {s['position'][1]})")
    return "\n".join(lines)


def _execute_tool_calls(tool_calls):
    """Execute tool calls from LLM response. Returns list of event dicts."""
    events = []
    for tc in tool_calls:
        name = tc.function.name
        args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments

        if name == "assign_mission":
            result = assign_mission(args["agent_id"], args["objective"])
            events.append({
                "source": "station",
                "type": "command",
                "name": "assign_mission",
                "payload": result,
            })
        elif name == "broadcast_alert":
            events.append({
                "source": "station",
                "type": "event",
                "name": "alert",
                "payload": {"message": args["message"]},
            })
    return events


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

    def _build_context(self):
        return SYSTEM_PROMPT + "\n== Current world state ==\n" + _build_world_summary()

    def _call_llm(self, user_message):
        """Single LLM call with tools. Returns (thinking, events)."""
        client = self._get_client()
        messages = [
            {"role": "system", "content": self._build_context()},
            {"role": "user", "content": user_message},
        ]
        logger.info("Station LLM call: %s", user_message[:80])
        response = client.chat.complete(
            model=self.model,
            messages=messages,
            tools=STATION_TOOLS,
        )
        choice = response.choices[0]
        thinking = choice.message.content or None
        events = []

        if thinking:
            logger.info("Station thinking: %s", thinking)
            events.append({
                "source": self.agent_id,
                "type": "event",
                "name": "thinking",
                "payload": {"text": thinking},
            })

        if choice.message.tool_calls:
            events.extend(_execute_tool_calls(choice.message.tool_calls))

        return events

    def define_mission(self):
        """Called at startup to define initial missions for rovers."""
        return self._call_llm(
            "The mission is starting. Review the world state and assign initial "
            "missions to the rovers. Consider the stone locations and grid layout."
        )

    def handle_event(self, event):
        """Called when a relevant field event occurs (e.g. stone found)."""
        prompt = (
            f"Field report from {event['source']}: {event['name']}\n"
            f"Details: {json.dumps(event.get('payload', {}))}\n"
            "Decide how to respond. You may reassign missions or broadcast alerts."
        )
        return self._call_llm(prompt)
