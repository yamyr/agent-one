"""Tests for elapsed time tracking and session duration persistence."""

import asyncio
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.host import Host
from app.narrator import Narrator
from app.training_logger import TrainingLogger
from app.training_models import SessionConfig, SessionResult
from app.world import get_snapshot, set_elapsed_provider
from tests.conftest import CaseWithDB


def _make_host():
    """Create a Host with a mocked narrator for testing."""
    narrator = MagicMock(spec=Narrator)
    narrator.feed = AsyncMock()
    narrator.reset = MagicMock()
    narrator.start = MagicMock()
    narrator.stop = MagicMock()
    return Host(narrator=narrator)


# ── Host.paused property ──


class TestHostPausedProperty(unittest.TestCase):
    """Test that paused property setter tracks pause duration."""

    def test_paused_default_false(self):
        host = _make_host()
        self.assertFalse(host.paused)

    def test_set_paused_true(self):
        host = _make_host()
        host.paused = True
        self.assertTrue(host.paused)
        self.assertIsNotNone(host._pause_start_time)

    def test_set_paused_false_after_true(self):
        host = _make_host()
        host.paused = True
        self.assertIsNotNone(host._pause_start_time)
        host.paused = False
        self.assertFalse(host.paused)
        self.assertIsNone(host._pause_start_time)
        self.assertGreater(host._total_paused_duration, 0.0)

    def test_setting_paused_true_twice_no_double_track(self):
        """Setting paused=True when already paused should not reset the pause start."""
        host = _make_host()
        host.paused = True
        first_start = host._pause_start_time
        host.paused = True  # no-op since already paused
        self.assertEqual(host._pause_start_time, first_start)

    def test_setting_paused_false_twice_no_double_add(self):
        """Setting paused=False when already unpaused should not add zero duration."""
        host = _make_host()
        host.paused = True
        host.paused = False
        dur1 = host._total_paused_duration
        host.paused = False  # no-op since already unpaused
        self.assertEqual(host._total_paused_duration, dur1)


# ── Host.get_elapsed_seconds ──


class TestHostElapsedSeconds(unittest.TestCase):
    """Test elapsed time calculation excluding pause duration."""

    def test_zero_before_start(self):
        host = _make_host()
        self.assertEqual(host.get_elapsed_seconds(), 0.0)

    def test_positive_after_start(self):
        host = _make_host()
        host._session_start_time = time.monotonic() - 5.0
        elapsed = host.get_elapsed_seconds()
        self.assertGreaterEqual(elapsed, 4.5)  # Allow small timing variance
        self.assertLessEqual(elapsed, 6.0)

    def test_excludes_paused_time(self):
        host = _make_host()
        host._session_start_time = time.monotonic() - 10.0
        host._total_paused_duration = 3.0
        elapsed = host.get_elapsed_seconds()
        self.assertGreaterEqual(elapsed, 6.5)
        self.assertLessEqual(elapsed, 8.0)

    def test_excludes_current_pause(self):
        """While paused, current pause time is also excluded."""
        host = _make_host()
        host._session_start_time = time.monotonic() - 10.0
        host._paused = True
        host._pause_start_time = time.monotonic() - 5.0
        elapsed = host.get_elapsed_seconds()
        # Should be ~5s (10s total - 5s paused)
        self.assertGreaterEqual(elapsed, 4.0)
        self.assertLessEqual(elapsed, 6.0)


# ── Host.start() resets pause tracking ──


class TestHostStartResetsPauseTracking(unittest.TestCase):
    def test_start_resets_pause_fields(self):
        host = _make_host()
        host._total_paused_duration = 42.0
        host._pause_start_time = time.monotonic()
        host._paused = True

        with patch("app.host.broadcaster") as mock_bc:
            mock_bc.send = AsyncMock()
            with patch.object(host, "station_startup", new_callable=AsyncMock):
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(host.start())
                    loop.run_until_complete(asyncio.sleep(0.05))
                finally:
                    host.stop()
                    loop.close()

        self.assertFalse(host._paused)
        # start() sets _session_start_time to a fresh value
        self.assertIsNone(host._pause_start_time)


# ── get_snapshot() includes elapsed_seconds ──


