import unittest

from app.world import world, execute_action
from app.agent import MistralRoverReasoner, ROVER_TOOLS, DRONE_TOOLS
from app.agent import parse_task_separator, _parse_structured_thinking


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

    def test_ice_and_upgrade_tools_in_rover_tools(self):
        names = self._tool_names(ROVER_TOOLS)
        self.assertIn("gather_ice", names)
        self.assertIn("upgrade_base", names)


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
        self._orig_upgrades = world.state.get("station_upgrades", {}).copy()
        self._orig_stones = list(world.state.get("stones", []))
        world.state["agents"]["rover-mistral"]["position"] = [0, 0]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["mission"] = {"objective": "Explore", "plan": []}
        world.state["agents"]["rover-mistral"]["visited"] = [[0, 0]]

    def tearDown(self):
        world.state["drone_scans"] = self._orig_scans
        world.state["station_upgrades"] = self._orig_upgrades
        world.state["stones"] = self._orig_stones

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

    def test_context_shows_ice_and_station_upgrade_status(self):
        world.state["stones"] = [
            {
                "position": [0, 0],
                "type": "ice",
                "_true_type": "ice",
                "grade": "n/a",
                "quantity": 1,
                "analyzed": True,
            }
        ]
        world.state["station_upgrades"] = {"charge_mk2": 1, "extended_fuel": 1}
        world.state["agents"]["rover-mistral"]["position"] = [0, 0]

        agent = MistralRoverReasoner()
        context = agent._build_context()

        self.assertIn("ice deposit", context)
        self.assertIn("charge_mk2: level 1/1", context)


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


class TestRoverContextNoBoundaryClipping(unittest.TestCase):
    """Verify _build_context doesn't clip unvisited dirs at legacy GRID_W/GRID_H."""

    def setUp(self):
        self._orig_pos = world.state["agents"]["rover-mistral"]["position"][:]
        self._orig_battery = world.state["agents"]["rover-mistral"]["battery"]
        self._orig_mission = world.state["agents"]["rover-mistral"]["mission"].copy()
        self._orig_visited = world.state["agents"]["rover-mistral"].get("visited", [])[:]

    def tearDown(self):
        world.state["agents"]["rover-mistral"]["position"] = self._orig_pos
        world.state["agents"]["rover-mistral"]["battery"] = self._orig_battery
        world.state["agents"]["rover-mistral"]["mission"] = self._orig_mission
        world.state["agents"]["rover-mistral"]["visited"] = self._orig_visited

    def test_unvisited_dirs_beyond_old_grid_boundary(self):
        """At x=25, y=25 (beyond old 20x20 grid), all 4 dirs should be unvisited."""
        world.state["agents"]["rover-mistral"]["position"] = [25, 25]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["mission"] = {"objective": "Explore", "plan": []}
        world.state["agents"]["rover-mistral"]["visited"] = [[25, 25]]
        agent = MistralRoverReasoner()
        context = agent._build_context()
        # All 4 directions should appear as unvisited
        self.assertIn("north", context)
        self.assertIn("south", context)
        self.assertIn("east", context)
        self.assertIn("west", context)

    def test_unvisited_dirs_at_negative_coords(self):
        """At x=-5, y=-5, all 4 dirs should still be listed as unvisited."""
        world.state["agents"]["rover-mistral"]["position"] = [-5, -5]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["mission"] = {"objective": "Explore", "plan": []}
        world.state["agents"]["rover-mistral"]["visited"] = [[-5, -5]]
        agent = MistralRoverReasoner()
        context = agent._build_context()
        self.assertIn("north", context)
        self.assertIn("south", context)
        self.assertIn("east", context)
        self.assertIn("west", context)

    def test_context_says_infinite_terrain(self):
        """Context should mention 'infinite terrain', not 'Grid: 20x20'."""
        world.state["agents"]["rover-mistral"]["position"] = [0, 0]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["mission"] = {"objective": "Explore", "plan": []}
        world.state["agents"]["rover-mistral"]["visited"] = [[0, 0]]
        agent = MistralRoverReasoner()
        context = agent._build_context()
        self.assertIn("chunk-based", context)
        self.assertNotIn("Grid: 20x20", context)


class TestParseStructuredThinking(unittest.TestCase):
    """Tests for _parse_structured_thinking helper."""

    def test_parses_all_fields(self):
        text = "SITUATION: Low battery near vein\nOPTIONS: dig, return\nDECISION: return to station\nRISK: high"
        result = _parse_structured_thinking(text)
        self.assertEqual(result["situation"], "Low battery near vein")
        self.assertEqual(result["options"], ["dig", "return"])
        self.assertEqual(result["decision"], "return to station")
        self.assertEqual(result["risk"], "high")

    def test_returns_default_for_plain_text(self):
        result = _parse_structured_thinking("Just thinking about stuff")
        self.assertEqual(result["situation"], "")
        self.assertEqual(result["options"], [])
        self.assertEqual(result["risk"], "low")

    def test_partial_tags_still_parsed(self):
        text = "SITUATION: Exploring north\nDECISION: move north"
        result = _parse_structured_thinking(text)
        self.assertEqual(result["situation"], "Exploring north")
        self.assertEqual(result["decision"], "move north")

    def test_risk_normalized_to_lowercase(self):
        text = "SITUATION: Storm approaching\nRISK: high"
        result = _parse_structured_thinking(text)
        self.assertEqual(result["risk"], "high")

    def test_empty_string_returns_default(self):
        result = _parse_structured_thinking("")
        self.assertEqual(result["situation"], "")
        self.assertEqual(result["risk"], "low")

    def test_invalid_risk_defaults_with_warning(self):
        text = "SITUATION: Unknown state\nRISK: extreme"
        with self.assertLogs("app.agent", level="DEBUG") as cm:
            result = _parse_structured_thinking(text)
        self.assertEqual(result["risk"], "low")
        self.assertTrue(any("Unrecognized risk level" in msg for msg in cm.output))
