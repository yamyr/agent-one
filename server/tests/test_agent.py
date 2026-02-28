import json
import unittest
from unittest.mock import MagicMock, patch

from app.world import WORLD
from app.agent import MockRoverAgent


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


class TestMockRoverAgent(unittest.TestCase):
    def setUp(self):
        self._orig_pos = list(WORLD["agents"]["rover-mock"]["position"])
        self._orig_battery = WORLD["agents"]["rover-mock"]["battery"]
        self._orig_mission = WORLD["agents"]["rover-mock"]["mission"].copy()
        self._orig_visited = list(WORLD["agents"]["rover-mock"]["visited"])

        WORLD["agents"]["rover-mock"]["position"] = [10, 10]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        WORLD["agents"]["rover-mock"]["mission"] = {
            "objective": "Explore the terrain",
            "plan": [],
        }
        WORLD["agents"]["rover-mock"]["visited"] = [[10, 10]]

    def tearDown(self):
        WORLD["agents"]["rover-mock"]["position"] = self._orig_pos
        WORLD["agents"]["rover-mock"]["battery"] = self._orig_battery
        WORLD["agents"]["rover-mock"]["mission"] = self._orig_mission
        WORLD["agents"]["rover-mock"]["visited"] = self._orig_visited

    @patch("app.agent.settings")
    def test_run_turn_returns_dict(self, mock_settings):
        mock_settings.mistral_api_key = "test-key"
        agent = MockRoverAgent()
        mock_client = MagicMock()
        agent._client = mock_client

        tool_calls = [_mock_tool_call("move", {"direction": "north"})]
        mock_client.chat.complete.return_value = _mock_client_response(
            content="Moving north to explore.", tool_calls=tool_calls
        )

        turn = agent.run_turn()
        self.assertIsInstance(turn, dict)
        self.assertIn("thinking", turn)
        self.assertIn("action", turn)

    @patch("app.agent.settings")
    def test_run_turn_has_thinking(self, mock_settings):
        mock_settings.mistral_api_key = "test-key"
        agent = MockRoverAgent()
        mock_client = MagicMock()
        agent._client = mock_client

        tool_calls = [_mock_tool_call("move", {"direction": "east"})]
        mock_client.chat.complete.return_value = _mock_client_response(
            content="Heading east for coverage.", tool_calls=tool_calls
        )

        turn = agent.run_turn()
        self.assertIsInstance(turn["thinking"], str)
        self.assertTrue(len(turn["thinking"]) > 0)

    @patch("app.agent.settings")
    def test_run_turn_action_shape(self, mock_settings):
        mock_settings.mistral_api_key = "test-key"
        agent = MockRoverAgent()
        mock_client = MagicMock()
        agent._client = mock_client

        tool_calls = [_mock_tool_call("move", {"direction": "south"})]
        mock_client.chat.complete.return_value = _mock_client_response(
            content="Going south.", tool_calls=tool_calls
        )

        turn = agent.run_turn()
        action = turn["action"]
        self.assertIsInstance(action, dict)
        self.assertEqual(action["name"], "move")
        self.assertIn("direction", action["params"])
        self.assertIn(action["params"]["direction"], ["north", "south", "east", "west"])

    @patch("app.agent.settings")
    def test_run_turn_does_not_mutate_world(self, mock_settings):
        mock_settings.mistral_api_key = "test-key"
        agent = MockRoverAgent()
        mock_client = MagicMock()
        agent._client = mock_client

        tool_calls = [_mock_tool_call("move", {"direction": "west"})]
        mock_client.chat.complete.return_value = _mock_client_response(
            content="Moving west.", tool_calls=tool_calls
        )

        pos_before = list(WORLD["agents"]["rover-mock"]["position"])
        agent.run_turn()
        self.assertEqual(WORLD["agents"]["rover-mock"]["position"], pos_before)

    @patch("app.agent.settings")
    def test_run_turn_dig_action(self, mock_settings):
        """Verify dig tool calls are parsed correctly."""
        mock_settings.mistral_api_key = "test-key"
        agent = MockRoverAgent()
        mock_client = MagicMock()
        agent._client = mock_client

        tool_calls = [_mock_tool_call("dig", {})]
        mock_client.chat.complete.return_value = _mock_client_response(
            content="Stone detected, digging.", tool_calls=tool_calls
        )

        turn = agent.run_turn()
        self.assertEqual(turn["action"]["name"], "dig")

    @patch("app.agent.settings")
    def test_run_turn_pickup_action(self, mock_settings):
        """Verify pickup tool calls are parsed correctly."""
        mock_settings.mistral_api_key = "test-key"
        agent = MockRoverAgent()
        mock_client = MagicMock()
        agent._client = mock_client

        tool_calls = [_mock_tool_call("pickup", {})]
        mock_client.chat.complete.return_value = _mock_client_response(
            content="Picking up the stone.", tool_calls=tool_calls
        )

        turn = agent.run_turn()
        self.assertEqual(turn["action"]["name"], "pickup")

    @patch("app.agent.settings")
    def test_run_turn_no_tool_calls(self, mock_settings):
        """When LLM returns no tool calls, action should be None."""
        mock_settings.mistral_api_key = "test-key"
        agent = MockRoverAgent()
        mock_client = MagicMock()
        agent._client = mock_client

        mock_client.chat.complete.return_value = _mock_client_response(
            content="I'm thinking about what to do.", tool_calls=None
        )

        turn = agent.run_turn()
        self.assertEqual(turn["thinking"], "I'm thinking about what to do.")
        self.assertIsNone(turn["action"])

    @patch("app.agent.settings")
    def test_run_turn_no_thinking(self, mock_settings):
        """When LLM returns no content, thinking should be None."""
        mock_settings.mistral_api_key = "test-key"
        agent = MockRoverAgent()
        mock_client = MagicMock()
        agent._client = mock_client

        tool_calls = [_mock_tool_call("move", {"direction": "north"})]
        mock_client.chat.complete.return_value = _mock_client_response(
            content=None, tool_calls=tool_calls
        )

        turn = agent.run_turn()
        self.assertIsNone(turn["thinking"])
        self.assertEqual(turn["action"]["name"], "move")

    @patch("app.agent.settings")
    def test_run_turn_unknown_tool_ignored(self, mock_settings):
        """Unknown tool calls should not produce an action."""
        mock_settings.mistral_api_key = "test-key"
        agent = MockRoverAgent()
        mock_client = MagicMock()
        agent._client = mock_client

        tool_calls = [_mock_tool_call("fly", {"altitude": 100})]
        mock_client.chat.complete.return_value = _mock_client_response(
            content="Flying!", tool_calls=tool_calls
        )

        turn = agent.run_turn()
        self.assertIsNone(turn["action"])

    @patch("app.agent.settings")
    def test_build_context_includes_personality(self, mock_settings):
        """Context should include the randomly chosen personality prompt."""
        mock_settings.mistral_api_key = "test-key"
        agent = MockRoverAgent()
        context = agent._build_context()
        # Personality is the first line of context
        self.assertTrue(any(prompt in context for prompt in MockRoverAgent.MISSION_PROMPTS))

    @patch("app.agent.settings")
    def test_build_context_includes_position(self, mock_settings):
        """Context should include the agent's current position."""
        mock_settings.mistral_api_key = "test-key"
        agent = MockRoverAgent()
        context = agent._build_context()
        self.assertIn("Position: (10, 10)", context)

    @patch("app.agent.settings")
    def test_build_context_includes_battery(self, mock_settings):
        """Context should include battery level."""
        mock_settings.mistral_api_key = "test-key"
        agent = MockRoverAgent()
        context = agent._build_context()
        self.assertIn("Battery: 100%", context)

    @patch("app.agent.settings")
    def test_build_context_includes_mission(self, mock_settings):
        """Context should include mission objective."""
        mock_settings.mistral_api_key = "test-key"
        agent = MockRoverAgent()
        context = agent._build_context()
        self.assertIn("Explore the terrain", context)

    @patch("app.agent.settings")
    def test_personality_is_random(self, mock_settings):
        """Different instantiations should potentially get different prompts."""
        mock_settings.mistral_api_key = "test-key"
        personalities = set()
        for _ in range(50):
            agent = MockRoverAgent()
            personalities.add(agent._mission_prompt)
        # With 8 prompts and 50 tries, we should see at least 2 different ones
        self.assertGreater(len(personalities), 1)

    @patch("app.agent.settings")
    def test_stores_context_in_world(self, mock_settings):
        """run_turn should store the LLM context in WORLD for UI display."""
        mock_settings.mistral_api_key = "test-key"
        agent = MockRoverAgent()
        mock_client = MagicMock()
        agent._client = mock_client

        tool_calls = [_mock_tool_call("move", {"direction": "north"})]
        mock_client.chat.complete.return_value = _mock_client_response(
            content="Moving.", tool_calls=tool_calls
        )

        agent.run_turn()
        self.assertIn("last_context", WORLD["agents"]["rover-mock"])
        self.assertIsInstance(WORLD["agents"]["rover-mock"]["last_context"], str)
