"""Scripted event timeline — fire pre-defined world events at specific ticks.

Enables deterministic demo scenarios, tutorial walkthroughs, and repeatable
integration testing without relying on random storm/geyser timing.

Usage:
    from app.events import ScriptedTimeline

    timeline = ScriptedTimeline()
    timeline.load([
        {"tick": 5, "type": "storm_start", "payload": {"duration": 10}},
        {"tick": 20, "type": "battery_drain", "payload": {"agent_id": "rover-mistral", "amount": 0.3}},
    ])

    # Each simulation tick:
    pending = timeline.check_tick(current_tick, world_dict)
    # Returns list of broadcast-ready event dicts
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from . import storm as storm_mod

logger = logging.getLogger(__name__)


# ── Pydantic models ────────────────────────────────────────────────────────


class ScriptedEvent(BaseModel):
    """A single scripted event entry in the timeline."""

    tick: int = Field(..., ge=0, description="Simulation tick to fire this event at")
    type: str = Field(..., description="Event type identifier")
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Event-specific parameters",
    )
    description: str = Field(
        default="",
        description="Human-readable description for UI display",
    )
    fired: bool = Field(default=False, exclude=True)

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {
            "storm_start",
            "storm_end",
            "resource_spawn",
            "battery_drain",
            "battery_set",
            "agent_message",
            "broadcast",
            "spawn_obstacle",
            "mission_update",
        }
        if v not in allowed:
            raise ValueError(f"Unknown event type: {v!r}. Allowed: {sorted(allowed)}")
        return v


# ── Event executors ────────────────────────────────────────────────────────


def _execute_storm_start(world: dict, payload: dict) -> dict:
    """Force-start a storm warning at the current tick."""
    storm = world.setdefault("storm", storm_mod.make_storm_state())
    duration = int(payload.get("duration", 15))
    intensity = float(payload.get("intensity", 0.5))
    tick = world.get("tick", 0)

    storm["phase"] = "warning"
    storm["warning_start"] = tick
    storm["active_start"] = tick + storm_mod.STORM_WARNING_TICKS
    storm["active_end"] = tick + storm_mod.STORM_WARNING_TICKS + duration
    storm["intensity"] = min(1.0, max(0.0, intensity))

    logger.info(
        "Scripted storm_start at tick %d, duration=%d, intensity=%.2f",
        tick,
        duration,
        intensity,
    )
    return {
        "name": "scripted_storm_warning",
        "payload": {
            "message": f"[SCRIPTED] Dust storm approaching! ETA {storm_mod.STORM_WARNING_TICKS} ticks.",
            "active_start": storm["active_start"],
            "active_end": storm["active_end"],
            "scripted": True,
        },
    }


def _execute_storm_end(world: dict, payload: dict) -> dict:
    """Force-clear any active storm."""
    storm = world.get("storm")
    if storm is None:
        return {
            "name": "scripted_storm_end",
            "payload": {"message": "[SCRIPTED] No storm to clear.", "scripted": True},
        }

    old_phase = storm["phase"]
    storm["phase"] = "clear"
    storm["intensity"] = 0.0
    storm_mod.schedule_next_storm(world)

    logger.info("Scripted storm_end at tick %d (was %s)", world.get("tick", 0), old_phase)
    return {
        "name": "scripted_storm_ended",
        "payload": {
            "message": "[SCRIPTED] Dust storm cleared by timeline.",
            "previous_phase": old_phase,
            "scripted": True,
        },
    }


def _execute_resource_spawn(world: dict, payload: dict) -> dict:
    """Spawn a resource (vein, ice, gas) at a specific position."""
    resource_type = payload.get("resource_type", "basalt_vein")
    position = payload.get("position", [5, 5])
    grade = payload.get("grade", "medium")
    quantity = int(payload.get("quantity", 100))

    x, y = int(position[0]), int(position[1])

    if resource_type == "ice":
        deposit = {
            "position": [x, y],
            "type": "ice_deposit",
            "quantity": quantity,
            "gathered": False,
        }
        world.setdefault("ice_deposits", []).append(deposit)
        logger.info("Scripted ice spawn at (%d,%d) qty=%d", x, y, quantity)
    else:
        stone = {
            "position": [x, y],
            "type": "basalt_vein",
            "_true_type": "basalt_vein",
            "grade": grade,
            "_true_grade": grade,
            "quantity": quantity,
            "_true_quantity": quantity,
            "analyzed": True,
        }
        world.setdefault("stones", []).append(stone)
        logger.info("Scripted vein spawn at (%d,%d) grade=%s qty=%d", x, y, grade, quantity)

    return {
        "name": "scripted_resource_spawn",
        "payload": {
            "resource_type": resource_type,
            "position": [x, y],
            "grade": grade,
            "quantity": quantity,
            "scripted": True,
        },
    }


def _execute_battery_drain(world: dict, payload: dict) -> dict:
    """Drain a specific agent's battery by an amount."""
    agent_id = payload.get("agent_id", "rover-mistral")
    amount = float(payload.get("amount", 0.2))

    agents = world.get("agents", {})
    agent = agents.get(agent_id)
    if agent is None:
        return {
            "name": "scripted_battery_drain",
            "payload": {
                "error": f"Unknown agent: {agent_id}",
                "scripted": True,
            },
        }

    old_battery = agent["battery"]
    agent["battery"] = max(0.0, old_battery - amount)

    logger.info(
        "Scripted battery_drain on %s: %.0f%% -> %.0f%%",
        agent_id,
        old_battery * 100,
        agent["battery"] * 100,
    )
    return {
        "name": "scripted_battery_drain",
        "payload": {
            "agent_id": agent_id,
            "amount": amount,
            "battery_before": old_battery,
            "battery_after": agent["battery"],
            "scripted": True,
        },
    }


