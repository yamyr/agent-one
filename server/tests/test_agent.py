import unittest

from app.world import world, execute_action
from app.agent import MistralRoverReasoner, ROVER_TOOLS, DRONE_TOOLS
from app.agent import parse_task_separator


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


class TestTaskSeparatorParsing(unittest.TestCase):
    def test_no_separator(self):
        thinking, task = parse_task_separator("I should move north.")
        self.assertEqual(thinking, "I should move north.")
        self.assertIsNone(task)

    def test_with_separator(self):
        text = "I need to head north toward the vein.\n---TASK---\nNavigate to basalt vein at (3,5)"
        thinking, task = parse_task_separator(text)
        self.assertEqual(thinking, "I need to head north toward the vein.")
        self.assertEqual(task, "Navigate to basalt vein at (3,5)")

    def test_none_input(self):
        thinking, task = parse_task_separator(None)
        self.assertIsNone(thinking)
        self.assertIsNone(task)

    def test_empty_input(self):
        thinking, task = parse_task_separator("")
        self.assertIsNone(thinking)
        self.assertIsNone(task)

    def test_separator_only(self):
        thinking, task = parse_task_separator("---TASK---")
        self.assertIsNone(thinking)
        self.assertIsNone(task)

    def test_separator_with_only_task(self):
        thinking, task = parse_task_separator("---TASK---\nExplore north quadrant")
        self.assertIsNone(thinking)
        self.assertEqual(task, "Explore north quadrant")

    def test_separator_with_only_thinking(self):
        thinking, task = parse_task_separator("Moving east now.\n---TASK---\n")
        self.assertEqual(thinking, "Moving east now.")
        self.assertIsNone(task)

    def test_fallback_includes_task_key(self):
        agent = MistralRoverReasoner()
        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["mission"] = {"objective": "Explore", "plan": []}
        world.state["agents"]["rover-mistral"]["visited"] = [[10, 10]]
        turn = agent._fallback_turn("test")
        self.assertNotIn("task", turn)


class TestRoverContextDroneHotspot(unittest.TestCase):
    def setUp(self):
        self._orig_scans = world.state.get("drone_scans", [])
        world.state["agents"]["rover-mistral"]["position"] = [0, 0]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["mission"] = {"objective": "Explore", "plan": []}
        world.state["agents"]["rover-mistral"]["visited"] = [[0, 0]]

    def tearDown(self):
        world.state["drone_scans"] = self._orig_scans

    def test_hotspot_appears_in_context(self):
        world.state["drone_scans"] = [
            {"position": [10, 10], "readings": {"10,10": 0.7, "11,10": 0.3}},
        ]
        agent = MistralRoverReasoner()
        context = agent._build_context()
        self.assertIn("Drone Scan Hotspots", context)
        self.assertIn("(10,10)", context)
        self.assertIn("0.700", context)

    def test_no_hotspot_section_when_empty(self):
        world.state["drone_scans"] = []
        agent = MistralRoverReasoner()
        context = agent._build_context()
        self.assertNotIn("Drone Scan Hotspots", context)


class TestExecuteActionNoTaskUpdate(unittest.TestCase):
    def setUp(self):
        self._orig_pos = world.state["agents"]["rover-mistral"]["position"][:]
        self._orig_bat = world.state["agents"]["rover-mistral"]["battery"]
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0

    def tearDown(self):
        world.state["agents"]["rover-mistral"]["position"] = self._orig_pos
        world.state["agents"]["rover-mistral"]["battery"] = self._orig_bat

    def test_move_result_has_no_task_update(self):
        result = execute_action("rover-mistral", "move", {"direction": "north"})
        self.assertTrue(result["ok"])
        self.assertNotIn("task_update", result)
