"""TrainingLogger — SurrealDB persistence for training data.

Records agent turns, events, and world snapshots for replay and fine-tuning.
All writes are fire-and-forget (logged errors, never blocks simulation).
"""

from __future__ import annotations

import logging
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from .config import settings
from .db import get_db_sync
from .training_models import (
    SessionConfig,
    SessionResult,
    TrainingEvent,
    TrainingSession,
    TrainingTurn,
)

logger = logging.getLogger(__name__)

# SurrealDB schema definitions
_SCHEMA_QUERIES = [
    "DEFINE TABLE IF NOT EXISTS training_session SCHEMAFULL",
    "DEFINE FIELD IF NOT EXISTS started_at ON training_session TYPE datetime",
    "DEFINE FIELD IF NOT EXISTS ended_at ON training_session TYPE option<datetime>",
    "DEFINE FIELD IF NOT EXISTS status ON training_session TYPE string DEFAULT 'running'",
    "DEFINE FIELD IF NOT EXISTS config ON training_session TYPE object FLEXIBLE",
    "DEFINE FIELD IF NOT EXISTS result ON training_session TYPE option<object> FLEXIBLE",
    "DEFINE FIELD IF NOT EXISTS tags ON training_session TYPE array DEFAULT []",
    "DEFINE INDEX IF NOT EXISTS idx_session_status ON training_session FIELDS status",
    "DEFINE TABLE IF NOT EXISTS training_turn SCHEMAFULL",
    "DEFINE FIELD IF NOT EXISTS session_id ON training_turn TYPE string",
    "DEFINE FIELD IF NOT EXISTS tick ON training_turn TYPE int",
    "DEFINE FIELD IF NOT EXISTS agent_id ON training_turn TYPE string",
    "DEFINE FIELD IF NOT EXISTS agent_type ON training_turn TYPE string",
    "DEFINE FIELD IF NOT EXISTS timestamp ON training_turn TYPE datetime",
    "DEFINE FIELD IF NOT EXISTS context ON training_turn TYPE string DEFAULT ''",
    "DEFINE FIELD IF NOT EXISTS world_snapshot ON training_turn TYPE object FLEXIBLE",
    "DEFINE FIELD IF NOT EXISTS thinking ON training_turn TYPE option<string>",
    "DEFINE FIELD IF NOT EXISTS action_name ON training_turn TYPE string DEFAULT ''",
    "DEFINE FIELD IF NOT EXISTS action_params ON training_turn TYPE object FLEXIBLE",
    "DEFINE FIELD IF NOT EXISTS action_result ON training_turn TYPE object FLEXIBLE",
    "DEFINE FIELD IF NOT EXISTS action_ok ON training_turn TYPE bool DEFAULT false",
    "DEFINE FIELD IF NOT EXISTS battery_before ON training_turn TYPE float DEFAULT 1.0",
    "DEFINE FIELD IF NOT EXISTS battery_after ON training_turn TYPE float DEFAULT 1.0",
    "DEFINE FIELD IF NOT EXISTS position_before ON training_turn TYPE array DEFAULT [0, 0]",
    "DEFINE FIELD IF NOT EXISTS position_after ON training_turn TYPE array DEFAULT [0, 0]",
    "DEFINE FIELD IF NOT EXISTS model ON training_turn TYPE string DEFAULT ''",
    "DEFINE FIELD IF NOT EXISTS is_fallback ON training_turn TYPE bool DEFAULT false",
    "DEFINE FIELD IF NOT EXISTS llm_duration_ms ON training_turn TYPE option<int>",
    "DEFINE INDEX IF NOT EXISTS idx_turn_session ON training_turn FIELDS session_id",
    "DEFINE INDEX IF NOT EXISTS idx_turn_agent ON training_turn FIELDS agent_id",
    "DEFINE INDEX IF NOT EXISTS idx_turn_tick ON training_turn FIELDS session_id, tick",
    "DEFINE TABLE IF NOT EXISTS training_event SCHEMAFULL",
    "DEFINE FIELD IF NOT EXISTS session_id ON training_event TYPE string",
    "DEFINE FIELD IF NOT EXISTS tick ON training_event TYPE int",
    "DEFINE FIELD IF NOT EXISTS timestamp ON training_event TYPE datetime",
    "DEFINE FIELD IF NOT EXISTS source ON training_event TYPE string DEFAULT ''",
    "DEFINE FIELD IF NOT EXISTS event_type ON training_event TYPE string DEFAULT ''",
    "DEFINE FIELD IF NOT EXISTS event_name ON training_event TYPE string DEFAULT ''",
    "DEFINE FIELD IF NOT EXISTS payload ON training_event TYPE object FLEXIBLE",
    "DEFINE INDEX IF NOT EXISTS idx_event_session ON training_event FIELDS session_id",
    "DEFINE TABLE IF NOT EXISTS training_world_snapshot SCHEMAFULL",
    "DEFINE FIELD IF NOT EXISTS session_id ON training_world_snapshot TYPE string",
    "DEFINE FIELD IF NOT EXISTS tick ON training_world_snapshot TYPE int",
    "DEFINE FIELD IF NOT EXISTS timestamp ON training_world_snapshot TYPE datetime",
    "DEFINE FIELD IF NOT EXISTS world_state ON training_world_snapshot TYPE object FLEXIBLE",
    "DEFINE INDEX IF NOT EXISTS idx_snapshot_session ON training_world_snapshot FIELDS session_id",
]