def _execute_battery_set(world: dict, payload: dict) -> dict:
    """Set a specific agent's battery to an exact level."""
    agent_id = payload.get("agent_id", "rover-mistral")
    level = float(payload.get("level", 1.0))
    level = max(0.0, min(1.0, level))

    agents = world.get("agents", {})
    agent = agents.get(agent_id)
    if agent is None:
        return {
            "name": "scripted_battery_set",
            "payload": {
                "error": f"Unknown agent: {agent_id}",
                "scripted": True,
            },
        }

    old_battery = agent["battery"]
    agent["battery"] = level

    logger.info(
        "Scripted battery_set on %s: %.0f%% -> %.0f%%",
        agent_id,
        old_battery * 100,
        level * 100,
    )
    return {
        "name": "scripted_battery_set",
        "payload": {
            "agent_id": agent_id,
            "level": level,
            "battery_before": old_battery,
            "battery_after": level,
            "scripted": True,
        },
    }


def _execute_agent_message(world: dict, payload: dict) -> dict:
    """Inject a message into the agent messaging system."""
    from_id = payload.get("from", "world")
    to_id = payload.get("to", "rover-mistral")
    message = payload.get("message", "")

    # Import here to avoid circular dependency
    from .world import send_agent_message

    send_agent_message(from_id, to_id, message)

    logger.info("Scripted agent_message from %s to %s: %s", from_id, to_id, message[:50])
    return {
        "name": "scripted_agent_message",
        "payload": {
            "from": from_id,
            "to": to_id,
            "message": message,
            "scripted": True,
        },
    }


def _execute_broadcast(world: dict, payload: dict) -> dict:
    """Emit an arbitrary named event for broadcast to WebSocket clients."""
    event_name = payload.get("name", "scripted_event")
    event_payload = payload.get("event_payload", {})
    event_payload["scripted"] = True

    logger.info("Scripted broadcast: %s", event_name)
    return {
        "name": event_name,
        "payload": event_payload,
    }


def _execute_spawn_obstacle(world: dict, payload: dict) -> dict:
    """Place a mountain or geyser at a specific position."""
    kind = payload.get("kind", "mountain")
    position = payload.get("position", [10, 10])
    x, y = int(position[0]), int(position[1])

    obstacle = {
        "position": [x, y],
        "kind": kind,
        "state": "idle",
    }
    if kind == "geyser":
        obstacle["_cycle_tick"] = 0

    world.setdefault("obstacles", []).append(obstacle)

    logger.info("Scripted %s spawn at (%d,%d)", kind, x, y)
    return {
        "name": "scripted_spawn_obstacle",
        "payload": {
            "kind": kind,
            "position": [x, y],
            "scripted": True,
        },
    }


