import unittest

from app.world import WORLD
from app.agent import MockRoverReasoner


class TestMockRoverAgent(unittest.TestCase):
    def setUp(self):
        WORLD["agents"]["rover-mock"]["position"] = [10, 10]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        WORLD["agents"]["rover-mock"]["mission"] = {"objective": "Explore the terrain", "plan": []}
        WORLD["agents"]["rover-mock"]["visited"] = [[10, 10]]

    def test_run_turn_returns_dict(self):
        agent = MockRoverReasoner()
        turn = agent.run_turn()
        self.assertIsInstance(turn, dict)
        self.assertIn("thinking", turn)
        self.assertIn("action", turn)

    def test_run_turn_has_thinking(self):
        agent = MockRoverReasoner()
        turn = agent.run_turn()
        self.assertIsInstance(turn["thinking"], str)
        self.assertTrue(len(turn["thinking"]) > 0)

    def test_run_turn_action_shape(self):
        agent = MockRoverReasoner()
        turn = agent.run_turn()
        action = turn["action"]
        self.assertIsInstance(action, dict)
        self.assertEqual(action["name"], "move")
        self.assertIn("direction", action["params"])
        self.assertIn(action["params"]["direction"], ["north", "south", "east", "west"])

    def test_run_turn_does_not_mutate_world(self):
        agent = MockRoverReasoner()
        pos_before = list(WORLD["agents"]["rover-mock"]["position"])
        agent.run_turn()
        self.assertEqual(WORLD["agents"]["rover-mock"]["position"], pos_before)

    def test_run_turn_at_corner(self):
        """With infinite grid, all 4 directions are valid from any position."""
        WORLD["agents"]["rover-mock"]["position"] = [0, 0]
        agent = MockRoverReasoner()
        turn = agent.run_turn()
        self.assertIn(turn["action"]["params"]["direction"], ["north", "south", "east", "west"])

    def test_run_turn_at_bottom_right(self):
        """With infinite grid, all 4 directions are valid from any position."""
        WORLD["agents"]["rover-mock"]["position"] = [19, 19]
        WORLD["agents"]["rover-mock"]["visited"] = [[19, 19]]
        agent = MockRoverReasoner()
        turn = agent.run_turn()
        self.assertIn(turn["action"]["params"]["direction"], ["north", "south", "east", "west"])

    def test_mock_prefers_unvisited(self):
        WORLD["agents"]["rover-mock"]["position"] = [10, 10]
        WORLD["agents"]["rover-mock"]["visited"] = [
            [10, 10],
            [11, 10],
            [10, 9],
            [9, 10],
        ]
        agent = MockRoverReasoner()
        turn = agent.run_turn()
        self.assertEqual(turn["action"]["params"]["direction"], "north")

    def test_mock_recall_heads_to_station(self):
        WORLD["agents"]["rover-mock"]["position"] = [5, 5]
        WORLD["agents"]["rover-mock"]["pending_commands"] = [
            {"name": "recall", "payload": {"reason": "Emergency"}},
        ]
        agent = MockRoverReasoner()
        turn = agent.run_turn()
        self.assertEqual(turn["action"]["name"], "move")
        # Should head toward station at (0,0) — west or south
        self.assertIn(turn["action"]["params"]["direction"], ["west", "south"])
        self.assertIn("RECALL", turn["thinking"])
        # Clean up
        WORLD["agents"]["rover-mock"].pop("pending_commands", None)

    def test_mock_recall_at_station(self):
        """If already at station when recall received, still returns valid action."""
        WORLD["agents"]["rover-mock"]["position"] = [0, 0]
        WORLD["agents"]["rover-mock"]["pending_commands"] = [
            {"name": "recall", "payload": {"reason": "Test"}},
        ]
        agent = MockRoverReasoner()
        turn = agent.run_turn()
        self.assertIn("already at station", turn["thinking"])
        WORLD["agents"]["rover-mock"].pop("pending_commands", None)
