import unittest

from app.world import WORLD, move_agent, execute_action, get_snapshot, check_ground
from app.world import BATTERY_COST_MOVE, GRID_W, GRID_H, AGENT_STARTS


class TestMoveAgent(unittest.TestCase):

    def setUp(self):
        WORLD["agents"]["rover-mock"]["position"] = [2, 10]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        WORLD["agents"]["rover-mock"]["mission"] = {"objective": "Explore the terrain", "plan": []}
        WORLD["agents"]["rover-mock"]["visited"] = [[2, 10]]

    def test_move_success(self):
        result = move_agent("rover-mock", 3, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["from"], [2, 10])
        self.assertEqual(result["to"], [3, 10])
        self.assertEqual(WORLD["agents"]["rover-mock"]["position"], [3, 10])

    def test_move_out_of_bounds_negative(self):
        WORLD["agents"]["rover-mock"]["position"] = [0, 10]
        result = move_agent("rover-mock", -1, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Out of bounds", result["error"])

    def test_move_out_of_bounds_over(self):
        WORLD["agents"]["rover-mock"]["position"] = [19, 10]
        result = move_agent("rover-mock", 20, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Out of bounds", result["error"])

    def test_move_not_adjacent(self):
        result = move_agent("rover-mock", 5, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Not adjacent", result["error"])
        self.assertEqual(WORLD["agents"]["rover-mock"]["position"], [2, 10])

    def test_move_diagonal_rejected(self):
        result = move_agent("rover-mock", 3, 11)
        self.assertFalse(result["ok"])
        self.assertIn("Not adjacent", result["error"])

    def test_move_already_there(self):
        result = move_agent("rover-mock", 2, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Already at", result["error"])

    def test_move_unknown_agent(self):
        result = move_agent("rover-99", 3, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_move_sequential(self):
        move_agent("rover-mock", 3, 10)
        result = move_agent("rover-mock", 4, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["from"], [3, 10])
        self.assertEqual(result["to"], [4, 10])

    def test_move_all_four_directions(self):
        WORLD["agents"]["rover-mock"]["position"] = [10, 10]
        for tx, ty in [(11, 10), (10, 10), (10, 11), (10, 10)]:
            result = move_agent("rover-mock", tx, ty)
            self.assertTrue(result["ok"])

    def test_get_snapshot_is_copy(self):
        snap = get_snapshot()
        snap["agents"]["rover-mock"]["position"] = [99, 99]
        self.assertEqual(WORLD["agents"]["rover-mock"]["position"], [2, 10])

    def test_snapshot_has_grid(self):
        snap = get_snapshot()
        self.assertEqual(snap["grid"]["w"], 20)
        self.assertEqual(snap["grid"]["h"], 20)


class TestExecuteAction(unittest.TestCase):

    def setUp(self):
        WORLD["agents"]["rover-mock"]["position"] = [2, 10]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        WORLD["agents"]["rover-mock"]["mission"] = {"objective": "Explore the terrain", "plan": []}
        WORLD["agents"]["rover-mock"]["visited"] = [[2, 10]]

    def test_execute_move_east(self):
        result = execute_action("rover-mock", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["from"], [2, 10])
        self.assertEqual(result["to"], [3, 10])
        self.assertEqual(WORLD["agents"]["rover-mock"]["position"], [3, 10])

    def test_execute_move_drains_battery(self):
        result = execute_action("rover-mock", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(WORLD["agents"]["rover-mock"]["battery"], 1.0 - BATTERY_COST_MOVE)

    def test_execute_move_failed_no_drain(self):
        WORLD["agents"]["rover-mock"]["position"] = [0, 10]
        result = execute_action("rover-mock", "move", {"direction": "west"})
        self.assertFalse(result["ok"])
        self.assertEqual(WORLD["agents"]["rover-mock"]["battery"], 1.0)

    def test_execute_move_invalid_direction(self):
        result = execute_action("rover-mock", "move", {"direction": "up"})
        self.assertFalse(result["ok"])
        self.assertIn("Invalid direction", result["error"])

    def test_execute_unknown_action(self):
        result = execute_action("rover-mock", "drill", {})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown action", result["error"])

    def test_execute_unknown_agent(self):
        result = execute_action("rover-99", "move", {"direction": "east"})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_execute_move_all_directions(self):
        WORLD["agents"]["rover-mock"]["position"] = [10, 10]
        for direction, expected in [("north", [10, 9]), ("south", [10, 11]),
                                     ("east", [11, 10]), ("west", [10, 10])]:
            result = execute_action("rover-mock", "move", {"direction": direction})
            self.assertTrue(result["ok"], f"Failed for direction {direction}")

    def test_mission_in_snapshot(self):
        snap = get_snapshot()
        agent = snap["agents"]["rover-mock"]
        self.assertIn("mission", agent)
        self.assertEqual(agent["mission"]["objective"], "Explore the terrain")
        self.assertEqual(agent["mission"]["plan"], [])


class TestStones(unittest.TestCase):

    def test_stones_in_snapshot(self):
        snap = get_snapshot()
        self.assertIn("stones", snap)
        self.assertGreaterEqual(len(snap["stones"]), 5)
        self.assertLessEqual(len(snap["stones"]), 8)

    def test_stone_shape(self):
        snap = get_snapshot()
        for stone in snap["stones"]:
            self.assertIn("position", stone)
            self.assertIn("type", stone)
            self.assertEqual(len(stone["position"]), 2)
            self.assertIn(stone["type"], ("core", "basalt"))

    def test_stones_in_bounds(self):
        snap = get_snapshot()
        for stone in snap["stones"]:
            x, y = stone["position"]
            self.assertGreaterEqual(x, 0)
            self.assertLess(x, GRID_W)
            self.assertGreaterEqual(y, 0)
            self.assertLess(y, GRID_H)

    def test_stones_avoid_agent_starts(self):
        snap = get_snapshot()
        for stone in snap["stones"]:
            pos = tuple(stone["position"])
            self.assertNotIn(pos, AGENT_STARTS)


class TestVisited(unittest.TestCase):

    def setUp(self):
        WORLD["agents"]["rover-mock"]["position"] = [10, 10]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        WORLD["agents"]["rover-mock"]["mission"] = {"objective": "Explore the terrain", "plan": []}
        WORLD["agents"]["rover-mock"]["visited"] = [[10, 10]]

    def test_visited_initial(self):
        self.assertEqual(WORLD["agents"]["rover-mock"]["visited"], [[10, 10]])

    def test_move_updates_visited(self):
        execute_action("rover-mock", "move", {"direction": "east"})
        visited = WORLD["agents"]["rover-mock"]["visited"]
        self.assertIn([11, 10], visited)

    def test_visited_no_duplicates(self):
        execute_action("rover-mock", "move", {"direction": "east"})
        execute_action("rover-mock", "move", {"direction": "west"})
        visited = WORLD["agents"]["rover-mock"]["visited"]
        self.assertEqual(visited.count([10, 10]), 1)


class TestCheckGround(unittest.TestCase):

    def setUp(self):
        WORLD["agents"]["rover-mock"]["position"] = [10, 10]
        WORLD["agents"]["rover-mock"]["battery"] = 1.0
        WORLD["agents"]["rover-mock"]["mission"] = {"objective": "Explore the terrain", "plan": []}
        WORLD["agents"]["rover-mock"]["visited"] = [[10, 10]]
        self._original_stones = WORLD.get("stones", [])

    def tearDown(self):
        WORLD["stones"] = self._original_stones

    def test_check_ground_finds_stone(self):
        WORLD["stones"] = [{"position": [10, 10], "type": "core"}]
        result = check_ground("rover-mock")
        self.assertEqual(result["stone"], {"type": "core"})

    def test_check_ground_no_stone(self):
        WORLD["stones"] = [{"position": [5, 5], "type": "basalt"}]
        result = check_ground("rover-mock")
        self.assertIsNone(result["stone"])

    def test_move_result_includes_ground(self):
        WORLD["stones"] = []
        result = execute_action("rover-mock", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertIn("ground", result)
        self.assertIsNone(result["ground"]["stone"])