# Events worth logging (skip noisy ones like every state broadcast)
LOGGABLE_EVENTS = frozenset(
    {
        "thinking",
        "mission_success",
        "mission_failed",
        "mission_aborted",
        "charge_agent",
        "alert",
        "assign_mission",
        "recall",
        "check",
        "intel_relay",
        "task_update",
        "insight",
        "world_event",
    }
)


class TrainingLogger:
    """Logs training data to SurrealDB. Thread-safe, fire-and-forget writes."""

    def __init__(self):
        self._enabled = settings.training_data_enabled
        self._snapshot_interval = settings.training_snapshot_interval
        self._session_id: str | None = None
        self._last_snapshot_tick: int = -1

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def session_id(self) -> str | None:
        return self._session_id

    def init_schema(self) -> None:
        """Create SurrealDB tables/fields if they don't exist. Call once at startup."""
        if not self._enabled:
            return
        try:
            db = get_db_sync()
            try:
                for q in _SCHEMA_QUERIES:
                    db.query(q)
                logger.info(
                    "Training data schema initialized (%d definitions)", len(_SCHEMA_QUERIES)
                )
            finally:
                db.close()
        except Exception:
            logger.exception(
                "Failed to initialize training schema — training data will not be persisted"
            )
            self._enabled = False

    def start_session(self, config: SessionConfig) -> str:
        """Create a new training session record. Returns session_id."""
        if not self._enabled:
            return ""
        session_id = str(uuid.uuid4())
        self._session_id = session_id
        self._last_snapshot_tick = -1
        session = TrainingSession(config=config)
        try:
            db = get_db_sync()
            try:
                db.create(
                    "training_session",
                    {
                        "id": session_id,
                        "started_at": session.started_at,
                        "ended_at": None,
                        "status": session.status,
                        "config": config.model_dump(),
                        "result": None,
                        "tags": session.tags,
                    },
                )
                logger.info("Training session started: %s", session_id)
            finally:
                db.close()
        except Exception:
            logger.exception("Failed to create training session")
        return session_id

    def end_session(self, result: SessionResult, status: str = "success") -> None:
        """Finalize the current training session."""
        if not self._enabled or not self._session_id:
            return
        try:
            db = get_db_sync()
            try:
                db.query(
                    f"UPDATE training_session:`{self._session_id}` SET "
                    "ended_at = $ended_at, status = $status, result = $result",
                    {
                        "ended_at": datetime.now(timezone.utc),
                        "status": status,
                        "result": result.model_dump(),
                    },
                )
                logger.info("Training session ended: %s (status=%s)", self._session_id, status)
            finally:
                db.close()
        except Exception:
            logger.exception("Failed to end training session %s", self._session_id)

    def log_turn(self, turn: TrainingTurn) -> None:
        """Log an agent decision cycle."""
        if not self._enabled or not self._session_id:
            return
        turn.session_id = self._session_id
        try:
            db = get_db_sync()
            try:
                db.create(
                    "training_turn",
                    {
                        "id": str(uuid.uuid4()),
                        "session_id": turn.session_id,
                        "tick": turn.tick,
                        "agent_id": turn.agent_id,
                        "agent_type": turn.agent_type,
                        "timestamp": turn.timestamp,
                        "context": turn.context,
                        "world_snapshot": turn.world_snapshot.model_dump(),
                        "thinking": turn.thinking,
                        "action_name": turn.action_name,
                        "action_params": turn.action_params,
                        "action_result": turn.action_result,
                        "action_ok": turn.action_ok,
                        "battery_before": turn.battery_before,
                        "battery_after": turn.battery_after,
                        "position_before": turn.position_before,
                        "position_after": turn.position_after,
                        "model": turn.model,
                        "is_fallback": turn.is_fallback,
                        "llm_duration_ms": turn.llm_duration_ms,
                    },
                )
            finally:
                db.close()
        except Exception:
            logger.exception(
                "Failed to log training turn (tick=%d, agent=%s)", turn.tick, turn.agent_id
            )

    def log_event(self, event: TrainingEvent) -> None:
        """Log a significant world/mission event."""
        if not self._enabled or not self._session_id:
            return
        event.session_id = self._session_id
        try:
            db = get_db_sync()
            try:
                db.create(
                    "training_event",
                    {
                        "id": str(uuid.uuid4()),
                        "session_id": event.session_id,
                        "tick": event.tick,
                        "timestamp": event.timestamp,
                        "source": event.source,
                        "event_type": event.event_type,
                        "event_name": event.event_name,
                        "payload": event.payload,
                    },
                )
            finally:
                db.close()
        except Exception:
            logger.exception("Failed to log training event (%s)", event.event_name)

    def log_world_snapshot(self, tick: int, world_state: dict[str, Any]) -> None:
        """Log a full world state snapshot (called periodically)."""
        if not self._enabled or not self._session_id:
            return
        # Respect snapshot interval
        if (
            self._last_snapshot_tick >= 0
            and (tick - self._last_snapshot_tick) < self._snapshot_interval
        ):
            return
        self._last_snapshot_tick = tick
        try:
            db = get_db_sync()
            try:
                db.create(
                    "training_world_snapshot",
                    {
                        "id": str(uuid.uuid4()),
                        "session_id": self._session_id,
                        "tick": tick,
                        "timestamp": datetime.now(timezone.utc),
                        "world_state": world_state,
                    },
                )
            finally:
                db.close()
        except Exception:
            logger.exception("Failed to log world snapshot (tick=%d)", tick)

    def maybe_log_broadcast_event(self, msg_dict: dict, tick: int) -> None:
        """Conditionally log a broadcast message as a training event."""
        if not self._enabled or not self._session_id:
            return
        event_name = msg_dict.get("name", "")
        if event_name not in LOGGABLE_EVENTS:
            return
        event = TrainingEvent(
            session_id=self._session_id,
            tick=tick,
            source=msg_dict.get("source", ""),
            event_type=msg_dict.get("type", ""),
            event_name=event_name,
            payload=msg_dict.get("payload", {}),
        )
        self.log_event(event)

    # ── Query methods (for API endpoints) ──

    def list_sessions(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """List training sessions, newest first."""
        try:
            db = get_db_sync()
            try:
                result = db.query(
                    "SELECT * FROM training_session ORDER BY started_at DESC LIMIT $limit START $offset",
                    {"limit": limit, "offset": offset},
                )
                return result if result else []
            finally:
                db.close()
        except Exception:
            logger.exception("Failed to list training sessions")
            return []

    def get_session(self, session_id: str) -> dict | None:
        """Get a single training session by ID."""
        try:
            db = get_db_sync()
            try:
                result = db.query(f"SELECT * FROM training_session:`{session_id}`")
                if not result:
                    return None
                row = result[0]
                # SurrealDB v3 omits None-valued option<T> fields; ensure they exist
                row.setdefault("ended_at", None)
                row.setdefault("result", None)
                return row
            finally:
                db.close()
        except Exception:
            logger.exception("Failed to get training session %s", session_id)
            return None

    def get_turns(self, session_id: str, limit: int = 100, offset: int = 0) -> list[dict]:
        """Get turns for a session, ordered by tick."""
        try:
            db = get_db_sync()
            try:
                result = db.query(
                    "SELECT * FROM training_turn WHERE session_id = $sid "
                    "ORDER BY tick ASC LIMIT $limit START $offset",
                    {"sid": session_id, "limit": limit, "offset": offset},
                )
                return result if result else []
            finally:
                db.close()
        except Exception:
            logger.exception("Failed to get turns for session %s", session_id)
            return []

    def get_events(self, session_id: str, limit: int = 200, offset: int = 0) -> list[dict]:
        """Get events for a session, ordered by tick."""
        try:
            db = get_db_sync()
            try:
                result = db.query(
                    "SELECT * FROM training_event WHERE session_id = $sid "
                    "ORDER BY tick ASC LIMIT $limit START $offset",
                    {"sid": session_id, "limit": limit, "offset": offset},
                )
                return result if result else []
            finally:
                db.close()
        except Exception:
            logger.exception("Failed to get events for session %s", session_id)
            return []

    def get_snapshots(self, session_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get world snapshots for a session, ordered by tick."""
        try:
            db = get_db_sync()
            try:
                result = db.query(
                    "SELECT * FROM training_world_snapshot WHERE session_id = $sid "
                    "ORDER BY tick ASC LIMIT $limit START $offset",
                    {"sid": session_id, "limit": limit, "offset": offset},
                )
                return result if result else []
            finally:
                db.close()
        except Exception:
            logger.exception("Failed to get snapshots for session %s", session_id)
            return []

    def export_session_jsonl(self, session_id: str) -> list[dict]:
        """Export session turns as training-ready JSONL records.

        Each record: {messages: [{role: system, content: context}, {role: assistant, ...}]}
        """
        turns = self.get_turns(session_id, limit=10000)
        records = []
        for turn in turns:
            context = turn.get("context", "")
            action_name = turn.get("action_name", "")
            action_params = turn.get("action_params", {})
            thinking = turn.get("thinking", "")

            # Build assistant message mimicking the LLM output
            assistant_content = thinking or ""
            tool_call = {
                "id": f"call_{turn.get('tick', 0)}",
                "type": "function",
                "function": {
                    "name": action_name,
                    "arguments": _safe_json_str(action_params),
                },
            }
            assistant_msg: dict[str, Any] = {"role": "assistant"}
            if assistant_content:
                assistant_msg["content"] = assistant_content
            assistant_msg["tool_calls"] = [tool_call]

            record = {
                "messages": [
                    {"role": "system", "content": context},
                    {
                        "role": "user",
                        "content": "Observe your surroundings and decide your next move.",
                    },
                    assistant_msg,
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": _safe_json_str(turn.get("action_result", {})),
                    },
                ],
                "meta": {
                    "session_id": session_id,
                    "tick": turn.get("tick"),
                    "agent_id": turn.get("agent_id"),
                    "agent_type": turn.get("agent_type"),
                    "action_ok": turn.get("action_ok"),
                    "is_fallback": turn.get("is_fallback"),
                },
            }
            records.append(record)
        return records

    def get_session_stats(self, session_id: str) -> dict:
        """Compute summary stats for a session."""
        try:
            db = get_db_sync()
            try:
                turn_count = db.query(
                    "SELECT count() AS c FROM training_turn WHERE session_id = $sid GROUP ALL",
                    {"sid": session_id},
                )
                event_count = db.query(
                    "SELECT count() AS c FROM training_event WHERE session_id = $sid GROUP ALL",
                    {"sid": session_id},
                )
                snapshot_count = db.query(
                    "SELECT count() AS c FROM training_world_snapshot WHERE session_id = $sid GROUP ALL",
                    {"sid": session_id},
                )
                agent_breakdown = db.query(
                    "SELECT agent_type, count() AS c FROM training_turn "
                    "WHERE session_id = $sid GROUP BY agent_type",
                    {"sid": session_id},
                )
                return {
                    "turns": _extract_count(turn_count),
                    "events": _extract_count(event_count),
                    "snapshots": _extract_count(snapshot_count),
                    "turns_by_agent_type": {
                        row["agent_type"]: row["c"]
                        for row in (agent_breakdown if agent_breakdown else [])
                    },
                }
            finally:
                db.close()
        except Exception:
            logger.exception("Failed to get session stats for %s", session_id)
            return {"turns": 0, "events": 0, "snapshots": 0, "turns_by_agent_type": {}}


def _extract_count(result) -> int:
    """Extract count from a SurrealDB GROUP ALL result."""
    if not result:
        return 0
    return result[0].get("c", 0) if isinstance(result[0], dict) else 0


def _safe_json_str(obj: Any) -> str:
    """Convert to JSON string, handling non-serializable objects gracefully."""

    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except TypeError, ValueError:
        return "{}"


# Module-level singleton
training_logger = TrainingLogger()
