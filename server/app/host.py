"""Host — pure message router between agents, station, and UI.

Owns agent inboxes, lifecycle, and station action routing.
Agents never talk directly — the Host routes all messages.
The Host has NO domain knowledge — agents own their loops via BaseAgent.run().
"""

import asyncio
import logging
import time
import uuid

from .base_agent import BaseAgent
from .broadcast import broadcaster
from .narrator import Narrator
from .protocol import make_message
from .station import StationAgent, execute_action as station_execute_action
from .world import abort_mission as world_abort_mission
from .world import get_snapshot
from .world import observe_station
from .world import set_elapsed_provider
from .config import settings
from .training_logger import training_logger
from .training_models import SessionConfig, SessionResult

logger = logging.getLogger(__name__)

CONFIRM_DEFAULT_TIMEOUT = 30


class Host:
    """Central message router. Manages agent inboxes, loops, and station routing."""

    def __init__(self, narrator: Narrator):
        self._narrator = narrator
        self._inboxes: dict[str, asyncio.Queue] = {}
        self._agents: list[BaseAgent] = []
        self._station = StationAgent()
        self._station_loop = None
        self._agent_tasks: list[asyncio.Task] = []
        self._paused = False
        self._session_start_time: float = 0.0
        self._total_paused_duration: float = 0.0
        self._pause_start_time: float | None = None
        self._pending_confirms: dict[str, dict] = {}

    @property
    def paused(self) -> bool:
        return self._paused

    @paused.setter
    def paused(self, value: bool):
        """Set paused state with automatic pause duration tracking."""
        if value and not self._paused:
            self._pause_start_time = time.monotonic()
        elif not value and self._paused and self._pause_start_time is not None:
            self._total_paused_duration += time.monotonic() - self._pause_start_time
            self._pause_start_time = None
        self._paused = value

    def get_elapsed_seconds(self) -> float:
        """Return wall-clock seconds since start, excluding paused time."""
        if not self._session_start_time:
            return 0.0
        raw = time.monotonic() - self._session_start_time
        paused_so_far = self._total_paused_duration
        if self._paused and self._pause_start_time is not None:
            paused_so_far += time.monotonic() - self._pause_start_time
        return max(0.0, raw - paused_so_far)

    # ── Confirmation management ──

    def create_confirm(self, agent_id: str, question: str, timeout: int) -> str:
        """Create a pending confirmation request. Returns request_id (UUID)."""
        # Enforce one-per-agent: clean up any existing confirm for this agent
        existing = self.get_agent_pending_confirm(agent_id)
        if existing:
            for rid, entry in list(self._pending_confirms.items()):
                if entry["agent_id"] == agent_id:
                    self.cleanup_confirm(rid)
                    break

        request_id = str(uuid.uuid4())
        self._pending_confirms[request_id] = {
            "agent_id": agent_id,
            "question": question,
            "timeout": timeout,
            "event": asyncio.Event(),
            "response": None,
            "tick": 0,
        }
        return request_id

    def resolve_confirm(self, request_id: str, confirmed: bool) -> bool:
        """Set response and signal the waiting agent. Returns True if found."""
        entry = self._pending_confirms.get(request_id)
        if entry is None:
            return False
        entry["response"] = confirmed
        entry["event"].set()
        return True

    def get_pending_confirm(self, request_id: str) -> dict | None:
        """Get a pending confirmation by request_id."""
        return self._pending_confirms.get(request_id)

    def get_agent_pending_confirm(self, agent_id: str) -> dict | None:
        """Get the pending confirmation for a specific agent (if any)."""
        for entry in self._pending_confirms.values():
            if entry["agent_id"] == agent_id:
                return entry
        return None

    def cleanup_confirm(self, request_id: str):
        """Remove a resolved or timed-out confirmation."""
        self._pending_confirms.pop(request_id, None)

    # ── Agent registration ──

    def register(self, agent: BaseAgent):
        """Register an agent and create its inbox."""
        from .agent import StationLoop

        self._agents.append(agent)
        self._inboxes[agent.agent_id] = asyncio.Queue()
        if isinstance(agent, StationLoop):
            self._station_loop = agent

    # ── Inbox management ──

    def send_command(self, target_id: str, command: dict):
        """Enqueue a command dict into an agent's inbox."""
        inbox = self._inboxes.get(target_id)
        if inbox is None:
            logger.warning("send_command: no inbox for %s", target_id)
            return
        inbox.put_nowait(command)

    def drain_inbox(self, agent_id: str) -> list[dict]:
        """Drain all pending commands from an agent's inbox. Non-blocking."""
        inbox = self._inboxes.get(agent_id)
        if inbox is None:
            return []
        commands = []
        while not inbox.empty():
            try:
                commands.append(inbox.get_nowait())
            except asyncio.QueueEmpty:
                break
        return commands

    # ── Broadcast ──

    async def broadcast(self, msg_dict: dict):
        """Send a message to all WebSocket clients and feed the narrator."""
        await broadcaster.send(msg_dict)
        await self._narrator.feed(msg_dict)
        # Log training events
        from .world import world as default_world

        training_logger.maybe_log_broadcast_event(msg_dict, default_world.get_tick())
        # Finalize training session on mission end events
        event_name = msg_dict.get("name", "")
        if event_name in ("mission_success", "mission_failed"):
            payload = msg_dict.get("payload", {})
            status = "success" if event_name == "mission_success" else "failed"
            result = SessionResult(
                total_ticks=default_world.get_tick(),
                basalt_collected=payload.get("collected_quantity", 0),
                basalt_delivered=payload.get("collected_quantity", 0),
                duration_seconds=self.get_elapsed_seconds(),
            )
            training_logger.end_session(result, status=status)
        # Feed interesting events to station loop for periodic evaluation
        if self._station_loop is not None:
            from .agent import StationLoop

            event_name = msg_dict.get("name", "")
            if event_name in StationLoop.INTERESTING_EVENTS:
                self._station_loop.buffer_event(msg_dict)

    # ── Lifecycle ──

    async def start(self):
        """Launch all registered agent loops."""
        self._paused = False
        self._session_start_time = time.monotonic()
        self._total_paused_duration = 0.0
        self._pause_start_time = None
        self._narrator.reset()
        self._narrator.start()

        # Start training session
        config = SessionConfig(
            active_agents=[a.agent_id for a in self._agents],
            llm_turn_interval=settings.llm_turn_interval_seconds,
        )
        training_logger.start_session(config)

        for agent in self._agents:
            task = asyncio.create_task(agent.run(self))
            self._agent_tasks.append(task)
            logger.info("Started agent loop: %s (interval=%.1fs)", agent.agent_id, agent.interval)

        # Station assigns initial missions to all agents
        asyncio.create_task(self.station_startup())
        # Register elapsed time provider for world snapshots
        set_elapsed_provider(self.get_elapsed_seconds)

    def stop(self):
        """Cancel all running agent loops and narrator."""
        self._narrator.stop()
        # End training session
        elapsed = self.get_elapsed_seconds()
        set_elapsed_provider(None)
        result = SessionResult(
            duration_seconds=elapsed,
        )
        training_logger.end_session(result, status="aborted")
        for task in self._agent_tasks:
            task.cancel()
        self._agent_tasks.clear()
        self._agents.clear()
        self._inboxes.clear()

    # ── Station startup ──

    async def station_startup(self):
        """Run station mission definition in background."""
        try:
            station_ctx = observe_station()
            result = await asyncio.wait_for(
                asyncio.to_thread(self._station.define_mission, station_ctx),
                timeout=settings.llm_call_timeout,
            )

            if result["thinking"]:
                msg = make_message(
                    source="station",
                    type="event",
                    name="thinking",
                    payload={"text": result["thinking"]},
                )
                await self.broadcast(msg.to_dict())

            await self.route_station_actions(result)

            await broadcaster.send(
                make_message("world", "event", "state", get_snapshot()).to_dict()
            )
        except Exception:
            logger.exception("Station startup failed")

    # ── Station action routing ──

    async def route_station_actions(self, result, correlation_id=None):
        """Execute station actions and route commands to rover inboxes."""
        for action in result["actions"]:
            action_result = station_execute_action(action)

            # Route assign_mission to target rover inbox
            if action["name"] == "assign_mission" and action_result.get("ok"):
                target_id = action["params"]["agent_id"]
                self.send_command(
                    target_id,
                    {
                        "name": "assign_mission",
                        "payload": {
                            "objective": action["params"]["objective"],
                        },
                        "id": correlation_id or "",
                    },
                )

            # Route recall command to target agent inbox
            if action["name"] == "recall_agent" and action_result.get("ok"):
                target_id = action["params"]["agent_id"]
                self.send_command(
                    target_id,
                    {
                        "name": "recall",
                        "payload": {
                            "reason": action["params"].get(
                                "reason", "Emergency recall from station"
                            ),
                        },
                        "id": correlation_id or "",
                    },
                )

            # Broadcast to UI
            if action["name"] == "broadcast_alert":
                msg = make_message(
                    source="station",
                    type="event",
                    name="alert",
                    payload={"message": action["params"]["message"]},
                    correlation_id=correlation_id,
                )
            else:
                event_type = "command" if action["name"] == "assign_mission" else "action"
                msg = make_message(
                    source="station",
                    type=event_type,
                    name=action["name"],
                    payload=action_result,
                    correlation_id=correlation_id,
                )
            msg_dict = msg.to_dict()
            await broadcaster.send(msg_dict)
            await self._narrator.feed(msg_dict)

    # ── External commands ──

    async def recall_rover(self, rover_id: str):
        """Send a recall command to a rover's inbox."""
        if rover_id not in self._inboxes:
            return {"ok": False, "error": f"Unknown rover: {rover_id}"}
        self.send_command(
            rover_id,
            {
                "name": "recall",
                "payload": {"reason": "Emergency recall from mission control"},
            },
        )
        msg = make_message(
            source="host",
            type="command",
            name="recall",
            payload={"rover_id": rover_id, "reason": "Emergency recall"},
        )
        await broadcaster.send(msg.to_dict())
        return {"ok": True, "rover_id": rover_id}

    async def abort_mission(self, reason="Manual abort from mission control"):
        """Abort the running mission and broadcast the event."""
        result = world_abort_mission(reason)
        if result is None:
            return {"ok": False, "error": "Mission already ended"}
        msg = make_message(
            source="host",
            type="event",
            name="mission_aborted",
            payload=result,
        )
        # Finalize training session as aborted
        from .world import world as default_world

        abort_result = SessionResult(
            total_ticks=default_world.get_tick(),
            basalt_collected=result.get("collected_quantity", 0),
            basalt_delivered=result.get("collected_quantity", 0),
            duration_seconds=self.get_elapsed_seconds(),
        )
        training_logger.end_session(abort_result, status="aborted")
        await broadcaster.send(msg.to_dict())
        await self._narrator.feed(msg.to_dict())
        return {"ok": True, **result}
