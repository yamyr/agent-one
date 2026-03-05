"""Tests for the simulation replay API endpoints.

Verifies that training session, snapshot, and event retrieval endpoints
work correctly for the replay UI feature.
"""

from tests.conftest import CaseWithDB

from app.training_logger import TrainingLogger
from app.training_models import (
    SessionConfig,
    SessionResult,
    TrainingEvent,
    TrainingTurn,
)


class TestReplaySessionList(CaseWithDB):
    """Test listing training sessions for the replay picker."""

    def _make_logger(self):
        tl = TrainingLogger()
        tl._enabled = True
        tl.init_schema()
        return tl

    async def test_list_sessions_empty(self):
        tl = self._make_logger()
        sessions = tl.list_sessions()
        self.assertEqual(sessions, [])

    async def test_list_sessions_returns_sessions(self):
        tl = self._make_logger()
        sid1 = tl.start_session(SessionConfig(active_agents=["rover-mistral"]))
        sid2 = tl.start_session(SessionConfig(active_agents=["rover-mistral", "drone-mistral"]))

        sessions = tl.list_sessions()
        self.assertEqual(len(sessions), 2)
        # RecordID objects: extract string ID for comparison
        session_ids = [str(getattr(s["id"], "id", s["id"])) for s in sessions]
        self.assertIn(sid1, session_ids)
        self.assertIn(sid2, session_ids)

    async def test_list_sessions_pagination(self):
        tl = self._make_logger()
        for i in range(5):
            tl.start_session(SessionConfig(active_agents=[f"rover-{i}"]))
            tl._session_id = None  # Allow creating multiple sessions

        sessions = tl.list_sessions(limit=2)
        self.assertEqual(len(sessions), 2)

        sessions_offset = tl.list_sessions(limit=2, offset=2)
        self.assertEqual(len(sessions_offset), 2)

    async def test_list_sessions_includes_status(self):
        tl = self._make_logger()
        tl.start_session(SessionConfig())
        result = SessionResult(total_ticks=100, duration_seconds=60.0)
        tl.end_session(result, status="success")

        sessions = tl.list_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["status"], "success")


class TestReplaySessionDetail(CaseWithDB):
    """Test getting session detail for replay header."""

    def _make_logger(self):
        tl = TrainingLogger()
        tl._enabled = True
        tl.init_schema()
        return tl

    async def test_get_session_with_stats(self):
        tl = self._make_logger()
        sid = tl.start_session(SessionConfig(active_agents=["rover-mistral"]))

        # Add some turns and events
        tl.log_turn(
            TrainingTurn(
                tick=1,
                agent_id="rover-mistral",
                agent_type="rover",
                action_name="move",
                action_ok=True,
            )
        )
        tl.log_event(TrainingEvent(tick=1, event_name="thinking", source="rover-mistral"))
        tl.log_world_snapshot(0, {"agents": {}, "tick": 0})

        session = tl.get_session(sid)
        self.assertIsNotNone(session)
        self.assertEqual(session["status"], "running")

        stats = tl.get_session_stats(sid)
        self.assertEqual(stats["turns"], 1)
        self.assertEqual(stats["events"], 1)
        self.assertEqual(stats["snapshots"], 1)

    async def test_get_nonexistent_session(self):
        tl = self._make_logger()
        session = tl.get_session("nonexistent-id")
        self.assertIsNone(session)


class TestReplaySnapshots(CaseWithDB):
    """Test retrieving world snapshots for replay playback."""

    def _make_logger(self):
        tl = TrainingLogger()
        tl._enabled = True
        tl._snapshot_interval = 1  # Log every tick for testing
        tl.init_schema()
        return tl

    async def test_get_snapshots_ordered_by_tick(self):
        tl = self._make_logger()
        tl.start_session(SessionConfig())

        world_states = [
            {"agents": {"rover": {"position": [0, 0]}}, "tick": 0},
            {"agents": {"rover": {"position": [1, 0]}}, "tick": 1},
            {"agents": {"rover": {"position": [2, 0]}}, "tick": 2},
        ]
        for i, ws in enumerate(world_states):
            tl.log_world_snapshot(i, ws)

        snapshots = tl.get_snapshots(tl.session_id)
        self.assertEqual(len(snapshots), 3)
        # Verify ordering by tick
        ticks = [s["tick"] for s in snapshots]
        self.assertEqual(ticks, [0, 1, 2])

    async def test_snapshots_contain_world_state(self):
        tl = self._make_logger()
        tl.start_session(SessionConfig())

        world_state = {
            "agents": {
                "rover-mistral": {
                    "position": [5, 3],
                    "battery": 0.8,
                    "type": "rover",
                    "inventory": [],
                    "visited": [[5, 3]],
                }
            },
            "stones": [{"position": [7, 4], "grade": "high", "quantity": 50}],
            "obstacles": [{"position": [3, 3], "kind": "mountain"}],
            "solar_panels": [],
            "structures": [],
            "storm": {"phase": "clear", "intensity": 0},
            "mission": {"status": "running", "collected": 10, "target_quantity": 300},
            "tick": 5,
        }
        tl.log_world_snapshot(5, world_state)

        snapshots = tl.get_snapshots(tl.session_id)
        self.assertEqual(len(snapshots), 1)
        ws = snapshots[0]["world_state"]
        self.assertIn("agents", ws)
        self.assertIn("rover-mistral", ws["agents"])
        self.assertEqual(ws["agents"]["rover-mistral"]["position"], [5, 3])
        self.assertIn("stones", ws)
        self.assertIn("storm", ws)

    async def test_snapshots_pagination(self):
        tl = self._make_logger()
        tl.start_session(SessionConfig())

        for i in range(10):
            tl.log_world_snapshot(i, {"tick": i})

        first_page = tl.get_snapshots(tl.session_id, limit=3)
        self.assertEqual(len(first_page), 3)
        self.assertEqual(first_page[0]["tick"], 0)

        second_page = tl.get_snapshots(tl.session_id, limit=3, offset=3)
        self.assertEqual(len(second_page), 3)
        self.assertEqual(second_page[0]["tick"], 3)

    async def test_snapshots_empty_session(self):
        tl = self._make_logger()
        tl.start_session(SessionConfig())
        snapshots = tl.get_snapshots(tl.session_id)
        self.assertEqual(snapshots, [])


