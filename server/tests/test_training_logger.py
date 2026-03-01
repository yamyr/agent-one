"""Tests for the training data logging system (TrainingLogger + SurrealDB)."""

import unittest

from tests.conftest import CaseWithDB

from app.training_logger import TrainingLogger
from app.training_models import (
    SessionConfig,
    SessionResult,
    TrainingEvent,
    TrainingTurn,
    TurnWorldSnapshot,
)


class TestTrainingLoggerDisabled(unittest.TestCase):
    """When training_data_enabled=False, logger should be a no-op."""

    def test_disabled_logger_returns_empty(self):
        logger = TrainingLogger()
        logger._enabled = False
        sid = logger.start_session(SessionConfig())
        self.assertEqual(sid, "")
        self.assertIsNone(logger.session_id)


class TestTrainingLoggerDB(CaseWithDB):
    """Integration tests with real SurrealDB."""

    def _make_logger(self):
        tl = TrainingLogger()
        tl._enabled = True
        tl.init_schema()
        return tl

    async def test_init_schema_creates_tables(self):
        tl = self._make_logger()
        # Schema init should succeed (no exception)
        self.assertTrue(tl.enabled)

    async def test_session_lifecycle(self):
        tl = self._make_logger()
        sid = tl.start_session(SessionConfig(active_agents=["rover-mistral"]))
        self.assertIsNotNone(sid)
        self.assertTrue(len(sid) > 0)
        self.assertEqual(tl.session_id, sid)

        # Session should be retrievable
        session = tl.get_session(sid)
        self.assertIsNotNone(session)
        self.assertEqual(session["status"], "running")
        self.assertIsNone(session["ended_at"])

        # End session
        result = SessionResult(total_ticks=42, basalt_collected=10, duration_seconds=120.0)
        tl.end_session(result, status="success")

        session = tl.get_session(sid)
        self.assertEqual(session["status"], "success")
        self.assertIsNotNone(session["ended_at"])
        self.assertEqual(session["result"]["total_ticks"], 42)

    async def test_list_sessions(self):
        tl = self._make_logger()
        tl.start_session(SessionConfig())
        sessions = tl.list_sessions()
        self.assertGreaterEqual(len(sessions), 1)

    async def test_log_turn(self):
        tl = self._make_logger()
        sid = tl.start_session(SessionConfig())

        turn = TrainingTurn(
            tick=5,
            agent_id="rover-mistral",
            agent_type="rover",
            context="You are a rover on Mars.",
            world_snapshot=TurnWorldSnapshot(
                agent_position=[3, 4],
                agent_battery=0.8,
            ),
            thinking="I should move east.",
            action_name="move",
            action_params={"direction": "east", "distance": 2},
            action_result={"ok": True, "position": [5, 4]},
            action_ok=True,
            battery_before=0.8,
            battery_after=0.75,
            position_before=[3, 4],
            position_after=[5, 4],
            model="mistral-small-latest",
            is_fallback=False,
            llm_duration_ms=450,
        )
        tl.log_turn(turn)

        turns = tl.get_turns(sid)
        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0]["agent_id"], "rover-mistral")
        self.assertEqual(turns[0]["action_name"], "move")
        self.assertEqual(turns[0]["tick"], 5)
        self.assertTrue(turns[0]["action_ok"])

    async def test_log_event(self):
        tl = self._make_logger()
        sid = tl.start_session(SessionConfig())

        event = TrainingEvent(
            tick=10,
            source="world",
            event_type="event",
            event_name="mission_success",
            payload={"collected": 300, "target": 300},
        )
        tl.log_event(event)

        events = tl.get_events(sid)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_name"], "mission_success")

    async def test_log_world_snapshot(self):
        tl = self._make_logger()
        sid = tl.start_session(SessionConfig())

        world_state = {"agents": {"rover": {"position": [1, 2]}}, "tick": 10}
        tl.log_world_snapshot(10, world_state)

        snapshots = tl.get_snapshots(sid)
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["tick"], 10)

    async def test_snapshot_interval_enforcement(self):
        tl = self._make_logger()
        tl._snapshot_interval = 5
        tl.start_session(SessionConfig())

        tl.log_world_snapshot(0, {"tick": 0})
        tl.log_world_snapshot(2, {"tick": 2})  # Should be skipped (interval=5)
        tl.log_world_snapshot(5, {"tick": 5})  # Should be logged

        snapshots = tl.get_snapshots(tl.session_id)
        self.assertEqual(len(snapshots), 2)  # tick 0 and tick 5

    async def test_maybe_log_broadcast_event_filters(self):
        tl = self._make_logger()
        tl.start_session(SessionConfig())

        # Loggable event
        tl.maybe_log_broadcast_event(
            {"name": "mission_success", "source": "world", "type": "event", "payload": {}}, tick=5
        )
        # Non-loggable event (state is not in LOGGABLE_EVENTS)
        tl.maybe_log_broadcast_event(
            {"name": "state", "source": "world", "type": "event", "payload": {}}, tick=5
        )

        events = tl.get_events(tl.session_id)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_name"], "mission_success")

    async def test_session_stats(self):
        tl = self._make_logger()
        sid = tl.start_session(SessionConfig())

        # Log 2 rover turns and 1 drone turn
        for tick in range(2):
            tl.log_turn(
                TrainingTurn(
                    tick=tick,
                    agent_id="rover-mistral",
                    agent_type="rover",
                    action_name="move",
                    action_ok=True,
                )
            )
        tl.log_turn(
            TrainingTurn(
                tick=2,
                agent_id="drone-mistral",
                agent_type="drone",
                action_name="scan",
                action_ok=True,
            )
        )
        tl.log_event(TrainingEvent(tick=1, event_name="test_event"))

        stats = tl.get_session_stats(sid)
        self.assertEqual(stats["turns"], 3)
        self.assertEqual(stats["events"], 1)
        self.assertEqual(stats["turns_by_agent_type"].get("rover"), 2)
        self.assertEqual(stats["turns_by_agent_type"].get("drone"), 1)

    async def test_export_session_jsonl(self):
        tl = self._make_logger()
        sid = tl.start_session(SessionConfig())

        tl.log_turn(
            TrainingTurn(
                tick=1,
                agent_id="rover-mistral",
                agent_type="rover",
                context="System prompt here.",
                thinking="I need to dig.",
                action_name="dig",
                action_params={},
                action_result={"ok": True},
                action_ok=True,
            )
        )

        records = tl.export_session_jsonl(sid)
        self.assertEqual(len(records), 1)
        record = records[0]

        # Validate Mistral fine-tuning format
        self.assertIn("messages", record)
        messages = record["messages"]
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[2]["role"], "assistant")
        self.assertEqual(messages[3]["role"], "tool")

        # Meta should contain session_id
        self.assertEqual(record["meta"]["session_id"], sid)
        self.assertEqual(record["meta"]["agent_type"], "rover")


