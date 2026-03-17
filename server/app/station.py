"""Station agent — LLM-powered, event-driven. Assigns missions and reacts to field reports."""

import json
import logging

from huggingface_hub import InferenceClient

from .config import settings
from .llm import get_mistral_client
from .llm_utils import safe_get_choice
from .models import StationContext
from .world import allocate_power, assign_mission, charge_agent

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

RECALL_AGENT_TOOL = {
    "type": "function",
    "function": {
        "name": "recall_agent",
        "description": "Issue an emergency recall command so an agent returns to station immediately.",
        "parameters": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "The agent to recall (e.g. 'rover-mistral', 'drone-mistral', 'hauler-mistral').",
                },
                "reason": {
                    "type": "string",
                    "description": "Short reason for the recall command.",
                },
            },
            "required": ["agent_id"],
        },
    },
}

ALLOCATE_POWER_TOOL = {
    "type": "function",
    "function": {
        "name": "allocate_power",
        "description": "Set a power budget for an agent. Defines the minimum battery threshold to maintain. A PowerBudgetWarning event fires when the agent's battery drops below this level.",
        "parameters": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "The agent to set a power budget for (e.g. 'rover-mistral', 'drone-mistral').",
                },
                "amount": {
                    "type": "number",
                    "description": "Minimum battery threshold (0.0-1.0). Agent receives warnings below this level.",
                },
            },
            "required": ["agent_id", "amount"],
        },
    },
}

STATION_TOOLS = [
    ASSIGN_MISSION_TOOL,
    BROADCAST_ALERT_TOOL,
    CHARGE_AGENT_TOOL,
    RECALL_AGENT_TOOL,
    ALLOCATE_POWER_TOOL,
]