def _execute_mission_update(world: dict, payload: dict) -> dict:
    """Modify mission parameters (target quantity, collected, status)."""
    mission = world.get("mission", {})
    updates = {}

    if "target_quantity" in payload:
        old_target = mission.get("target_quantity", 300)
        mission["target_quantity"] = int(payload["target_quantity"])
        updates["target_quantity"] = {
            "old": old_target,
            "new": mission["target_quantity"],
        }

    if "collected_quantity" in payload:
        old_collected = mission.get("collected_quantity", 0)
        mission["collected_quantity"] = int(payload["collected_quantity"])
        updates["collected_quantity"] = {
            "old": old_collected,
            "new": mission["collected_quantity"],
        }

    if "status" in payload:
        old_status = mission.get("status", "running")
        mission["status"] = payload["status"]
        updates["status"] = {"old": old_status, "new": mission["status"]}

    logger.info("Scripted mission_update: %s", updates)
    return {
        "name": "scripted_mission_update",
        "payload": {
            "updates": updates,
            "scripted": True,
        },
    }


# ── Executor dispatch table ────────────────────────────────────────────────

_EXECUTORS: dict[str, Any] = {
    "storm_start": _execute_storm_start,
    "storm_end": _execute_storm_end,
    "resource_spawn": _execute_resource_spawn,
    "battery_drain": _execute_battery_drain,
    "battery_set": _execute_battery_set,
    "agent_message": _execute_agent_message,
    "broadcast": _execute_broadcast,
    "spawn_obstacle": _execute_spawn_obstacle,
    "mission_update": _execute_mission_update,
}


# ── ScriptedTimeline ───────────────────────────────────────────────────────


class ScriptedTimeline:
    """Ordered list of scripted events, checked each simulation tick.

    Events are sorted by tick on load. `check_tick()` returns all events
    whose tick matches the current simulation tick (fires exactly once each).
    """

    def __init__(self) -> None:
        self._events: list[ScriptedEvent] = []
        self._cursor: int = 0  # index of next unfired event (events are sorted by tick)

    @property
    def events(self) -> list[ScriptedEvent]:
        """All loaded events (including already-fired ones)."""
        return list(self._events)

    @property
    def pending_count(self) -> int:
        """Number of events not yet fired."""
        return sum(1 for e in self._events if not e.fired)

    @property
    def fired_count(self) -> int:
        """Number of events already fired."""
        return sum(1 for e in self._events if e.fired)

    def load(self, events: list[dict]) -> int:
        """Load events from a list of dicts. Returns count loaded.

        Validates each entry via ScriptedEvent model. Invalid entries are
        logged and skipped. Events are sorted by tick after loading.
        """
        loaded = []
        for i, raw in enumerate(events):
            try:
                loaded.append(ScriptedEvent(**raw))
            except Exception as exc:
                logger.warning("Skipping invalid event at index %d: %s", i, exc)
        self._events = sorted(loaded, key=lambda e: e.tick)
        self._cursor = 0
        logger.info(
            "Loaded %d scripted events (%d skipped)", len(loaded), len(events) - len(loaded)
        )
        return len(loaded)

    def load_from_file(self, path: str | Path) -> int:
        """Load events from a JSON file. Returns count loaded.

        The file should contain a JSON array of event objects, or an object
        with an "events" key containing the array.
        """
        filepath = Path(path)
        if not filepath.exists():
            logger.warning("Event script file not found: %s", filepath)
            return 0

        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to read event script %s: %s", filepath, exc)
            return 0

        if isinstance(data, list):
            return self.load(data)
        if isinstance(data, dict) and "events" in data:
            return self.load(data["events"])

        logger.error("Event script must be a JSON array or object with 'events' key")
        return 0

    def clear(self) -> None:
        """Remove all events and reset cursor."""
        self._events.clear()
        self._cursor = 0

    def reset(self) -> None:
        """Mark all events as unfired and reset cursor (for simulation restart)."""
        for event in self._events:
            event.fired = False
        self._cursor = 0

    def check_tick(self, tick: int, world: dict) -> list[dict]:
        """Execute all events scheduled for the given tick.

        Returns a list of broadcast-ready event dicts (each has 'name' and 'payload').
        Uses cursor-based iteration for O(1) amortized per tick.
        """
        results: list[dict] = []

        # Advance cursor past events with tick < current tick
        while self._cursor < len(self._events) and self._events[self._cursor].tick < tick:
            event = self._events[self._cursor]
            if not event.fired:
                # Fire missed events (simulation jumped ahead)
                result = self._fire_event(event, world)
                if result:
                    results.append(result)
            self._cursor += 1

        # Fire events at current tick
        while self._cursor < len(self._events) and self._events[self._cursor].tick == tick:
            event = self._events[self._cursor]
            if not event.fired:
                result = self._fire_event(event, world)
                if result:
                    results.append(result)
            self._cursor += 1

        return results

    def _fire_event(self, event: ScriptedEvent, world: dict) -> dict | None:
        """Execute a single scripted event. Returns broadcast dict or None."""
        executor = _EXECUTORS.get(event.type)
        if executor is None:
            logger.warning("No executor for event type: %s", event.type)
            event.fired = True
            return None

        try:
            result = executor(world, event.payload)
            event.fired = True
            # Tag with description if present
            if event.description and result and "payload" in result:
                result["payload"]["description"] = event.description
            return result
        except Exception:
            logger.exception("Error executing scripted event %s at tick %d", event.type, event.tick)
            event.fired = True
            return None

    def get_status(self) -> dict:
        """Return timeline status for API responses."""
        return {
            "total_events": len(self._events),
            "fired": self.fired_count,
            "pending": self.pending_count,
            "events": [
                {
                    "tick": e.tick,
                    "type": e.type,
                    "description": e.description,
                    "fired": e.fired,
                    "payload": e.payload,
                }
                for e in self._events
            ],
        }


