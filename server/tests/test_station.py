import json
import unittest
from unittest.mock import MagicMock, patch

from app.station import StationAgent, _execute_tool_calls, _build_world_summary
from app.world import WORLD


def _mock_tool_call(name, arguments):
    """Create a mock tool call object matching Mistral response format."""
    tc = MagicMock()
    tc.function.name = name
    tc.function.arguments = json.dumps(arguments)
    return tc


def _mock_client_response(content=None, tool_calls=None):
    """Create a mock Mistral chat.complete response."""
    choice = MagicMock()
    choice.message.content = content
    choice.message.tool_calls = tool_calls
    response = MagicMock()
    response.choices = [choice]
    return response


class TestStationDefine(unittest.TestCase):
    @patch("app.station.settings")
    def test_define_mission_returns_events(self, mock_settings):
        mock_settings.mistral_api_key = "test-key"
        station = StationAgent()
        mock_client = MagicMock()
        station._client = mock_client

        tool_calls = [
            _mock_tool_call(
                "assign_mission", {"agent_id": "randy-rover", "objective": "Explore north sector"}
            ),
        ]
        mock_client.chat.complete.return_value = _mock_client_response(
            content="Assigning initial missions.",
            tool_calls=tool_calls,
        )

        events = station.define_mission()

        self.assertEqual(len(events), 2)  # thinking + assign_mission
        self.assertEqual(events[0]["name"], "thinking")
        self.assertEqual(events[0]["source"], "station")
        self.assertEqual(events[1]["name"], "assign_mission")
        self.assertEqual(events[1]["payload"]["agent_id"], "randy-rover")
        self.assertEqual(events[1]["payload"]["objective"], "Explore north sector")

    @patch("app.station.settings")
    def test_define_mission_no_thinking(self, mock_settings):
        mock_settings.mistral_api_key = "test-key"
        station = StationAgent()
        mock_client = MagicMock()
        station._client = mock_client

        tool_calls = [
            _mock_tool_call("broadcast_alert", {"message": "Mission start"}),
        ]
        mock_client.chat.complete.return_value = _mock_client_response(
            content=None,
            tool_calls=tool_calls,
        )

        events = station.define_mission()

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["name"], "alert")
        self.assertEqual(events[0]["payload"]["message"], "Mission start")


class TestStationHandleEvent(unittest.TestCase):
    @patch("app.station.settings")
    def test_handle_event_returns_events(self, mock_settings):
        mock_settings.mistral_api_key = "test-key"
        station = StationAgent()
        mock_client = MagicMock()
        station._client = mock_client

        tool_calls = [
            _mock_tool_call(
                "assign_mission",
                {"agent_id": "rover-mistral", "objective": "Collect the basalt stone"},
            ),
        ]
        mock_client.chat.complete.return_value = _mock_client_response(
            content="Stone found, reassigning rover.",
            tool_calls=tool_calls,
        )

        event = {
            "source": "randy-rover",
            "type": "event",
            "name": "check",
            "payload": {"stone": {"type": "basalt"}},
        }
        events = station.handle_event(event)

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["name"], "thinking")
        self.assertEqual(events[1]["name"], "assign_mission")
        self.assertEqual(events[1]["payload"]["objective"], "Collect the basalt stone")


class TestExecuteToolCalls(unittest.TestCase):
    def setUp(self):
        self._orig_mission = WORLD["agents"]["randy-rover"]["mission"].copy()

    def tearDown(self):
        WORLD["agents"]["randy-rover"]["mission"] = self._orig_mission

    def test_assign_mission_tool_call(self):
        tool_calls = [
            _mock_tool_call("assign_mission", {"agent_id": "randy-rover", "objective": "Go north"})
        ]
        events = _execute_tool_calls(tool_calls)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["name"], "assign_mission")
        self.assertTrue(events[0]["payload"]["ok"])
        self.assertEqual(WORLD["agents"]["randy-rover"]["mission"]["objective"], "Go north")

    def test_broadcast_alert_tool_call(self):
        tool_calls = [_mock_tool_call("broadcast_alert", {"message": "Storm incoming"})]
        events = _execute_tool_calls(tool_calls)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["name"], "alert")
        self.assertEqual(events[0]["payload"]["message"], "Storm incoming")


class TestBuildWorldSummary(unittest.TestCase):
    def test_summary_contains_rovers(self):
        summary = _build_world_summary()
        self.assertIn("randy-rover", summary)
        self.assertIn("rover-mistral", summary)

    def test_summary_excludes_station(self):
        summary = _build_world_summary()
        # Station should not list itself as an agent to manage
        self.assertNotIn("station:", summary)

    def test_summary_contains_grid(self):
        summary = _build_world_summary()
        self.assertIn("Grid: 20x20", summary)
