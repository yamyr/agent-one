"""Tests for simulation control endpoints and narration toggle in app.main."""

import unittest
from unittest.mock import AsyncMock, patch


class TestPauseSimulation(unittest.TestCase):
    """POST /simulation/pause → sets host.paused = True."""

    def test_pause_returns_paused_true(self):
        from app.main import pause_simulation

        with patch("app.main.host"):
            result = pause_simulation()
        self.assertEqual(result, {"paused": True})

    def test_pause_sets_host_paused_true(self):
        from app.main import pause_simulation

        with patch("app.main.host") as mock_host:
            mock_host.paused = False
            pause_simulation()
            # Verify the setter was called with True
            # (PropertyMock not needed — MagicMock attribute assignment is tracked)
        # After calling pause_simulation, host.paused should have been set to True
        self.assertTrue(mock_host.paused)


class TestResumeSimulation(unittest.TestCase):
    """POST /simulation/resume → sets host.paused = False."""

    def test_resume_returns_paused_false(self):
        from app.main import resume_simulation

        with patch("app.main.host"):
            result = resume_simulation()
        self.assertEqual(result, {"paused": False})

    def test_resume_sets_host_paused_false(self):
        from app.main import resume_simulation

        with patch("app.main.host") as mock_host:
            mock_host.paused = True
            resume_simulation()
        self.assertFalse(mock_host.paused)


class TestSimulationStatus(unittest.TestCase):
    """GET /simulation/status → returns current paused state."""

    def test_status_returns_paused_true_when_paused(self):
        from app.main import simulation_status

        with patch("app.main.host") as mock_host:
            mock_host.paused = True
            result = simulation_status()
        self.assertEqual(result, {"paused": True})

    def test_status_returns_paused_false_when_running(self):
        from app.main import simulation_status

        with patch("app.main.host") as mock_host:
            mock_host.paused = False
            result = simulation_status()
        self.assertEqual(result, {"paused": False})


class TestResetSimulation(unittest.IsolatedAsyncioTestCase):
    """POST /simulation/reset → stops host, resets world/narrator, re-registers agents, starts host."""

    async def test_reset_returns_reset_true(self):
        from app.main import reset_simulation

        with (
            patch("app.main.host") as mock_host,
            patch("app.main.narrator"),
            patch("app.main.reset_world"),
            patch("app.main._register_agents"),
        ):
            mock_host.start = AsyncMock()
            result = await reset_simulation()

        self.assertEqual(result, {"reset": True})

    async def test_reset_calls_host_stop(self):
        from app.main import reset_simulation

        with (
            patch("app.main.host") as mock_host,
            patch("app.main.narrator"),
            patch("app.main.reset_world"),
            patch("app.main._register_agents"),
        ):
            mock_host.start = AsyncMock()
            await reset_simulation()
            mock_host.stop.assert_called_once()

    async def test_reset_calls_reset_world(self):
        from app.main import reset_simulation

        with (
            patch("app.main.host") as mock_host,
            patch("app.main.narrator"),
            patch("app.main.reset_world") as mock_reset_world,
            patch("app.main._register_agents"),
        ):
            mock_host.start = AsyncMock()
            await reset_simulation()
            mock_reset_world.assert_called_once()

    async def test_reset_calls_narrator_reset(self):
        from app.main import reset_simulation

        with (
            patch("app.main.host") as mock_host,
            patch("app.main.narrator") as mock_narrator,
            patch("app.main.reset_world"),
            patch("app.main._register_agents"),
        ):
            mock_host.start = AsyncMock()
            await reset_simulation()
            mock_narrator.reset.assert_called_once()

    async def test_reset_calls_register_agents(self):
        from app.main import reset_simulation

        with (
            patch("app.main.host") as mock_host,
            patch("app.main.narrator"),
            patch("app.main.reset_world"),
            patch("app.main._register_agents") as mock_register,
        ):
            mock_host.start = AsyncMock()
            await reset_simulation()
            mock_register.assert_called_once()

    async def test_reset_calls_host_start(self):
        from app.main import reset_simulation

        with (
            patch("app.main.host") as mock_host,
            patch("app.main.narrator"),
            patch("app.main.reset_world"),
            patch("app.main._register_agents"),
        ):
            mock_host.start = AsyncMock()
            await reset_simulation()
            mock_host.start.assert_awaited_once()

    async def test_reset_calls_in_order(self):
        """Verify the reset sequence: stop → reset_world → narrator.reset → register → start."""
        from app.main import reset_simulation

        call_order = []

        with (
            patch("app.main.host") as mock_host,
            patch("app.main.narrator") as mock_narrator,
            patch("app.main.reset_world") as mock_reset_world,
            patch("app.main._register_agents") as mock_register,
        ):
            mock_host.stop.side_effect = lambda: call_order.append("stop")
            mock_reset_world.side_effect = lambda: call_order.append("reset_world")
            mock_narrator.reset.side_effect = lambda: call_order.append("narrator_reset")
            mock_register.side_effect = lambda: call_order.append("register_agents")
            mock_host.start = AsyncMock(side_effect=lambda: call_order.append("start"))

            await reset_simulation()

        self.assertEqual(
            call_order,
            ["stop", "reset_world", "narrator_reset", "register_agents", "start"],
        )