class TestReplayEvents(CaseWithDB):
    """Test retrieving events for replay timeline."""

    def _make_logger(self):
        tl = TrainingLogger()
        tl._enabled = True
        tl.init_schema()
        return tl

    async def test_get_events_ordered_by_tick(self):
        tl = self._make_logger()
        tl.start_session(SessionConfig())

        events = [
            TrainingEvent(tick=1, event_name="thinking", source="rover"),
            TrainingEvent(tick=3, event_name="mission_success", source="world"),
            TrainingEvent(tick=2, event_name="alert", source="station"),
        ]
        for ev in events:
            tl.log_event(ev)

        result = tl.get_events(tl.session_id)
        self.assertEqual(len(result), 3)
        ticks = [e["tick"] for e in result]
        self.assertEqual(ticks, [1, 2, 3])

    async def test_events_contain_payload(self):
        tl = self._make_logger()
        tl.start_session(SessionConfig())

        tl.log_event(
            TrainingEvent(
                tick=5,
                source="rover-mistral",
                event_type="action",
                event_name="thinking",
                payload={"thought": "I should move east"},
            )
        )

        events = tl.get_events(tl.session_id)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_name"], "thinking")
        self.assertEqual(events[0]["source"], "rover-mistral")
        self.assertIn("thought", events[0]["payload"])

    async def test_events_pagination(self):
        tl = self._make_logger()
        tl.start_session(SessionConfig())

        for i in range(8):
            tl.log_event(TrainingEvent(tick=i, event_name=f"event_{i}"))

        page1 = tl.get_events(tl.session_id, limit=3)
        self.assertEqual(len(page1), 3)

        page2 = tl.get_events(tl.session_id, limit=3, offset=3)
        self.assertEqual(len(page2), 3)

    async def test_events_empty_session(self):
        tl = self._make_logger()
        tl.start_session(SessionConfig())
        events = tl.get_events(tl.session_id)
        self.assertEqual(events, [])


class TestReplayEndToEnd(CaseWithDB):
    """End-to-end test simulating a full replay workflow."""

    def _make_logger(self):
        tl = TrainingLogger()
        tl._enabled = True
        tl._snapshot_interval = 1
        tl.init_schema()
        return tl

    async def test_full_replay_workflow(self):
        """Simulate creating a session, then loading it for replay."""
        tl = self._make_logger()

        # 1. Create session with config
        sid = tl.start_session(
            SessionConfig(
                active_agents=["rover-mistral", "drone-mistral"],
                world_seed="test-seed",
                target_quantity=100,
            )
        )

        # 2. Log some ticks with snapshots and events
        for tick in range(5):
            tl.log_world_snapshot(
                tick,
                {
                    "agents": {
                        "rover-mistral": {
                            "position": [tick, 0],
                            "battery": 1.0 - tick * 0.05,
                            "type": "rover",
                            "inventory": [],
                            "visited": [[i, 0] for i in range(tick + 1)],
                        },
                        "drone-mistral": {
                            "position": [0, tick],
                            "battery": 1.0 - tick * 0.03,
                            "type": "drone",
                            "inventory": [],
                            "visited": [[0, i] for i in range(tick + 1)],
                        },
                    },
                    "stones": [],
                    "obstacles": [],
                    "solar_panels": [],
                    "structures": [],
                    "storm": {"phase": "clear", "intensity": 0},
                    "mission": {
                        "status": "running",
                        "collected": tick * 10,
                        "target_quantity": 100,
                    },
                    "tick": tick,
                },
            )
            if tick % 2 == 0:
                tl.log_event(
                    TrainingEvent(
                        tick=tick,
                        source="rover-mistral",
                        event_type="action",
                        event_name="thinking",
                        payload={"thought": f"tick {tick}"},
                    )
                )

        # 3. End session
        result = SessionResult(
            total_ticks=5,
            basalt_collected=40,
            duration_seconds=25.0,
        )
        tl.end_session(result, status="success")

        # 4. Replay: list sessions
        sessions = tl.list_sessions()
        self.assertGreaterEqual(len(sessions), 1)
        replay_session = next(s for s in sessions if str(getattr(s["id"], "id", s["id"])) == sid)
        self.assertEqual(replay_session["status"], "success")

        # 5. Replay: load snapshots
        snapshots = tl.get_snapshots(sid, limit=100)
        self.assertEqual(len(snapshots), 5)

        # Verify first and last snapshot
        first = snapshots[0]
        self.assertEqual(first["tick"], 0)
        self.assertEqual(first["world_state"]["agents"]["rover-mistral"]["position"], [0, 0])

        last = snapshots[-1]
        self.assertEqual(last["tick"], 4)
        self.assertEqual(last["world_state"]["agents"]["rover-mistral"]["position"], [4, 0])

        # 6. Replay: load events
        events = tl.get_events(sid, limit=100)
        self.assertEqual(len(events), 3)  # ticks 0, 2, 4

        # 7. Verify stats
        stats = tl.get_session_stats(sid)
        self.assertEqual(stats["snapshots"], 5)
        self.assertEqual(stats["events"], 3)
