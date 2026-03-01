"""Host — pure message router between agents, station, and UI.

Owns agent inboxes, lifecycle, and station action routing.
Agents never talk directly — the Host routes all messages.
The Host has NO domain knowledge — agents own their loops via BaseAgent.run().
"""

import asyncio
import logging

from .base_agent import BaseAgent
from .broadcast import broadcaster
from .narrator import Narrator
from .protocol import make_message
from .station import StationAgent, execute_action as station_execute_action
from .world import abort_mission as world_abort_mission
from .world import get_snapshot
from .world import observe_station

logger = logging.getLogger(__name__)


class Host:
    """Central message router. Manages agent inboxes, loops, and station routing."""

    def __init__(self, narrator: Narrator):
        self._narrator = narrator
        self._inboxes: dict[str, asyncio.Queue] = {}
        self._agents: list[BaseAgent] = []
        self._station = StationAgent()
        self._station_loop = None
        self._agent_tasks: list[asyncio.Task] = []
        self.paused = False

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
        # Feed interesting events to station loop for periodic evaluation
        if self._station_loop is not None:
            from .agent import StationLoop
            event_name = msg_dict.get("name", "")
            if event_name in StationLoop.INTERESTING_EVENTS:
                self._station_loop.buffer_event(msg_dict)

    # ── Lifecycle ──

    async def start(self):
        """Launch all registered agent loops."""
        self.paused = False
        self._narrator.reset()
        self._narrator.start()

        for agent in self._agents:
            task = asyncio.create_task(agent.run(self))
            self._agent_tasks.append(task)
            logger.info("Started agent loop: %s (interval=%.1fs)", agent.agent_id, agent.interval)

        # Station assigns initial missions to all agents
        asyncio.create_task(self.station_startup())

    def stop(self):
        """Cancel all running agent loops and narrator."""
        self._narrator.stop()
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
            result = await asyncio.to_thread(self._station.define_mission, station_ctx)

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
        await broadcaster.send(msg.to_dict())
        await self._narrator.feed(msg.to_dict())
        return {"ok": True, **result}