class TestToggleNarration(unittest.TestCase):
    """POST /narration/toggle → flips narrator.enabled."""

    def test_toggle_from_disabled_to_enabled(self):
        from app.main import toggle_narration

        with patch("app.main.narrator") as mock_narrator:
            mock_narrator.enabled = False
            # After `narrator.enabled = not narrator.enabled`, enabled becomes True
            # But MagicMock doesn't actually negate — we need to simulate the property
            # The function reads narrator.enabled, negates, writes back, then reads again
            # With MagicMock, the assignment sticks, so the return value reflects the last set
            toggle_narration()
            # The function does: narrator.enabled = not narrator.enabled
            # MagicMock: `not False` → True, so it sets True
            # Then returns {"enabled": narrator.enabled} which is True
            self.assertTrue(mock_narrator.enabled)

    def test_toggle_from_enabled_to_disabled(self):
        from app.main import toggle_narration

        with patch("app.main.narrator") as mock_narrator:
            mock_narrator.enabled = True
            toggle_narration()
            # not True → False
            self.assertFalse(mock_narrator.enabled)

    def test_toggle_returns_new_state(self):
        from app.main import toggle_narration

        with patch("app.main.narrator") as mock_narrator:
            mock_narrator.enabled = False
            result = toggle_narration()
        self.assertEqual(result, {"enabled": True})


class TestNarrationStatus(unittest.TestCase):
    """GET /narration/status → returns current narration enabled state."""

    def test_status_enabled(self):
        from app.main import narration_status

        with patch("app.main.narrator") as mock_narrator:
            mock_narrator.enabled = True
            result = narration_status()
        self.assertEqual(result, {"enabled": True})

    def test_status_disabled(self):
        from app.main import narration_status

        with patch("app.main.narrator") as mock_narrator:
            mock_narrator.enabled = False
            result = narration_status()
        self.assertEqual(result, {"enabled": False})


class TestAbortMission(unittest.IsolatedAsyncioTestCase):
    """POST /mission/abort → delegates to host.abort_mission."""

    async def test_abort_returns_host_result(self):
        from app.main import abort_mission

        expected = {"ok": True, "status": "aborted", "reason": "test abort"}
        with patch("app.main.host") as mock_host:
            mock_host.abort_mission = AsyncMock(return_value=expected)
            result = await abort_mission("test abort")
        self.assertEqual(result, expected)

    async def test_abort_passes_reason_to_host(self):
        from app.main import abort_mission

        with patch("app.main.host") as mock_host:
            mock_host.abort_mission = AsyncMock(return_value={"ok": True})
            await abort_mission("Custom reason")
            mock_host.abort_mission.assert_awaited_once_with("Custom reason")

    async def test_abort_default_reason(self):
        from app.main import abort_mission

        with patch("app.main.host") as mock_host:
            mock_host.abort_mission = AsyncMock(return_value={"ok": True})
            await abort_mission()
            mock_host.abort_mission.assert_awaited_once_with("Manual abort from mission control")

    async def test_abort_already_ended_returns_error(self):
        from app.main import abort_mission

        expected = {"ok": False, "error": "Mission already ended"}
        with patch("app.main.host") as mock_host:
            mock_host.abort_mission = AsyncMock(return_value=expected)
            result = await abort_mission("too late")
        self.assertFalse(result["ok"])
        self.assertIn("already ended", result["error"])
