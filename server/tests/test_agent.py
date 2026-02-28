import unittest

from app.world import world
from app.agent import MistralRoverReasoner, ROVER_TOOLS, DRONE_TOOLS, _parse_structured_thinking


class TestRoverFallback(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["mission"] = {
            "objective": "Explore the terrain",
            "plan": [],
        }
        world.state["agents"]["rover-mistral"]["visited"] = [[10, 10]]

    def test_fallback_returns_dict(self):
        agent = MistralRoverReasoner()
        turn = agent._fallback_turn("test reason")
        self.assertIsInstance(turn, dict)
        self.assertIn("thinking", turn)
        self.assertIn("action", turn)

    def test_fallback_has_thinking(self):
        agent = MistralRoverReasoner()
        turn = agent._fallback_turn("test reason")
        self.assertIsInstance(turn["thinking"], str)
        self.assertIn("LLM fallback", turn["thinking"])

    def test_fallback_action_shape(self):
        agent = MistralRoverReasoner()
        turn = agent._fallback_turn("test reason")
        action = turn["action"]
        self.assertIsInstance(action, dict)
        self.assertEqual(action["name"], "move")
        self.assertIn("direction", action["params"])
        self.assertIn(action["params"]["direction"], ["north", "south", "east", "west"])

    def test_fallback_does_not_mutate_world(self):
        agent = MistralRoverReasoner()
        pos_before = list(world.state["agents"]["rover-mistral"]["position"])
        agent._fallback_turn("test reason")
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], pos_before)

    def test_fallback_prefers_unvisited(self):
        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        world.state["agents"]["rover-mistral"]["visited"] = [
            [10, 10],
            [11, 10],
            [10, 9],
            [9, 10],
        ]
        agent = MistralRoverReasoner()
        turn = agent._fallback_turn("test reason")
        self.assertEqual(turn["action"]["params"]["direction"], "north")


class TestToolLists(unittest.TestCase):
    def _tool_names(self, tools):
        return [t["function"]["name"] for t in tools]

    def test_notify_in_rover_tools(self):
        names = self._tool_names(ROVER_TOOLS)
        self.assertIn("notify", names)
        self.assertNotIn("notify_base", names)

    def test_notify_in_drone_tools(self):
        names = self._tool_names(DRONE_TOOLS)
        self.assertIn("notify", names)
        self.assertNotIn("notify_base", names)


class TestParseStructuredThinking(unittest.TestCase):
    def test_full_block(self):
        raw = (
            "SITUATION: Low battery at zone B3\n"
            "OPTIONS: return to base, dig here, move east\n"
            "DECISION: return to base to recharge\n"
            "RISK: medium"
        )
        result = _parse_structured_thinking(raw)
        self.assertEqual(result["situation"], "Low battery at zone B3")
        self.assertEqual(result["options"], ["return to base", "dig here", "move east"])
        self.assertEqual(result["decision"], "return to base to recharge")
        self.assertEqual(result["risk"], "medium")

    def test_missing_fields(self):
        raw = "Just some freeform LLM text with no structure."
        result = _parse_structured_thinking(raw)
        self.assertEqual(result["situation"], "")
        self.assertEqual(result["options"], [])
        self.assertEqual(result["decision"], "")
        self.assertEqual(result["risk"], "low")

    def test_empty_input(self):
        result = _parse_structured_thinking("")
        self.assertEqual(result["situation"], "")
        self.assertEqual(result["risk"], "low")

    def test_partial_block(self):
        raw = "SITUATION: Storm approaching\nDECISION: take shelter"
        result = _parse_structured_thinking(raw)
        self.assertEqual(result["situation"], "Storm approaching")
        self.assertEqual(result["decision"], "take shelter")
        self.assertEqual(result["options"], [])
        self.assertEqual(result["risk"], "low")

    def test_invalid_risk_defaults_to_low(self):
        raw = "RISK: catastrophic"
        result = _parse_structured_thinking(raw)
        self.assertEqual(result["risk"], "low")
