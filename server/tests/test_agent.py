import unittest

from app.world import WORLD
from app.agent import MistralRoverReasoner


class TestRoverFallback(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["rover-mistral"]["position"] = [10, 10]
        WORLD["agents"]["rover-mistral"]["battery"] = 1.0
        WORLD["agents"]["rover-mistral"]["mission"] = {"objective": "Explore the terrain", "plan": []}
        WORLD["agents"]["rover-mistral"]["visited"] = [[10, 10]]

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
        pos_before = list(WORLD["agents"]["rover-mistral"]["position"])
        agent._fallback_turn("test reason")
        self.assertEqual(WORLD["agents"]["rover-mistral"]["position"], pos_before)

    def test_fallback_prefers_unvisited(self):
        WORLD["agents"]["rover-mistral"]["position"] = [10, 10]
        WORLD["agents"]["rover-mistral"]["visited"] = [
            [10, 10],
            [11, 10],
            [10, 9],
            [9, 10],
        ]
        agent = MistralRoverReasoner()
        turn = agent._fallback_turn("test reason")
        self.assertEqual(turn["action"]["params"]["direction"], "north")
