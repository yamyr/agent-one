import unittest

from app.world import WORLD, move_agent, get_snapshot


class TestMoveAgent(unittest.TestCase):
    def setUp(self):
        # Reset rover position before each test
        WORLD["agents"]["rover-mock"]["position"] = "Z01"
        WORLD["agents"]["rover-mock"]["battery"] = 1.0

    def test_move_success(self):
        result = move_agent("rover-mock", "Z03")
        self.assertTrue(result["ok"])
        self.assertEqual(result["from"], "Z01")
        self.assertEqual(result["to"], "Z03")
        self.assertEqual(WORLD["agents"]["rover-mock"]["position"], "Z03")

    def test_move_unknown_zone(self):
        result = move_agent("rover-mock", "Z99")
        self.assertFalse(result["ok"])
        self.assertIn("Unknown zone", result["error"])
        # Position unchanged
        self.assertEqual(WORLD["agents"]["rover-mock"]["position"], "Z01")

    def test_move_already_there(self):
        result = move_agent("rover-mock", "Z01")
        self.assertFalse(result["ok"])
        self.assertIn("Already at", result["error"])

    def test_move_unknown_agent(self):
        result = move_agent("rover-99", "Z02")
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_move_sequential(self):
        move_agent("rover-mock", "Z02")
        result = move_agent("rover-mock", "Z05")
        self.assertTrue(result["ok"])
        self.assertEqual(result["from"], "Z02")
        self.assertEqual(result["to"], "Z05")

    def test_get_snapshot_is_copy(self):
        snap = get_snapshot()
        snap["agents"]["rover-mock"]["position"] = "Z99"
        # Original unchanged
        self.assertEqual(WORLD["agents"]["rover-mock"]["position"], "Z01")
