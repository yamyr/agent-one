"""Minimal Rover agent — calls Mistral with a move tool, runs inside the server process."""

import json
import logging
import random

from mistralai import Mistral

from .config import settings
from .world import WORLD, move_agent

logger = logging.getLogger(__name__)

MOVE_TOOL = {
    "type": "function",
    "function": {
        "name": "move",
        "description": "Move the rover to a target zone.",
        "parameters": {
            "type": "object",
            "properties": {
                "zone": {
                    "type": "string",
                    "description": "Target zone ID, e.g. 'Z03'.",
                },
            },
            "required": ["zone"],
        },
    },
}

MAX_TOOL_ROUNDS = 5


class RoverAgent:
    """Rover agent that reasons via Mistral and can move between zones."""

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

    def _system_prompt(self):
        agent = WORLD["agents"][self.agent_id]
        return (
            "You are Rover-1, an autonomous Mars rover.\n"
            "You explore zones, observe your surroundings, and decide where to move.\n"
            "Keep responses short (1-2 sentences of reasoning, then act).\n"
            "\n"
            "Current world state:\n"
            f"- Your position: {agent['position']}\n"
            f"- Battery: {agent['battery']:.0%}\n"
            f"- Available zones: {', '.join(WORLD['zones'].keys())}\n"
        )

    def _execute_tool(self, name, args_json):
        """Execute a tool call. Returns (result_str, event_dict)."""
        args = json.loads(args_json) if isinstance(args_json, str) else args_json

        if name == "move":
            result = move_agent(self.agent_id, args["zone"])
            if result["ok"]:
                event = {
                    "source": self.agent_id,
                    "type": "action",
                    "name": "move",
                    "payload": {"from": result["from"], "to": result["to"]},
                }
                return json.dumps(result), event
            return json.dumps(result), None

        return json.dumps({"ok": False, "error": f"Unknown tool: {name}"}), None

    def run_turn(self, instruction):
        """Run one observe-reason-act loop. Returns list of event dicts."""
        events = []
        client = self._get_client()

        messages = [
            {"role": "system", "content": self._system_prompt()},
            {"role": "user", "content": instruction},
        ]

        for _ in range(MAX_TOOL_ROUNDS):
            logger.info("Calling Mistral (%s) with %d messages", self.model, len(messages))
            response = client.chat.complete(
                model=self.model,
                messages=messages,
                tools=[MOVE_TOOL],
            )
            choice = response.choices[0]

            # Capture any text reasoning
            if choice.message.content:
                text = choice.message.content
                logger.info("Rover thinking: %s", text)
                events.append(
                    {
                        "source": self.agent_id,
                        "type": "event",
                        "name": "thinking",
                        "payload": {"text": text},
                    }
                )

            # No tool calls — turn is done
            if not choice.message.tool_calls:
                break

            # Record assistant message with tool calls in history
            messages.append(choice.message)

            # Execute each tool call
            for tc in choice.message.tool_calls:
                result_str, action_event = self._execute_tool(
                    tc.function.name,
                    tc.function.arguments,
                )
                if action_event:
                    events.append(action_event)
                messages.append(
                    {
                        "role": "tool",
                        "name": tc.function.name,
                        "content": result_str,
                        "tool_call_id": tc.id,
                    }
                )
        else:
            logger.warning("Rover hit max tool rounds (%d)", MAX_TOOL_ROUNDS)

        return events


class MockRoverAgent:
    """Mock rover that picks a random zone each turn — no LLM calls."""

    def __init__(self, agent_id="rover-mock"):
        self.agent_id = agent_id

    def run_turn(self, instruction):
        events = []
        agent = WORLD["agents"][self.agent_id]
        current = agent["position"]
        others = [z for z in WORLD["zones"].keys() if z != current]
        target = random.choice(others)

        events.append(
            {
                "source": self.agent_id,
                "type": "event",
                "name": "thinking",
                "payload": {"text": f"I'm at {current}. I'll move to {target} to explore."},
            }
        )

        result = move_agent(self.agent_id, target)
        if result["ok"]:
            events.append(
                {
                    "source": self.agent_id,
                    "type": "action",
                    "name": "move",
                    "payload": {"from": result["from"], "to": result["to"]},
                }
            )

        return events
