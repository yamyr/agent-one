import json
import unittest
from unittest.mock import MagicMock, patch

from app.station import StationAgent, _parse_tool_calls, _build_world_summary, execute_action
from app.models import AgentMission, StoneInfo, RoverSummary, StationContext


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


def _make_station_context():
    """Build a typed StationContext for testing."""
    return StationContext(
        grid_w=20,
        grid_h=20,
        rovers=[
            RoverSummary(
                id="rover-mock",
                position=[0, 0],
                battery=1.0,
                mission=AgentMission(objective="Explore the terrain", plan=[]),
                visited_count=1,
            ),
            RoverSummary(
                id="rover-mistral",
                position=[0, 0],
                battery=1.0,
                mission=AgentMission(objective="Explore the terrain", plan=[]),
                visited_count=1,
            ),
        ],
        stones=[
            StoneInfo(type="unknown", position=[5, 5]),
            StoneInfo(type="unknown", position=[10, 10]),
        ],
    )


class TestStationDefine(unittest.TestCase):
    @patch("app.station.settings")
    def test_define_mission_returns_result(self, mock_settings):
        mock_settings.mistral_api_key = "test-key"
        station = StationAgent()
        mock_client = MagicMock()
        station._client = mock_client

        tool_calls = [
            _mock_tool_call(
                "assign_mission", {"agent_id": "rover-mock", "objective": "Explore north sector"}
            ),
        ]
        mock_client.chat.complete.return_value = _mock_client_response(
            content="Assigning initial missions.",
            tool_calls=tool_calls,
        )

        ctx = _make_station_context()
        result = station.define_mission(ctx)

        self.assertEqual(result["thinking"], "Assigning initial missions.")
        self.assertEqual(len(result["actions"]), 1)
        self.assertEqual(result["actions"][0]["name"], "assign_mission")
        self.assertEqual(result["actions"][0]["params"]["agent_id"], "rover-mock")
        self.assertEqual(result["actions"][0]["params"]["objective"], "Explore north sector")

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

        ctx = _make_station_context()
        result = station.define_mission(ctx)

        self.assertIsNone(result["thinking"])
        self.assertEqual(len(result["actions"]), 1)
        self.assertEqual(result["actions"][0]["name"], "broadcast_alert")
        self.assertEqual(result["actions"][0]["params"]["message"], "Mission start")


class TestStationHandleEvent(unittest.TestCase):
    @patch("app.station.settings")
    def test_handle_event_returns_result(self, mock_settings):
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
            "source": "rover-mock",
            "type": "event",
            "name": "check",
            "payload": {"stone": {"type": "basalt"}},
        }
        ctx = _make_station_context()
        result = station.handle_event(event, ctx)

        self.assertEqual(result["thinking"], "Stone found, reassigning rover.")
        self.assertEqual(len(result["actions"]), 1)
        self.assertEqual(result["actions"][0]["name"], "assign_mission")
        self.assertEqual(result["actions"][0]["params"]["objective"], "Collect the basalt stone")


class TestParseToolCalls(unittest.TestCase):
    def test_assign_mission_parsed(self):
        tool_calls = [
            _mock_tool_call("assign_mission", {"agent_id": "rover-mock", "objective": "Go north"})
        ]
        actions = _parse_tool_calls(tool_calls)

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["name"], "assign_mission")
        self.assertEqual(actions[0]["params"]["agent_id"], "rover-mock")

    def test_broadcast_alert_parsed(self):
        tool_calls = [_mock_tool_call("broadcast_alert", {"message": "Storm incoming"})]
        actions = _parse_tool_calls(tool_calls)

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["name"], "broadcast_alert")
        self.assertEqual(actions[0]["params"]["message"], "Storm incoming")

    def test_charge_rover_parsed(self):
        tool_calls = [_mock_tool_call("charge_rover", {"rover_id": "rover-mock"})]
        actions = _parse_tool_calls(tool_calls)

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["name"], "charge_rover")
        self.assertEqual(actions[0]["params"]["rover_id"], "rover-mock")

    def test_multiple_tool_calls_parsed(self):
        tool_calls = [
            _mock_tool_call("assign_mission", {"agent_id": "rover-mock", "objective": "Go"}),
            _mock_tool_call("broadcast_alert", {"message": "Alert"}),
        ]
        actions = _parse_tool_calls(tool_calls)
        self.assertEqual(len(actions), 2)


class TestExecuteAction(unittest.TestCase):
    def test_assign_mission(self):
        result = execute_action({
            "name": "assign_mission",
            "params": {"agent_id": "rover-mock", "objective": "Go north"},
        })
        self.assertTrue(result["ok"])
        self.assertEqual(result["agent_id"], "rover-mock")

    def test_broadcast_alert(self):
        result = execute_action({
            "name": "broadcast_alert",
            "params": {"message": "Storm incoming!"},
        })
        self.assertTrue(result["ok"])
        self.assertEqual(result["message"], "Storm incoming!")

    def test_charge_rover_at_station(self):
        from app.world import WORLD
        WORLD["agents"]["rover-mock"]["position"] = [0, 0]
        WORLD["agents"]["rover-mock"]["battery"] = 0.5
        result = execute_action({
            "name": "charge_rover",
            "params": {"rover_id": "rover-mock"},
        })
        self.assertTrue(result["ok"])

    def test_unknown_action(self):
        result = execute_action({
            "name": "self_destruct",
            "params": {},
        })
        self.assertFalse(result["ok"])
        self.assertIn("Unknown station action", result["error"])


class TestBuildWorldSummary(unittest.TestCase):
    def test_summary_contains_rovers(self):
        ctx = _make_station_context()
        summary = _build_world_summary(ctx)
        self.assertIn("rover-mock", summary)
        self.assertIn("rover-mistral", summary)

    def test_summary_contains_grid(self):
        ctx = _make_station_context()
        summary = _build_world_summary(ctx)
        self.assertIn("Grid: 20x20", summary)

    def test_summary_contains_veins(self):
        ctx = _make_station_context()
        summary = _build_world_summary(ctx)
        self.assertIn("Veins on map: 2", summary)