# ── Module-level singleton ─────────────────────────────────────────────────

timeline = ScriptedTimeline()


# ── Demo timeline script ───────────────────────────────────────────────────

DEMO_TIMELINE: list[dict] = [
    {
        "tick": 3,
        "type": "broadcast",
        "payload": {
            "name": "timeline_announcement",
            "event_payload": {
                "message": "Mission control: All systems nominal. Beginning surface operations.",
            },
        },
        "description": "Mission start announcement",
    },
    {
        "tick": 8,
        "type": "resource_spawn",
        "payload": {
            "resource_type": "basalt_vein",
            "position": [3, 2],
            "grade": "high",
            "quantity": 200,
        },
        "description": "High-grade vein discovered near base",
    },
    {
        "tick": 15,
        "type": "storm_start",
        "payload": {"duration": 12, "intensity": 0.6},
        "description": "First dust storm approaches",
    },
    {
        "tick": 25,
        "type": "battery_drain",
        "payload": {"agent_id": "rover-mistral", "amount": 0.15},
        "description": "Storm damage to rover-mistral",
    },
    {
        "tick": 35,
        "type": "storm_end",
        "payload": {},
        "description": "Storm clears",
    },
    {
        "tick": 40,
        "type": "resource_spawn",
        "payload": {
            "resource_type": "ice",
            "position": [5, -3],
            "quantity": 50,
        },
        "description": "Ice deposit detected by orbital scan",
    },
    {
        "tick": 50,
        "type": "agent_message",
        "payload": {
            "from": "station",
            "to": "rover-mistral",
            "message": "Priority shift: focus on delivering collected basalt to station.",
        },
        "description": "Station priority directive",
    },
    {
        "tick": 60,
        "type": "storm_start",
        "payload": {"duration": 20, "intensity": 0.8},
        "description": "Major dust storm incoming",
    },
    {
        "tick": 70,
        "type": "battery_set",
        "payload": {"agent_id": "drone-mistral", "level": 0.3},
        "description": "Drone damaged by storm — low battery",
    },
    {
        "tick": 85,
        "type": "storm_end",
        "payload": {},
        "description": "Major storm passes",
    },
    {
        "tick": 90,
        "type": "resource_spawn",
        "payload": {
            "resource_type": "basalt_vein",
            "position": [-4, 6],
            "grade": "pristine",
            "quantity": 800,
        },
        "description": "Pristine vein discovered in north quadrant",
    },
    {
        "tick": 100,
        "type": "mission_update",
        "payload": {"target_quantity": 200},
        "description": "Mission objective reduced — extraction deadline approaching",
    },
]