class TestGetSnapshotElapsedSeconds(unittest.TestCase):
    def tearDown(self):
        set_elapsed_provider(None)

    def test_default_zero_when_no_provider(self):
        set_elapsed_provider(None)
        snap = get_snapshot()
        self.assertEqual(snap["elapsed_seconds"], 0.0)

    def test_uses_provider_when_set(self):
        set_elapsed_provider(lambda: 42.5)
        snap = get_snapshot()
        self.assertAlmostEqual(snap["elapsed_seconds"], 42.5)


# ── TrainingLogger.end_session idempotency ──


class TestEndSessionIdempotency(CaseWithDB):
    def _make_logger(self):
        tl = TrainingLogger()
        tl._enabled = True
        tl.init_schema()
        return tl

    async def test_end_session_clears_session_id(self):
        tl = self._make_logger()
        tl.start_session(SessionConfig())
        self.assertIsNotNone(tl.session_id)

        result = SessionResult(duration_seconds=10.0)
        tl.end_session(result, status="success")
        self.assertIsNone(tl.session_id)

    async def test_end_session_twice_no_crash(self):
        """Calling end_session twice should not raise (idempotent)."""
        tl = self._make_logger()
        tl.start_session(SessionConfig())

        result = SessionResult(duration_seconds=5.0)
        tl.end_session(result, status="success")
        # Second call should be a no-op (session_id is None now)
        tl.end_session(result, status="success")
        self.assertIsNone(tl.session_id)


# ── Session duration_seconds persistence ──


class TestSessionDurationPersistence(CaseWithDB):
    def _make_logger(self):
        tl = TrainingLogger()
        tl._enabled = True
        tl.init_schema()
        return tl

    async def test_duration_seconds_stored(self):
        tl = self._make_logger()
        sid = tl.start_session(SessionConfig())

        result = SessionResult(duration_seconds=123.45)
        tl.end_session(result, status="success")

        session = tl.get_session(sid)
        self.assertIsNotNone(session)
        self.assertAlmostEqual(session["duration_seconds"], 123.45, places=1)

    async def test_duration_seconds_in_result(self):
        tl = self._make_logger()
        sid = tl.start_session(SessionConfig())

        result = SessionResult(total_ticks=10, duration_seconds=60.0)
        tl.end_session(result, status="success")

        session = tl.get_session(sid)
        self.assertAlmostEqual(session["result"]["duration_seconds"], 60.0, places=1)


# ── Host.broadcast finalizes session on mission events ──


class TestBroadcastFinalizesSession(unittest.TestCase):
    def test_mission_success_ends_session(self):
        host = _make_host()
        host._session_start_time = time.monotonic() - 30.0

        with patch("app.host.training_logger") as mock_tl:
            mock_tl.maybe_log_broadcast_event = MagicMock()
            mock_tl.end_session = MagicMock()

            with patch("app.host.broadcaster") as mock_bc:
                mock_bc.send = AsyncMock()
                msg = {
                    "name": "mission_success",
                    "source": "world",
                    "type": "event",
                    "payload": {"collected_quantity": 300},
                }
                asyncio.run(host.broadcast(msg))

            mock_tl.end_session.assert_called_once()
            call_args = mock_tl.end_session.call_args
            result = call_args[0][0]
            self.assertIsInstance(result, SessionResult)
            self.assertEqual(call_args[1]["status"], "success")
            self.assertGreater(result.duration_seconds, 0.0)

    def test_mission_failed_ends_session(self):
        host = _make_host()
        host._session_start_time = time.monotonic() - 15.0

        with patch("app.host.training_logger") as mock_tl:
            mock_tl.maybe_log_broadcast_event = MagicMock()
            mock_tl.end_session = MagicMock()

            with patch("app.host.broadcaster") as mock_bc:
                mock_bc.send = AsyncMock()
                msg = {
                    "name": "mission_failed",
                    "source": "world",
                    "type": "event",
                    "payload": {},
                }
                asyncio.run(host.broadcast(msg))

            mock_tl.end_session.assert_called_once()
            self.assertEqual(mock_tl.end_session.call_args[1]["status"], "failed")

    def test_regular_event_does_not_end_session(self):
        host = _make_host()

        with patch("app.host.training_logger") as mock_tl:
            mock_tl.maybe_log_broadcast_event = MagicMock()
            mock_tl.end_session = MagicMock()

            with patch("app.host.broadcaster") as mock_bc:
                mock_bc.send = AsyncMock()
                msg = {
                    "name": "state",
                    "source": "world",
                    "type": "event",
                    "payload": {},
                }
                asyncio.run(host.broadcast(msg))

            mock_tl.end_session.assert_not_called()