SYSTEM_PROMPT = (
    "You are the Mars base station. You coordinate the Mars mission.\n"
    "Your role is to assign missions to all field agents, respond to field reports, "
    "and recharge agents when they return to the station.\n"
    "\n"
    "AGENT TYPES:\n"
    "- Rovers: ground units that explore, analyze veins, dig basalt, and deliver to station.\n"
    "- Drones: aerial scouts that fly fast and scan for basalt deposits. They cannot dig.\n"
    "- Haulers: heavy transport vehicles that collect cargo from rovers and bring it to station.\n"
    "  Haulers carry up to 6 items (rovers carry only 3). Assign haulers to collect from rovers\n"
    "  that have full inventories so rovers can keep exploring without returning to station.\n"
    "\n"
    "RESOURCES:\n"
    "- Water: produced by recycling ice at station. Used for base upgrades.\n"
    "- Gas: produced by gas plants on geysers. Used for base upgrades.\n"
    "- Base upgrades: charge_speed (faster recharging), storage (higher mission target), radar (wider reveal).\n"
    "\n"
    "The mission goal is to collect basalt from veins. Each vein has a grade "
    "(low/medium/high/rich/pristine) that determines basalt quantity.\n"
    "Rovers must deliver enough basalt to the station to meet the target quantity.\n"
    "Keep responses short (1-2 sentences of reasoning, then act).\n"
    "Always assign missions to all available agents when defining the initial mission.\n"
    "When an agent arrives at the station with low battery, charge it.\n"
    "If an agent is critically low, stuck, or in danger, issue a recall command.\n"
    "\n"
    "DRONE COORDINATION:\n"
    "- When you have multiple drones, send each to a DIFFERENT sector of the map.\n"
    "- Divide the grid into quadrants or sectors and assign one drone per sector.\n"
    "- This maximizes scan coverage and avoids redundant overlapping scans.\n"
    "\n"
    "HAULER COORDINATION:\n"
    "- Assign haulers to patrol near rovers that are furthest from station.\n"
    "- When a rover's inventory is full (3 items), direct the hauler to collect from it.\n"
    "- This keeps rovers exploring instead of returning to station to deliver.\n"
    "\n"
    "POWER MANAGEMENT:\n"
    "- Use allocate_power to set minimum battery thresholds for agents.\n"
    "- Set budgets at mission start: 0.2-0.3 for rovers, 0.3-0.4 for drones.\n"
    "- When you receive a PowerBudgetWarning, recall the affected agent or prioritize charging.\n"
    "- When EmergencyModeActivated fires, recall all low-battery agents immediately.\n"
    "- Adjust budgets based on mission progress and distance from station.\n"
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
    # Resource totals
    if hasattr(context, "water_collected") or hasattr(context, "gas_collected"):
        water = getattr(context, "water_collected", 0)
        gas = getattr(context, "gas_collected", 0)
        if water > 0 or gas > 0:
            lines.append(f"Resources: water={water}, gas={gas}")
    for rover in context.rovers:
        x, y = rover.position
        if rover.agent_type == "drone":
            label = "drone"
        elif rover.agent_type == "hauler":
            label = "hauler"
        else:
            label = "rover"
        lines.append(
            f"  {rover.id} ({label}): pos=({x},{y}) battery={rover.battery:.0%} "
            f'mission="{rover.mission.objective}" visited={rover.visited_count}'
        )
    # Power budgets
    power_budgets = getattr(context, "power_budgets", {})
    if power_budgets:
        budget_parts = [f"{aid}={bud:.0%}" for aid, bud in power_budgets.items()]
        lines.append(f"Power budgets: {', '.join(budget_parts)}")
    if getattr(context, "emergency_mode", False):
        lines.append("*** EMERGENCY MODE ACTIVE — total power demand exceeds station capacity ***")
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
        elif name == "recall_agent":
            actions.append({"name": "recall_agent", "params": args})
        elif name == "allocate_power":
            actions.append({"name": "allocate_power", "params": args})
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
    elif name == "recall_agent":
        return {
            "ok": True,
            "agent_id": params["agent_id"],
            "reason": params.get("reason", "Emergency recall from station"),
        }
    elif name == "allocate_power":
        return allocate_power(params["agent_id"], params["amount"])
    return {"ok": False, "error": f"Unknown station action: {name}"}


class StationAgent:
    """Event-driven station agent. Called on startup and on specific events."""

    def __init__(self, agent_id="station", model="mistral-small-latest"):
        self.agent_id = agent_id
        self.model = model
        self._client = None
        self._hf_client = None

    def _get_client(self):
        if self._client is None:
            self._client = get_mistral_client()
        return self._client

    def _get_hf_client(self):
        if self._hf_client is None:
            if not settings.hugging_face_read:
                raise RuntimeError("HUGGING_FACE_READ not set")
            self._hf_client = InferenceClient(token=settings.hugging_face_read, provider="auto")
        return self._hf_client

    def _build_context(self, context: StationContext):
        parts = [SYSTEM_PROMPT, "\n== Current world state ==\n" + _build_world_summary(context)]
        if context.memory:
            parts.append("\n== Field Reports (memory) ==")
            for entry in context.memory:
                parts.append(f"- {entry}")
        return "\n".join(parts)

    def _call_llm(self, user_message, context: StationContext):
        """Single LLM call with tools. Returns {thinking, actions} dict."""
        ctx_text = self._build_context(context)
        messages = [
            {"role": "system", "content": ctx_text},
            {"role": "user", "content": user_message},
        ]
        logger.info("Station LLM call: %s", user_message[:80])
        effective_model = settings.fine_tuned_agent_model or self.model
        try:
            if settings.llm_provider == "huggingface":
                hf_client = self._get_hf_client()
                model = settings.huggingface_model or "Qwen/Qwen2.5-72B-Instruct"
                response = hf_client.chat_completion(
                    model=model,
                    messages=messages,
                    tools=STATION_TOOLS,
                    tool_choice="auto",
                )
            else:
                client = self._get_client()
                response = client.chat.complete(
                    model=effective_model,
                    messages=messages,
                    tools=STATION_TOOLS,
                )
        except Exception as e:
            logger.exception("Station LLM API failed: %s", e)
            return {
                "thinking": f"LLM error: {type(e).__name__}: {e}",
                "actions": [],
                "context_text": "",
            }

        from .training import collector

        collector.record_agent_interaction(
            agent_id=self.agent_id,
            agent_type="station",
            messages=messages,
            tools=STATION_TOOLS,
            response=response,
        )
        choice = safe_get_choice(response, "station")
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