class TestSafeJsonStr(unittest.TestCase):
    """Unit tests for _safe_json_str helper."""

    def test_serializes_dict(self):
        from app.training_logger import _safe_json_str

        result = _safe_json_str({"key": "value", "num": 42})
        self.assertIn('"key"', result)
        self.assertIn("42", result)

    def test_handles_non_serializable(self):
        from app.training_logger import _safe_json_str

        result = _safe_json_str({"obj": object()})
        self.assertIn("obj", result)

    def test_empty_dict(self):
        from app.training_logger import _safe_json_str

        self.assertEqual(_safe_json_str({}), "{}")

    def test_serializes_nested(self):
        from app.training_logger import _safe_json_str

        result = _safe_json_str({"a": [1, 2, {"b": True}]})
        self.assertIn('"a"', result)
        self.assertIn("true", result)


class TestBuildTurnSnapshot(unittest.TestCase):
    """Unit tests for _build_turn_snapshot helper."""

    def test_basic_snapshot(self):
        from unittest.mock import MagicMock

        from app.agent import _build_turn_snapshot

        world = MagicMock()
        world.get_agents.return_value = {"station": {"position": [5, 5]}}
        world.get_mission.return_value = {
            "status": "running",
            "collected": 10,
            "target_quantity": 100,
        }

        agent_state = {
            "position": [3, 4],
            "battery": 0.75,
            "inventory": [{"type": "basalt", "grade": "A", "quantity": 1}],
            "memory": ["moved east", "dug rock"],
            "tasks": ["collect basalt"],
        }

        snap = _build_turn_snapshot(agent_state, world)
        self.assertEqual(snap.agent_position, [3, 4])
        self.assertAlmostEqual(snap.agent_battery, 0.75)
        self.assertEqual(snap.distance_to_station, 3)
        self.assertEqual(snap.mission_status, "running")
        self.assertEqual(snap.collected_quantity, 10)

    def test_missing_fields_default_safely(self):
        from unittest.mock import MagicMock

        from app.agent import _build_turn_snapshot

        world = MagicMock()
        world.get_agents.return_value = {}
        world.get_mission.return_value = {}

        snap = _build_turn_snapshot({}, world)
        self.assertEqual(snap.agent_position, [0, 0])
        self.assertEqual(snap.agent_battery, 0)
        self.assertEqual(snap.distance_to_station, 0)

    def test_invalid_position_type(self):
        from unittest.mock import MagicMock

        from app.agent import _build_turn_snapshot

        world = MagicMock()
        world.get_agents.return_value = {"station": {"position": "invalid"}}
        world.get_mission.return_value = None

        agent_state = {"position": "not-a-list", "battery": "not-a-number"}
        snap = _build_turn_snapshot(agent_state, world)
        self.assertEqual(snap.agent_position, [0, 0])
        self.assertEqual(snap.agent_battery, 0)
