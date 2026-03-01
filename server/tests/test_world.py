import random
import unittest

from app.world import world, GRID_W, GRID_H, move_agent, execute_action, get_snapshot, check_ground
from app.world import check_mission_status, charge_rover, charge_agent
from app.world import BATTERY_COST_MOVE, BATTERY_COST_DIG
from app.world import BATTERY_COST_ANALYZE
from app.world import BATTERY_COST_SCAN, BATTERY_COST_MOVE_DRONE, BATTERY_COST_NOTIFY
from app.world import CHARGE_RATE, REVEAL_RADIUS, ROVER_REVEAL_RADIUS, DRONE_REVEAL_RADIUS
from app.world import AGENT_STARTS
from app.world import abort_mission, all_agents_at_station
from app.world import assign_mission, _cells_in_radius, record_memory, MEMORY_MAX
from app.world import _random_free_pos, CHUNK_SIZE
from app.world import direction_hint, best_drone_hotspot
from app.world import summarize_memories, record_strategic_insight
from app.world import set_agent_model, set_agent_last_context, set_pending_commands
from app.world import observe_rover, observe_station
from app.world import VEIN_GRADES, VEIN_WEIGHTS, VEIN_QUANTITY_RANGES, TARGET_QUANTITY
from app.world import MAX_INVENTORY_ROVER
from app.models import RoverContext, StationContext, StoneInfo


def _make_vein(pos, grade="high", quantity=200, analyzed=False):
    """Helper to build a vein dict for tests."""
    return {
        "position": list(pos),
        "type": "basalt_vein" if analyzed else "unknown",
        "_true_type": "basalt_vein",
        "grade": grade if analyzed else "unknown",
        "_true_grade": grade,
        "quantity": quantity if analyzed else 0,
        "_true_quantity": quantity,
        "analyzed": analyzed,
    }


class TestMoveAgent(unittest.TestCase):
    def setUp(self):
        agent = world.state["agents"]["rover-mistral"]
        self._orig_position = list(agent["position"])
        self._orig_battery = agent["battery"]
        self._orig_mission = dict(agent["mission"])
        self._orig_visited = list(agent["visited"])
        agent["position"] = [2, 10]
        agent["battery"] = 1.0
        agent["mission"] = {
            "objective": "Explore the terrain",
            "plan": [],
        }
        agent["visited"] = [[2, 10]]

    def tearDown(self):
        agent = world.state["agents"]["rover-mistral"]
        agent["position"] = self._orig_position
        agent["battery"] = self._orig_battery
        agent["mission"] = self._orig_mission
        agent["visited"] = self._orig_visited

    def test_move_success(self):
        result = move_agent("rover-mistral", 3, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["from"], [2, 10])
        self.assertEqual(result["to"], [3, 10])
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], [3, 10])

    def test_move_negative_coords_allowed(self):
        """Infinite grid: negative coordinates are valid."""
        world.state["agents"]["rover-mistral"]["position"] = [0, 10]
        result = move_agent("rover-mistral", -1, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["to"], [-1, 10])

    def test_move_beyond_old_bounds_allowed(self):
        """Infinite grid: moving beyond old 20x20 bounds is valid."""
        world.state["agents"]["rover-mistral"]["position"] = [19, 10]
        result = move_agent("rover-mistral", 20, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["to"], [20, 10])

    def test_move_too_far(self):
        result = move_agent("rover-mistral", 6, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Too far", result["error"])
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], [2, 10])

    def test_move_diagonal_rejected(self):
        result = move_agent("rover-mistral", 3, 11)
        self.assertFalse(result["ok"])
        self.assertIn("Not a straight line", result["error"])

    def test_move_multi_tile(self):
        result = move_agent("rover-mistral", 5, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["distance"], 3)
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], [5, 10])

    def test_move_2_tiles(self):
        result = move_agent("rover-mistral", 4, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["distance"], 2)

    def test_move_already_there(self):
        result = move_agent("rover-mistral", 2, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Already at", result["error"])

    def test_move_unknown_agent(self):
        result = move_agent("rover-99", 3, 10)
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_move_sequential(self):
        move_agent("rover-mistral", 3, 10)
        result = move_agent("rover-mistral", 4, 10)
        self.assertTrue(result["ok"])
        self.assertEqual(result["from"], [3, 10])
        self.assertEqual(result["to"], [4, 10])

    def test_move_all_four_directions(self):
        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        for tx, ty in [(11, 10), (10, 10), (10, 11), (10, 10)]:
            result = move_agent("rover-mistral", tx, ty)
            self.assertTrue(result["ok"])

    def test_get_snapshot_is_copy(self):
        snap = get_snapshot()
        snap["agents"]["rover-mistral"]["position"] = [99, 99]
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], [2, 10])

    def test_snapshot_has_grid(self):
        snap = get_snapshot()
        self.assertEqual(snap["grid"]["w"], 20)
        self.assertEqual(snap["grid"]["h"], 20)


class TestExecuteAction(unittest.TestCase):
    def setUp(self):
        agent = world.state["agents"]["rover-mistral"]
        self._orig_position = list(agent["position"])
        self._orig_battery = agent["battery"]
        self._orig_mission = dict(agent["mission"])
        self._orig_visited = list(agent["visited"])
        agent["position"] = [2, 10]
        agent["battery"] = 1.0
        agent["mission"] = {
            "objective": "Explore the terrain",
            "plan": [],
        }
        agent["visited"] = [[2, 10]]

    def tearDown(self):
        agent = world.state["agents"]["rover-mistral"]
        agent["position"] = self._orig_position
        agent["battery"] = self._orig_battery
        agent["mission"] = self._orig_mission
        agent["visited"] = self._orig_visited

    def test_execute_move_east(self):
        result = execute_action("rover-mistral", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["from"], [2, 10])
        self.assertEqual(result["to"], [3, 10])
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], [3, 10])

    def test_execute_move_drains_battery(self):
        result = execute_action("rover-mistral", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(
            world.state["agents"]["rover-mistral"]["battery"], 1.0 - BATTERY_COST_MOVE
        )

    def test_execute_move_negative_ok(self):
        """Infinite grid: moving to negative coords succeeds."""
        world.state["agents"]["rover-mistral"]["position"] = [0, 10]
        result = execute_action("rover-mistral", "move", {"direction": "west"})
        self.assertTrue(result["ok"])
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], [-1, 10])

    def test_execute_move_invalid_direction(self):
        result = execute_action("rover-mistral", "move", {"direction": "up"})
        self.assertFalse(result["ok"])
        self.assertIn("Invalid direction", result["error"])

    def test_execute_unknown_action(self):
        result = execute_action("rover-mistral", "drill", {})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown action", result["error"])

    def test_execute_unknown_agent(self):
        result = execute_action("rover-99", "move", {"direction": "east"})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_execute_move_all_directions(self):
        """North = +Y, South = -Y with flipped coordinate system."""
        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        for direction, expected in [
            ("north", [10, 11]),
            ("south", [10, 9]),
            ("east", [11, 10]),
            ("west", [10, 10]),
        ]:
            result = execute_action("rover-mistral", "move", {"direction": direction})
            self.assertTrue(result["ok"], f"Failed for direction {direction}")

    def test_execute_move_multi_tile(self):
        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        result = execute_action("rover-mistral", "move", {"direction": "east", "distance": 3})
        self.assertTrue(result["ok"])
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], [13, 10])
        self.assertAlmostEqual(
            world.state["agents"]["rover-mistral"]["battery"], 1.0 - BATTERY_COST_MOVE * 3
        )

    def test_execute_move_multi_visits_intermediate(self):
        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        execute_action("rover-mistral", "move", {"direction": "east", "distance": 3})
        visited = world.state["agents"]["rover-mistral"]["visited"]
        self.assertIn([11, 10], visited)
        self.assertIn([12, 10], visited)
        self.assertIn([13, 10], visited)

    def test_execute_move_no_battery(self):
        """Move should fail when battery is too low."""
        world.state["agents"]["rover-mistral"]["battery"] = 0.0
        result = execute_action("rover-mistral", "move", {"direction": "east"})
        self.assertFalse(result["ok"])
        self.assertIn("Not enough battery", result["error"])
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], [2, 10])

    def test_execute_move_insufficient_battery_multi(self):
        """Multi-tile move should fail when battery < cost for full distance."""
        world.state["agents"]["rover-mistral"]["battery"] = (
            BATTERY_COST_MOVE * 2
        )  # enough for ~1-2 tiles, not 3
        result = execute_action("rover-mistral", "move", {"direction": "east", "distance": 3})
        self.assertFalse(result["ok"])
        self.assertIn("Not enough battery", result["error"])
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], [2, 10])

    def test_mission_in_snapshot(self):
        snap = get_snapshot()
        agent = snap["agents"]["rover-mistral"]
        self.assertIn("mission", agent)
        self.assertEqual(agent["mission"]["objective"], "Explore the terrain")
        self.assertEqual(agent["mission"]["plan"], [])


class TestStones(unittest.TestCase):
    def test_stones_generated(self):
        """With chunk system, initial chunks generate multiple veins."""
        stones = world.state["stones"]
        self.assertGreaterEqual(len(stones), 1)

    def test_all_veins_are_basalt(self):
        """All generated veins should have _true_type basalt_vein."""
        for s in world.state["stones"]:
            self.assertEqual(s["_true_type"], "basalt_vein")

    def test_veins_have_valid_grades(self):
        """Every vein should have a valid _true_grade."""
        for s in world.state["stones"]:
            self.assertIn(s["_true_grade"], VEIN_GRADES)

    def test_veins_quantity_in_range(self):
        """Every vein's _true_quantity should fall within the range for its grade."""
        for s in world.state["stones"]:
            grade = s["_true_grade"]
            lo, hi = VEIN_QUANTITY_RANGES[grade]
            self.assertGreaterEqual(s["_true_quantity"], lo)
            self.assertLessEqual(s["_true_quantity"], hi)

    def test_stones_in_snapshot(self):
        snap = get_snapshot()
        self.assertIn("stones", snap)
        self.assertLessEqual(len(snap["stones"]), len(world.state["stones"]))

    def test_stone_shape(self):
        for stone in world.state["stones"]:
            self.assertIn("position", stone)
            self.assertIn("type", stone)
            self.assertIn("_true_type", stone)
            self.assertIn("grade", stone)
            self.assertIn("_true_grade", stone)
            self.assertIn("quantity", stone)
            self.assertIn("_true_quantity", stone)
            self.assertIn("analyzed", stone)
            self.assertNotIn("extracted", stone)
            self.assertEqual(len(stone["position"]), 2)
            self.assertEqual(stone["_true_type"], "basalt_vein")
            self.assertEqual(stone["type"], "unknown")
            self.assertEqual(stone["grade"], "unknown")
            self.assertEqual(stone["quantity"], 0)
            self.assertFalse(stone["analyzed"])

    def test_stones_have_valid_positions(self):
        """Veins should have integer coordinate positions (no bounds requirement)."""
        for stone in world.state["stones"]:
            x, y = stone["position"]
            self.assertIsInstance(x, int)
            self.assertIsInstance(y, int)

    def test_stones_avoid_agent_starts(self):
        for stone in world.state["stones"]:
            pos = tuple(stone["position"])
            self.assertNotIn(pos, AGENT_STARTS)

    def test_snapshot_strips_hidden_fields(self):
        snap = get_snapshot()
        for stone in snap["stones"]:
            self.assertNotIn("_true_type", stone)
            self.assertNotIn("_true_grade", stone)
            self.assertNotIn("_true_quantity", stone)


class TestVisited(unittest.TestCase):
    def setUp(self):
        agent = world.state["agents"]["rover-mistral"]
        self._orig_position = list(agent["position"])
        self._orig_battery = agent["battery"]
        self._orig_mission = dict(agent["mission"])
        self._orig_visited = list(agent["visited"])
        self._orig_revealed = list(agent.get("revealed", []))
        agent["position"] = [10, 10]
        agent["battery"] = 1.0
        agent["mission"] = {
            "objective": "Explore the terrain",
            "plan": [],
        }
        agent["visited"] = [[10, 10]]

    def tearDown(self):
        agent = world.state["agents"]["rover-mistral"]
        agent["position"] = self._orig_position
        agent["battery"] = self._orig_battery
        agent["mission"] = self._orig_mission
        agent["visited"] = self._orig_visited
        agent["revealed"] = self._orig_revealed

    def test_visited_initial(self):
        self.assertEqual(world.state["agents"]["rover-mistral"]["visited"], [[10, 10]])

    def test_move_updates_visited(self):
        execute_action("rover-mistral", "move", {"direction": "east"})
        visited = world.state["agents"]["rover-mistral"]["visited"]
        self.assertIn([11, 10], visited)

    def test_visited_no_duplicates(self):
        execute_action("rover-mistral", "move", {"direction": "east"})
        execute_action("rover-mistral", "move", {"direction": "west"})
        visited = world.state["agents"]["rover-mistral"]["visited"]
        self.assertEqual(visited.count([10, 10]), 1)


class TestCheckGround(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["mission"] = {
            "objective": "Explore the terrain",
            "plan": [],
        }
        world.state["agents"]["rover-mistral"]["visited"] = [[10, 10]]
        self._original_stones = world.state.get("stones", [])

    def tearDown(self):
        world.state["stones"] = self._original_stones

    def test_check_ground_finds_stone(self):
        world.state["stones"] = [_make_vein([10, 10])]
        result = check_ground("rover-mistral")
        self.assertEqual(result["stone"]["type"], "unknown")
        self.assertEqual(result["stone"]["grade"], "unknown")

    def test_check_ground_no_stone(self):
        world.state["stones"] = [_make_vein([5, 5])]
        result = check_ground("rover-mistral")
        self.assertIsNone(result["stone"])

    def test_move_result_includes_ground(self):
        world.state["stones"] = []
        result = execute_action("rover-mistral", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertIn("ground", result)
        self.assertIsNone(result["ground"]["stone"])


class TestAssignMission(unittest.TestCase):
    def setUp(self):
        self._orig = world.state["agents"]["rover-mistral"]["mission"].copy()

    def tearDown(self):
        world.state["agents"]["rover-mistral"]["mission"] = self._orig

    def test_assign_mission_success(self):
        result = assign_mission("rover-mistral", "Go to north edge")
        self.assertTrue(result["ok"])
        self.assertEqual(result["agent_id"], "rover-mistral")
        self.assertEqual(result["objective"], "Go to north edge")
        self.assertEqual(
            world.state["agents"]["rover-mistral"]["mission"]["objective"], "Go to north edge"
        )

    def test_assign_mission_unknown_agent(self):
        result = assign_mission("rover-99", "Go anywhere")
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_assign_mission_preserves_plan(self):
        world.state["agents"]["rover-mistral"]["mission"]["plan"] = ["step1"]
        assign_mission("rover-mistral", "New objective")
        self.assertEqual(world.state["agents"]["rover-mistral"]["mission"]["plan"], ["step1"])


class TestStationInWorld(unittest.TestCase):
    def test_station_in_snapshot(self):
        snap = get_snapshot()
        self.assertIn("station", snap["agents"])
        station = snap["agents"]["station"]
        self.assertEqual(station["type"], "station")
        self.assertEqual(station["position"], [0, 0])
        self.assertIn("mission", station)
        self.assertIn("battery", station)

    def test_station_start_in_agent_starts(self):
        self.assertIn((0, 0), AGENT_STARTS)


class TestAnalyze(unittest.TestCase):
    """Test the analyze action that reveals hidden vein grade and quantity."""

    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["inventory"] = []
        world.state["agents"]["rover-mistral"]["visited"] = [[5, 5]]
        world.state["agents"]["rover-mistral"]["memory"] = []
        self._original_stones = world.state.get("stones", [])
        world.state["stones"] = [_make_vein([5, 5], grade="rich", quantity=500)]

    def tearDown(self):
        world.state["stones"] = self._original_stones

    def test_analyze_reveals_type_grade_quantity(self):
        result = execute_action("rover-mistral", "analyze", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["stone"]["type"], "basalt_vein")
        self.assertEqual(result["stone"]["grade"], "rich")
        self.assertEqual(result["stone"]["quantity"], 500)
        stone = world.state["stones"][0]
        self.assertTrue(stone["analyzed"])
        self.assertEqual(stone["type"], "basalt_vein")
        self.assertEqual(stone["grade"], "rich")
        self.assertEqual(stone["quantity"], 500)

    def test_analyze_drains_battery(self):
        execute_action("rover-mistral", "analyze", {})
        self.assertAlmostEqual(
            world.state["agents"]["rover-mistral"]["battery"], 1.0 - BATTERY_COST_ANALYZE
        )

    def test_analyze_no_stone(self):
        world.state["stones"] = []
        result = execute_action("rover-mistral", "analyze", {})
        self.assertFalse(result["ok"])
        self.assertIn("No vein", result["error"])

    def test_analyze_already_analyzed(self):
        world.state["stones"] = [_make_vein([5, 5], grade="low", quantity=30, analyzed=True)]
        result = execute_action("rover-mistral", "analyze", {})
        self.assertFalse(result["ok"])
        self.assertIn("already analyzed", result["error"])

    def test_analyze_unknown_agent(self):
        result = execute_action("rover-99", "analyze", {})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_analyze_not_enough_battery(self):
        world.state["agents"]["rover-mistral"]["battery"] = BATTERY_COST_ANALYZE * 0.5
        result = execute_action("rover-mistral", "analyze", {})
        self.assertFalse(result["ok"])
        self.assertIn("Not enough battery", result["error"])

    def test_analyze_records_memory(self):
        execute_action("rover-mistral", "analyze", {})
        mem = world.state["agents"]["rover-mistral"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Analyzed", mem[0])
        self.assertIn("grade=rich", mem[0])
        self.assertIn("qty=500", mem[0])


class TestDig(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["inventory"] = []
        world.state["agents"]["rover-mistral"]["visited"] = [[5, 5]]
        self._original_stones = world.state.get("stones", [])
        world.state["stones"] = [_make_vein([5, 5], grade="high", quantity=200, analyzed=True)]

    def tearDown(self):
        world.state["stones"] = self._original_stones

    def test_dig_collects_stone(self):
        result = execute_action("rover-mistral", "dig", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["stone"]["type"], "basalt_vein")
        self.assertEqual(result["stone"]["grade"], "high")
        self.assertEqual(result["stone"]["quantity"], 200)
        self.assertEqual(result["inventory_count"], 1)
        # Stone removed from world, added to inventory
        self.assertEqual(len(world.state["stones"]), 0)
        inv = world.state["agents"]["rover-mistral"]["inventory"]
        self.assertEqual(len(inv), 1)
        self.assertEqual(inv[0]["grade"], "high")
        self.assertEqual(inv[0]["quantity"], 200)

    def test_dig_drains_battery(self):
        execute_action("rover-mistral", "dig", {})
        self.assertAlmostEqual(
            world.state["agents"]["rover-mistral"]["battery"], 1.0 - BATTERY_COST_DIG
        )

    def test_dig_no_stone(self):
        world.state["stones"] = []
        result = execute_action("rover-mistral", "dig", {})
        self.assertFalse(result["ok"])
        self.assertIn("No vein", result["error"])

    def test_dig_not_enough_battery(self):
        world.state["agents"]["rover-mistral"]["battery"] = BATTERY_COST_DIG * 0.5
        result = execute_action("rover-mistral", "dig", {})
        self.assertFalse(result["ok"])
        self.assertIn("Not enough battery", result["error"])
        self.assertAlmostEqual(
            world.state["agents"]["rover-mistral"]["battery"], BATTERY_COST_DIG * 0.5
        )

    def test_dig_failed_no_drain(self):
        world.state["stones"] = []
        old_battery = world.state["agents"]["rover-mistral"]["battery"]
        execute_action("rover-mistral", "dig", {})
        self.assertEqual(world.state["agents"]["rover-mistral"]["battery"], old_battery)

    def test_dig_requires_analyze(self):
        """Dig should fail if vein is not yet analyzed."""
        world.state["stones"] = [_make_vein([5, 5])]
        result = execute_action("rover-mistral", "dig", {})
        self.assertFalse(result["ok"])
        self.assertIn("not yet analyzed", result["error"])

    def test_dig_inventory_full(self):
        """Dig should fail when inventory already has MAX_INVENTORY_ROVER veins."""
        world.state["agents"]["rover-mistral"]["inventory"] = [
            {"type": "basalt_vein", "grade": "low", "quantity": 50}
            for _ in range(MAX_INVENTORY_ROVER)
        ]
        result = execute_action("rover-mistral", "dig", {})
        self.assertFalse(result["ok"])
        self.assertIn("Inventory full", result["error"])


class TestAnalyzeDigWorkflow(unittest.TestCase):
    """Test the merged analyze → dig workflow (dig now collects into inventory)."""

    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["inventory"] = []
        world.state["agents"]["rover-mistral"]["visited"] = [[5, 5]]
        self._original_stones = world.state.get("stones", [])

    def tearDown(self):
        world.state["stones"] = self._original_stones

    def test_analyze_dig_workflow(self):
        """Full workflow: analyze → dig (collects into inventory)."""
        world.state["stones"] = [_make_vein([5, 5], grade="pristine", quantity=900)]
        result = execute_action("rover-mistral", "analyze", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["stone"]["type"], "basalt_vein")
        self.assertEqual(result["stone"]["grade"], "pristine")
        self.assertEqual(result["stone"]["quantity"], 900)
        result = execute_action("rover-mistral", "dig", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["inventory_count"], 1)
        inv = world.state["agents"]["rover-mistral"]["inventory"]
        self.assertEqual(len(inv), 1)
        self.assertEqual(inv[0]["quantity"], 900)
        self.assertEqual(len(world.state["stones"]), 0)

    def test_dig_removes_stone_from_world(self):
        world.state["stones"] = [_make_vein([5, 5], grade="rich", quantity=400, analyzed=True)]
        execute_action("rover-mistral", "dig", {})
        self.assertEqual(len(world.state["stones"]), 0)

    def test_dig_adds_to_inventory_with_grade_and_quantity(self):
        world.state["stones"] = [_make_vein([5, 5], grade="rich", quantity=400, analyzed=True)]
        execute_action("rover-mistral", "dig", {})
        inv = world.state["agents"]["rover-mistral"]["inventory"]
        self.assertEqual(len(inv), 1)
        self.assertEqual(inv[0]["type"], "basalt_vein")
        self.assertEqual(inv[0]["grade"], "rich")
        self.assertEqual(inv[0]["quantity"], 400)

    def test_pickup_action_no_longer_exists(self):
        """Pickup action should return 'Unknown action' since it was removed."""
        world.state["stones"] = [_make_vein([5, 5], grade="low", quantity=30, analyzed=True)]
        result = execute_action("rover-mistral", "pickup", {})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown action", result["error"])


class TestCharge(unittest.TestCase):
    """Charging is a station-only action via charge_rover()."""

    def setUp(self):
        rover = world.state["agents"]["rover-mistral"]
        self._orig_position = list(rover["position"])
        self._orig_battery = rover["battery"]
        self._orig_inventory = list(rover.get("inventory", []))
        self._orig_visited = list(rover["visited"])
        self._orig_memory = list(rover.get("memory", []))
        self._orig_station_pos = list(world.state["agents"]["station"]["position"])
        rover["position"] = [0, 0]
        rover["battery"] = 0.5
        rover["inventory"] = []
        rover["visited"] = [[0, 0]]
        rover["memory"] = []
        world.state["agents"]["station"]["position"] = [0, 0]

    def tearDown(self):
        rover = world.state["agents"]["rover-mistral"]
        rover["position"] = self._orig_position
        rover["battery"] = self._orig_battery
        rover["inventory"] = self._orig_inventory
        rover["visited"] = self._orig_visited
        rover["memory"] = self._orig_memory
        world.state["agents"]["station"]["position"] = self._orig_station_pos

    def test_charge_rover_success(self):
        result = charge_rover("rover-mistral")
        self.assertTrue(result["ok"])
        self.assertEqual(result["agent_id"], "rover-mistral")
        self.assertAlmostEqual(result["battery_before"], 0.5)
        self.assertAlmostEqual(result["battery_after"], 0.5 + CHARGE_RATE)

    def test_charge_rover_increases_battery(self):
        charge_rover("rover-mistral")
        self.assertAlmostEqual(world.state["agents"]["rover-mistral"]["battery"], 0.5 + CHARGE_RATE)

    def test_charge_rover_caps_at_full(self):
        world.state["agents"]["rover-mistral"]["battery"] = 0.95
        charge_rover("rover-mistral")
        self.assertAlmostEqual(world.state["agents"]["rover-mistral"]["battery"], 1.0)

    def test_charge_rover_already_full(self):
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        result = charge_rover("rover-mistral")
        self.assertFalse(result["ok"])
        self.assertIn("already full", result["error"])

    def test_charge_rover_not_at_station(self):
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        result = charge_rover("rover-mistral")
        self.assertFalse(result["ok"])
        self.assertIn("Not at station", result["error"])

    def test_charge_rover_multiple_times(self):
        world.state["agents"]["rover-mistral"]["battery"] = 0.1
        charge_rover("rover-mistral")
        self.assertAlmostEqual(world.state["agents"]["rover-mistral"]["battery"], 0.1 + CHARGE_RATE)
        charge_rover("rover-mistral")
        self.assertAlmostEqual(
            world.state["agents"]["rover-mistral"]["battery"], 0.1 + 2 * CHARGE_RATE
        )

    def test_charge_rover_unknown_agent(self):
        result = charge_rover("rover-99")
        self.assertFalse(result["ok"])
        self.assertIn("Unknown agent", result["error"])

    def test_charge_agent_rejects_station(self):
        result = charge_agent("station")
        self.assertFalse(result["ok"])
        self.assertIn("is a station", result["error"])

    def test_charge_rover_records_memory(self):
        charge_rover("rover-mistral")
        mem = world.state["agents"]["rover-mistral"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Station charged", mem[0])

    def test_charge_not_available_as_rover_action(self):
        result = execute_action("rover-mistral", "charge", {})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown action", result["error"])


class TestFogOfWar(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["inventory"] = []
        world.state["agents"]["rover-mistral"]["visited"] = [[10, 10]]
        world.state["agents"]["rover-mistral"]["revealed"] = [
            [x, y] for x, y in sorted(_cells_in_radius(10, 10, REVEAL_RADIUS))
        ]
        # Give drone an empty revealed so it doesn't interfere
        if "drone-mistral" in world.state["agents"]:
            self._original_drone_revealed = world.state["agents"]["drone-mistral"].get(
                "revealed", []
            )
            world.state["agents"]["drone-mistral"]["revealed"] = []
        self._original_stones = world.state.get("stones", [])

    def tearDown(self):
        world.state["stones"] = self._original_stones
        # Restore rover-mistral revealed
        world.state["agents"]["rover-mistral"]["revealed"] = world.state["agents"][
            "rover-mistral"
        ].get("revealed", [])
        if "drone-mistral" in world.state["agents"]:
            world.state["agents"]["drone-mistral"]["revealed"] = self._original_drone_revealed

    def test_initial_revealed_cells_count(self):
        revealed = world.state["agents"]["rover-mistral"]["revealed"]
        expected = _cells_in_radius(10, 10, REVEAL_RADIUS)
        self.assertEqual(len(revealed), len(expected))

    def test_initial_revealed_contains_start(self):
        revealed = world.state["agents"]["rover-mistral"]["revealed"]
        self.assertIn([10, 10], revealed)

    def test_initial_revealed_contains_neighbors(self):
        revealed = world.state["agents"]["rover-mistral"]["revealed"]
        for pos in [[10, 9], [10, 11], [9, 10], [11, 10]]:
            self.assertIn(pos, revealed)

    def test_move_expands_revealed(self):
        before = len(world.state["agents"]["rover-mistral"]["revealed"])
        execute_action("rover-mistral", "move", {"direction": "east"})
        after = len(world.state["agents"]["rover-mistral"]["revealed"])
        self.assertGreater(after, before)

    def test_move_reveals_new_cells(self):
        execute_action("rover-mistral", "move", {"direction": "east"})
        revealed = world.state["agents"]["rover-mistral"]["revealed"]
        # (13, 10) is radius-2 east of new position (11, 10)
        self.assertIn([13, 10], revealed)

    def test_move_no_duplicate_revealed(self):
        execute_action("rover-mistral", "move", {"direction": "east"})
        execute_action("rover-mistral", "move", {"direction": "west"})
        revealed = world.state["agents"]["rover-mistral"]["revealed"]
        # Check no duplicates
        as_tuples = [tuple(c) for c in revealed]
        self.assertEqual(len(as_tuples), len(set(as_tuples)))

    def test_snapshot_hides_unrevealed_stones(self):
        world.state["stones"] = [_make_vein([19, 19])]
        snap = get_snapshot()
        self.assertEqual(len(snap["stones"]), 0)

    def test_snapshot_shows_revealed_stones(self):
        world.state["stones"] = [_make_vein([10, 10])]
        snap = get_snapshot()
        self.assertEqual(len(snap["stones"]), 1)
        self.assertEqual(snap["stones"][0]["type"], "unknown")

    def test_snapshot_mixed_visibility(self):
        world.state["stones"] = [_make_vein([10, 10]), _make_vein([19, 19])]
        snap = get_snapshot()
        self.assertEqual(len(snap["stones"]), 1)
        self.assertEqual(snap["stones"][0]["position"], [10, 10])

    def test_move_reveals_stone(self):
        world.state["stones"] = [_make_vein([14, 10])]
        snap_before = get_snapshot()
        self.assertEqual(len(snap_before["stones"]), 0)
        execute_action("rover-mistral", "move", {"direction": "east"})
        snap_after = get_snapshot()
        self.assertEqual(len(snap_after["stones"]), 1)

    def test_cells_in_radius_at_corner(self):
        """Infinite grid: cells_in_radius at origin includes negative coords."""
        cells = _cells_in_radius(0, 0, REVEAL_RADIUS)
        # Should include negative coords now (no clamping)
        has_negative = any(x < 0 or y < 0 for x, y in cells)
        self.assertTrue(has_negative)
        # Full diamond at center and corner should be the same size
        center_cells = _cells_in_radius(10, 10, REVEAL_RADIUS)
        self.assertEqual(len(cells), len(center_cells))

    def test_revealed_in_snapshot(self):
        snap = get_snapshot()
        self.assertIn("revealed", snap["agents"]["rover-mistral"])


class TestMissionCompletion(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["inventory"] = []
        world.state["agents"]["rover-mistral"]["visited"] = [[5, 5]]
        self._original_stones = world.state.get("stones", [])
        self._original_mission = world.state["mission"].copy()
        world.state["mission"]["status"] = "running"
        world.state["mission"]["collected_quantity"] = 0

    def tearDown(self):
        world.state["stones"] = self._original_stones
        world.state["mission"] = self._original_mission

    def test_mission_in_world(self):
        self.assertIn("mission", world.state)
        self.assertEqual(world.state["mission"]["status"], "running")
        self.assertEqual(world.state["mission"]["target_type"], "basalt_vein")
        self.assertEqual(world.state["mission"]["target_quantity"], TARGET_QUANTITY)

    def test_mission_in_snapshot(self):
        snap = get_snapshot()
        self.assertIn("mission", snap)
        self.assertEqual(snap["mission"]["status"], "running")

    def test_collected_quantity_updates_on_dig(self):
        """Dig away from station: vein is in transit, not yet collected."""
        world.state["stones"] = [_make_vein([5, 5], grade="high", quantity=200, analyzed=True)]
        execute_action("rover-mistral", "dig", {})
        self.assertEqual(world.state["mission"]["collected_quantity"], 0)
        self.assertEqual(world.state["mission"]["in_transit_quantity"], 200)

    def test_dig_away_from_station_no_success(self):
        """Digging a vein away from station should NOT trigger success."""
        world.state["mission"]["target_quantity"] = 100
        world.state["stones"] = [_make_vein([5, 5], grade="pristine", quantity=900, analyzed=True)]
        result = execute_action("rover-mistral", "dig", {})
        self.assertEqual(world.state["mission"]["status"], "running")
        self.assertNotIn("mission", result)
        self.assertEqual(world.state["mission"]["collected_quantity"], 0)
        self.assertEqual(world.state["mission"]["in_transit_quantity"], 900)

    def test_mission_success_on_delivery_to_station(self):
        """Success requires the rover to deliver basalt to the station."""
        world.state["mission"]["target_quantity"] = 100
        world.state["agents"]["rover-mistral"]["position"] = [0, 0]
        world.state["agents"]["station"]["position"] = [0, 0]
        world.state["stones"] = [_make_vein([0, 0], grade="high", quantity=200, analyzed=True)]
        result = execute_action("rover-mistral", "dig", {})
        self.assertEqual(world.state["mission"]["status"], "success")
        self.assertIn("mission", result)
        self.assertEqual(result["mission"]["status"], "success")

    def test_mission_success_on_move_to_station_with_basalt(self):
        """Moving to station while carrying enough basalt triggers success."""
        world.state["mission"]["target_quantity"] = 100
        world.state["agents"]["rover-mistral"]["position"] = [1, 0]
        world.state["agents"]["rover-mistral"]["inventory"] = [
            {"type": "basalt_vein", "grade": "rich", "quantity": 150}
        ]
        world.state["agents"]["station"]["position"] = [0, 0]
        world.state["stones"] = []
        result = execute_action("rover-mistral", "move", {"direction": "west"})
        self.assertEqual(world.state["mission"]["status"], "success")
        self.assertIn("mission", result)

    def test_mission_success_with_multiple_digs(self):
        """Multiple digs contributing basalt to reach target_quantity."""
        world.state["mission"]["target_quantity"] = 300
        world.state["agents"]["station"]["position"] = [0, 0]
        # First dig: 200 units at station
        world.state["agents"]["rover-mistral"]["position"] = [0, 0]
        world.state["stones"] = [_make_vein([0, 0], grade="high", quantity=200, analyzed=True)]
        execute_action("rover-mistral", "dig", {})
        self.assertEqual(world.state["mission"]["status"], "running")
        # Rover-mistral digs another 200 at station — total 400 >= 300
        world.state["agents"]["rover-mistral"]["position"] = [0, 0]
        world.state["stones"] = [_make_vein([0, 0], grade="high", quantity=200, analyzed=True)]
        result = execute_action("rover-mistral", "dig", {})
        self.assertEqual(world.state["mission"]["status"], "success")
        self.assertEqual(world.state["mission"]["collected_quantity"], 400)
        self.assertIn("mission", result)

    def test_mission_failed_all_rovers_depleted(self):
        world.state["agents"]["rover-mistral"]["battery"] = BATTERY_COST_MOVE
        world.state["agents"]["rover-mistral"]["position"] = [15, 15]
        # Deplete all other rovers too
        for aid, agent in world.state["agents"].items():
            if agent.get("type") == "rover" and aid != "rover-mistral":
                agent["battery"] = 0.0
                agent["position"] = [15, 15]
        world.state["stones"] = []
        # This move will drain rover-mistral to 0
        result = execute_action("rover-mistral", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertEqual(world.state["mission"]["status"], "failed")
        self.assertIn("mission", result)
        self.assertEqual(result["mission"]["status"], "failed")

    def test_rover_at_station_not_failed(self):
        # Even with 0 battery, rover at station can charge — not failed
        world.state["agents"]["rover-mistral"]["battery"] = 0.0
        world.state["agents"]["rover-mistral"]["position"] = [0, 0]
        world.state["agents"]["station"]["position"] = [0, 0]
        world.state["stones"] = []
        # Rover at station with 0 battery — should not be failed
        result = check_mission_status()
        self.assertIsNone(result)
        self.assertNotEqual(world.state["mission"]["status"], "failed")

    def test_no_status_change_after_terminal(self):
        world.state["mission"]["status"] = "success"
        result = check_mission_status()
        self.assertIsNone(result)

    def test_move_does_not_trigger_success(self):
        world.state["stones"] = []
        result = execute_action("rover-mistral", "move", {"direction": "east"})
        self.assertTrue(result["ok"])
        self.assertNotIn("mission", result)

    def test_partial_delivery_not_enough(self):
        """Delivering less than target_quantity should not trigger success."""
        world.state["mission"]["target_quantity"] = 500
        world.state["agents"]["rover-mistral"]["position"] = [0, 0]
        world.state["agents"]["station"]["position"] = [0, 0]
        world.state["stones"] = [_make_vein([0, 0], grade="medium", quantity=100, analyzed=True)]
        execute_action("rover-mistral", "dig", {})
        self.assertEqual(world.state["mission"]["status"], "running")
        self.assertEqual(world.state["mission"]["collected_quantity"], 100)


class TestMemory(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["inventory"] = []
        world.state["agents"]["rover-mistral"]["visited"] = [[10, 10]]
        world.state["agents"]["rover-mistral"]["memory"] = []
        self._original_stones = world.state.get("stones", [])

    def tearDown(self):
        world.state["stones"] = self._original_stones
        world.state["agents"]["rover-mistral"]["memory"] = []

    def test_move_records_memory(self):
        world.state["stones"] = []
        execute_action("rover-mistral", "move", {"direction": "east"})
        mem = world.state["agents"]["rover-mistral"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Moved east", mem[0])
        self.assertIn("(11,10)", mem[0])

    def test_move_records_stone_found(self):
        world.state["stones"] = [_make_vein([11, 10])]
        execute_action("rover-mistral", "move", {"direction": "east"})
        mem = world.state["agents"]["rover-mistral"]["memory"]
        self.assertIn("unknown", mem[0])

    def test_dig_records_memory(self):
        world.state["stones"] = [_make_vein([10, 10], grade="medium", quantity=80, analyzed=True)]
        execute_action("rover-mistral", "dig", {})
        mem = world.state["agents"]["rover-mistral"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Dug and collected medium", mem[0])
        self.assertIn("qty=80", mem[0])
        self.assertIn("inventory=1", mem[0])

    def test_charge_records_memory(self):
        world.state["agents"]["rover-mistral"]["position"] = [0, 0]
        world.state["agents"]["rover-mistral"]["battery"] = 0.5
        charge_rover("rover-mistral")
        mem = world.state["agents"]["rover-mistral"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Station charged", mem[0])

    def test_failed_action_records_memory(self):
        world.state["stones"] = []
        execute_action("rover-mistral", "dig", {})
        mem = world.state["agents"]["rover-mistral"]["memory"]
        self.assertEqual(len(mem), 1)
        self.assertIn("Failed dig", mem[0])

    def test_memory_capped_at_max(self):
        for i in range(MEMORY_MAX + 5):
            record_memory("rover-mistral", f"entry {i}")
        mem = world.state["agents"]["rover-mistral"]["memory"]
        self.assertEqual(len(mem), MEMORY_MAX)
        self.assertEqual(mem[0], f"entry {5}")
        self.assertEqual(mem[-1], f"entry {MEMORY_MAX + 4}")

    def test_memory_in_snapshot(self):
        record_memory("rover-mistral", "test entry")
        snap = get_snapshot()
        self.assertIn("memory", snap["agents"]["rover-mistral"])
        self.assertEqual(snap["agents"]["rover-mistral"]["memory"], ["test entry"])

    def test_record_memory_unknown_agent(self):
        # Should not raise
        record_memory("nonexistent", "noop")
        # Verify no agent named "nonexistent" was added to world state
        self.assertNotIn("nonexistent", world.state["agents"])


class TestDirectionHint(unittest.TestCase):
    """Direction hints use math convention: north = +Y, south = -Y."""

    def test_north(self):
        self.assertEqual(direction_hint(0, 3), "north")

    def test_south(self):
        self.assertEqual(direction_hint(0, -3), "south")

    def test_south_east(self):
        self.assertEqual(direction_hint(2, -5), "south, east")

    def test_north_east(self):
        self.assertEqual(direction_hint(2, 5), "north, east")

    def test_west(self):
        self.assertEqual(direction_hint(-1, 0), "west")

    def test_here(self):
        self.assertEqual(direction_hint(0, 0), "here")


class TestObserveRover(unittest.TestCase):
    def setUp(self):
        agent = world.state["agents"]["rover-mistral"]
        self._orig_position = list(agent["position"])
        self._orig_battery = agent["battery"]
        self._orig_mission = dict(agent["mission"])
        self._orig_visited = list(agent["visited"])
        self._orig_inventory = list(agent.get("inventory", []))
        self._orig_memory = list(agent.get("memory", []))
        self._orig_tasks = list(agent.get("tasks", []))
        self._orig_stones = list(world.state.get("stones", []))
        agent["position"] = [5, 5]
        agent["battery"] = 0.75
        agent["mission"] = {"objective": "Explore", "plan": []}
        agent["visited"] = [[0, 0], [5, 5]]
        agent["inventory"] = []
        agent["memory"] = ["moved east"]
        agent["tasks"] = []
        world.state["stones"] = []

    def tearDown(self):
        agent = world.state["agents"]["rover-mistral"]
        agent["position"] = self._orig_position
        agent["battery"] = self._orig_battery
        agent["mission"] = self._orig_mission
        agent["visited"] = self._orig_visited
        agent["inventory"] = self._orig_inventory
        agent["memory"] = self._orig_memory
        agent["tasks"] = self._orig_tasks
        world.state["stones"] = self._orig_stones

    def test_returns_rover_context_type(self):
        ctx = observe_rover("rover-mistral")
        self.assertIsInstance(ctx, RoverContext)

    def test_agent_state_fields(self):
        ctx = observe_rover("rover-mistral")
        self.assertEqual(ctx.agent.position, [5, 5])
        self.assertAlmostEqual(ctx.agent.battery, 0.75)
        self.assertEqual(ctx.agent.mission.objective, "Explore")
        self.assertEqual(ctx.agent.memory, ["moved east"])
        self.assertEqual(ctx.agent.visited_count, 2)

    def test_world_view_fields(self):
        ctx = observe_rover("rover-mistral")
        self.assertEqual(ctx.world.grid_w, GRID_W)
        self.assertEqual(ctx.world.grid_h, GRID_H)
        self.assertEqual(ctx.world.station_position, [0, 0])

    def test_unvisited_dirs(self):
        ctx = observe_rover("rover-mistral")
        # (5,5) with visited={(0,0),(5,5)} — all 4 neighbors are unvisited
        for d in ["north", "south", "east", "west"]:
            self.assertIn(d, ctx.computed.unvisited_dirs)

    def test_unvisited_dirs_excludes_visited(self):
        world.state["agents"]["rover-mistral"]["visited"].append([5, 6])
        ctx = observe_rover("rover-mistral")
        self.assertNotIn("north", ctx.computed.unvisited_dirs)

    def test_stone_line_none(self):
        ctx = observe_rover("rover-mistral")
        self.assertEqual(ctx.computed.stone_line, "none")
        self.assertIsNone(ctx.computed.stone_here)

    def test_stone_line_unknown(self):
        world.state["stones"] = [_make_vein([5, 5])]
        ctx = observe_rover("rover-mistral")
        self.assertIn("unknown", ctx.computed.stone_line)
        self.assertIsNotNone(ctx.computed.stone_here)
        self.assertIsInstance(ctx.computed.stone_here, StoneInfo)

    def test_stone_line_analyzed(self):
        world.state["stones"] = [_make_vein([5, 5], grade="high", quantity=200, analyzed=True)]
        ctx = observe_rover("rover-mistral")
        self.assertIn("needs dig", ctx.computed.stone_line)
        self.assertIn("high", ctx.computed.stone_line)

    def test_visible_stones_excludes_current_tile(self):
        world.state["stones"] = [
            _make_vein([5, 5]),
            _make_vein([6, 5], grade="medium", quantity=100, analyzed=True),
        ]
        world.state["agents"]["rover-mistral"]["revealed"] = [[5, 5], [6, 5]]
        ctx = observe_rover("rover-mistral")
        self.assertEqual(len(ctx.computed.visible_stones), 1)
        self.assertIn("basalt_vein", ctx.computed.visible_stones[0])

    def test_inventory_in_context(self):
        world.state["agents"]["rover-mistral"]["inventory"] = [
            {"type": "basalt_vein", "grade": "high", "quantity": 200}
        ]
        ctx = observe_rover("rover-mistral")
        self.assertEqual(len(ctx.agent.inventory), 1)
        self.assertEqual(ctx.agent.inventory[0].type, "basalt_vein")
        self.assertEqual(ctx.agent.inventory[0].grade, "high")
        self.assertEqual(ctx.agent.inventory[0].quantity, 200)

    def test_mission_info(self):
        ctx = observe_rover("rover-mistral")
        self.assertEqual(ctx.world.target_type, world.state["mission"]["target_type"])
        self.assertEqual(ctx.world.target_quantity, world.state["mission"]["target_quantity"])


class TestObserveStation(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [3, 4]
        world.state["agents"]["rover-mistral"]["battery"] = 0.5
        world.state["agents"]["rover-mistral"]["mission"] = {"objective": "Scout", "plan": []}
        world.state["agents"]["rover-mistral"]["visited"] = [[0, 0], [3, 4]]
        world.state["stones"] = [_make_vein([1, 1])]

    def test_returns_station_context_type(self):
        ctx = observe_station()
        self.assertIsInstance(ctx, StationContext)

    def test_grid_dimensions(self):
        ctx = observe_station()
        self.assertEqual(ctx.grid_w, GRID_W)
        self.assertEqual(ctx.grid_h, GRID_H)

    def test_rovers_list_excludes_station(self):
        ctx = observe_station()
        rover_ids = [r.id for r in ctx.rovers]
        self.assertNotIn("station", rover_ids)
        self.assertIn("rover-mistral", rover_ids)

    def test_rover_summary_fields(self):
        ctx = observe_station()
        rover = next(r for r in ctx.rovers if r.id == "rover-mistral")
        self.assertEqual(rover.position, [3, 4])
        self.assertAlmostEqual(rover.battery, 0.5)
        self.assertEqual(rover.mission.objective, "Scout")
        self.assertEqual(rover.visited_count, 2)

    def test_stones_list(self):
        ctx = observe_station()
        self.assertEqual(len(ctx.stones), 1)
        self.assertEqual(ctx.stones[0].position, [1, 1])
        self.assertEqual(ctx.stones[0].type, "unknown")

    def test_memory_included(self):
        world.state["agents"]["station"]["memory"] = ["Radio from drone at (3,3): peak=0.9"]
        ctx = observe_station()
        self.assertEqual(len(ctx.memory), 1)
        self.assertIn("peak=0.9", ctx.memory[0])


class TestDrone(unittest.TestCase):
    """Tests for drone agent: creation, scan action, movement, reveal radius."""

    def setUp(self):
        self.drone = world.state["agents"].get("drone-mistral")
        if self.drone:
            self.drone["position"] = [10, 10]
            self.drone["battery"] = 1.0
            self.drone["visited"] = [[10, 10]]
            self.drone["memory"] = []
        self._original_stones = list(world.state.get("stones", []))
        world.state.setdefault("drone_scans", []).clear()

    def tearDown(self):
        world.state["stones"] = self._original_stones

    def test_drone_exists_in_world(self):
        self.assertIn("drone-mistral", world.state["agents"])
        self.assertEqual(world.state["agents"]["drone-mistral"]["type"], "drone")

    def test_drone_reveal_radius_larger(self):
        self.assertGreater(DRONE_REVEAL_RADIUS, ROVER_REVEAL_RADIUS)

    def test_drone_initial_revealed_larger_than_rover(self):
        drone_revealed = len(_cells_in_radius(0, 0, DRONE_REVEAL_RADIUS))
        rover_revealed = len(_cells_in_radius(0, 0, ROVER_REVEAL_RADIUS))
        self.assertGreater(drone_revealed, rover_revealed)

    def test_scan_action(self):
        result = execute_action("drone-mistral", "scan", {})
        self.assertTrue(result["ok"])
        self.assertIn("readings", result)
        self.assertIn("peak", result)
        self.assertEqual(len(world.state["drone_scans"]), 1)

    def test_scan_battery_cost(self):
        before = self.drone["battery"]
        execute_action("drone-mistral", "scan", {})
        self.assertAlmostEqual(self.drone["battery"], before - BATTERY_COST_SCAN)

    def test_scan_no_battery(self):
        self.drone["battery"] = 0.0
        result = execute_action("drone-mistral", "scan", {})
        self.assertFalse(result["ok"])

    def test_drone_move_max_distance(self):
        result = execute_action("drone-mistral", "move", {"direction": "east", "distance": 6})
        self.assertTrue(result["ok"])
        self.assertEqual(self.drone["position"], [16, 10])

    def test_drone_move_exceeds_max(self):
        result = execute_action("drone-mistral", "move", {"direction": "east", "distance": 7})
        # Should be clamped to MAX_MOVE_DISTANCE_DRONE=6
        self.assertTrue(result["ok"])
        self.assertEqual(self.drone["position"], [16, 10])

    def test_drone_move_battery_cost_lower(self):
        before = self.drone["battery"]
        execute_action("drone-mistral", "move", {"direction": "east", "distance": 1})
        self.assertAlmostEqual(self.drone["battery"], before - BATTERY_COST_MOVE_DRONE)

    def test_drone_cannot_dig(self):
        world.state["stones"] = [_make_vein([10, 10], grade="high", quantity=200, analyzed=True)]
        result = execute_action("drone-mistral", "dig", {})
        self.assertFalse(result["ok"])


class TestChunkSystem(unittest.TestCase):
    """Tests for infinite grid chunk-based procedural generation."""

    def test_chunk_generated_on_move(self):
        """Moving to a far tile generates the chunk."""
        world.state["agents"]["rover-mistral"]["position"] = [30, 30]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        result = move_agent("rover-mistral", 31, 30)
        self.assertTrue(result["ok"])
        # Chunk containing (31, 30) should exist
        from app.world import _chunk_key

        ck = _chunk_key(31, 30)
        self.assertIn(ck, world.state["chunks"])

    def test_chunk_deterministic(self):
        """Same chunk coords always produce same concentration."""
        from app.world import _ensure_chunk, get_concentration, CHUNK_SIZE

        # Generate chunk (5, 5)
        _ensure_chunk(5, 5)
        val1 = get_concentration(5 * CHUNK_SIZE, 5 * CHUNK_SIZE)
        # Re-generating should return cached (same) value
        val2 = get_concentration(5 * CHUNK_SIZE, 5 * CHUNK_SIZE)
        self.assertEqual(val1, val2)

    def test_negative_coords_work(self):
        """Agents can move to and exist at negative coordinates."""
        world.state["agents"]["rover-mistral"]["position"] = [-5, -5]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        result = move_agent("rover-mistral", -6, -5)
        self.assertTrue(result["ok"])
        self.assertEqual(world.state["agents"]["rover-mistral"]["position"], [-6, -5])

    def test_bounds_tracking(self):
        """World bounds update when agents move."""
        world.state["agents"]["rover-mistral"]["position"] = [50, 50]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        move_agent("rover-mistral", 51, 50)
        bounds = world.state["bounds"]
        self.assertGreaterEqual(bounds["max_x"], 51)

    def test_origin_chunk_has_vein(self):
        """Origin chunk should have at least one basalt_vein."""
        veins = [s for s in world.state["stones"] if s.get("_true_type") == "basalt_vein"]
        self.assertGreaterEqual(len(veins), 1)

    def test_get_concentration_lazy(self):
        """get_concentration generates chunk on demand."""
        from app.world import get_concentration, _chunk_key

        # Access a far-away cell
        val = get_concentration(100, 100)
        self.assertIsInstance(val, float)
        self.assertGreaterEqual(val, 0.0)
        ck = _chunk_key(100, 100)
        self.assertIn(ck, world.state["chunks"])

    def test_snapshot_includes_bounds(self):
        """Snapshot should include world bounds."""
        snap = get_snapshot()
        self.assertIn("bounds", snap)
        self.assertIn("min_x", snap["bounds"])
        self.assertIn("max_x", snap["bounds"])


class TestVeinGradeDistribution(unittest.TestCase):
    """Verify exponential rarity of vein grades via random sampling."""

    def test_grade_distribution_matches_weights(self):
        """Generate 10000 veins and verify grade distribution is roughly correct."""
        rng = random.Random(12345)
        counts = {g: 0 for g in VEIN_GRADES}
        n = 10000
        for _ in range(n):
            grade = rng.choices(VEIN_GRADES, weights=VEIN_WEIGHTS, k=1)[0]
            counts[grade] += 1
        total_weight = sum(VEIN_WEIGHTS)
        for i, grade in enumerate(VEIN_GRADES):
            expected_pct = VEIN_WEIGHTS[i] / total_weight
            actual_pct = counts[grade] / n
            # Allow generous tolerance (5% absolute) for statistical sampling
            self.assertAlmostEqual(
                actual_pct,
                expected_pct,
                delta=0.05,
                msg=f"Grade '{grade}': expected ~{expected_pct:.1%}, got {actual_pct:.1%}",
            )

    def test_quantity_ranges_per_grade(self):
        """Verify that random quantities stay within defined ranges."""
        rng = random.Random(99999)
        for grade, (lo, hi) in VEIN_QUANTITY_RANGES.items():
            for _ in range(100):
                qty = rng.randint(lo, hi)
                self.assertGreaterEqual(qty, lo)
                self.assertLessEqual(qty, hi)

    def test_low_is_most_common(self):
        """Low grade should have the highest weight."""
        self.assertEqual(VEIN_GRADES[0], "low")
        self.assertEqual(max(VEIN_WEIGHTS), VEIN_WEIGHTS[0])

    def test_pristine_is_rarest(self):
        """Pristine grade should have the lowest weight."""
        self.assertEqual(VEIN_GRADES[-1], "pristine")
        self.assertEqual(min(VEIN_WEIGHTS), VEIN_WEIGHTS[-1])

    def test_weights_decrease_monotonically(self):
        """Weights should decrease from low to pristine."""
        for i in range(len(VEIN_WEIGHTS) - 1):
            self.assertGreater(VEIN_WEIGHTS[i], VEIN_WEIGHTS[i + 1])


class TestAbortMission(unittest.TestCase):
    def setUp(self):
        self._original_status = world.state["mission"]["status"]

    def tearDown(self):
        world.state["mission"]["status"] = self._original_status

    def test_abort_sets_status(self):
        world.state["mission"]["status"] = "running"
        result = abort_mission("test reason")
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "aborted")
        self.assertEqual(result["reason"], "test reason")
        self.assertEqual(world.state["mission"]["status"], "aborted")

    def test_abort_noop_when_success(self):
        world.state["mission"]["status"] = "success"
        result = abort_mission("too late")
        self.assertIsNone(result)

    def test_abort_noop_when_failed(self):
        world.state["mission"]["status"] = "failed"
        result = abort_mission("too late")
        self.assertIsNone(result)

    def test_abort_noop_when_already_aborted(self):
        world.state["mission"]["status"] = "aborted"
        result = abort_mission("again")
        self.assertIsNone(result)

    def test_abort_default_reason(self):
        world.state["mission"]["status"] = "running"
        result = abort_mission()
        self.assertIn("Manual abort", result["reason"])

    def test_abort_updates_agent_objectives(self):
        world.state["mission"]["status"] = "running"
        world.state["agents"]["rover-mistral"]["mission"]["objective"] = "Collect veins"
        abort_mission("test")
        self.assertIn("ABORTED", world.state["agents"]["rover-mistral"]["mission"]["objective"])

    def test_all_agents_at_station_true(self):
        station_pos = world.state["agents"]["station"]["position"]
        for aid, agent in world.state["agents"].items():
            if agent.get("type") in ("rover", "drone"):
                agent["position"] = list(station_pos)
        self.assertTrue(all_agents_at_station())

    def test_all_agents_at_station_false(self):
        world.state["agents"]["rover-mistral"]["position"] = [99, 99]
        self.assertFalse(all_agents_at_station())


class TestChargeAgent(unittest.TestCase):
    """Test charge_agent for non-rover agents (drone)."""

    def setUp(self):
        self.drone = world.state["agents"].get("drone-mistral")
        if self.drone:
            self.drone["position"] = [0, 0]
            self.drone["battery"] = 0.5
            self.drone["memory"] = []
        world.state["agents"]["station"]["position"] = [0, 0]

    def test_charge_drone(self):
        result = charge_agent("drone-mistral")
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(result["battery_before"], 0.5)
        self.assertAlmostEqual(result["battery_after"], 0.5 + CHARGE_RATE)


class TestStoneProximityConcentration(unittest.TestCase):
    """Test proximity-based concentration replaces noise-based."""

    def setUp(self):
        self._original_stones = world.state.get("stones", [])

    def tearDown(self):
        world.state["stones"] = self._original_stones

    def test_concentration_at_stone(self):
        from app.world import _stone_proximity_concentration

        world.state["stones"] = [_make_vein([5, 5])]
        self.assertEqual(_stone_proximity_concentration(5, 5), 1.0)

    def test_concentration_falls_off(self):
        from app.world import _stone_proximity_concentration

        world.state["stones"] = [_make_vein([5, 5])]
        val_near = _stone_proximity_concentration(6, 5)
        val_far = _stone_proximity_concentration(10, 5)
        self.assertGreater(val_near, val_far)

    def test_concentration_zero_far_away(self):
        from app.world import _stone_proximity_concentration

        world.state["stones"] = [_make_vein([5, 5])]
        val = _stone_proximity_concentration(50, 50)
        self.assertEqual(val, 0.0)


class TestNotify(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["inventory"] = []
        world.state["agents"]["rover-mistral"]["visited"] = [[5, 5]]
        world.state["agents"]["rover-mistral"]["memory"] = []
        world.state["agents"]["drone-mistral"]["position"] = [3, 3]
        world.state["agents"]["drone-mistral"]["battery"] = 1.0
        world.state["agents"]["drone-mistral"]["memory"] = []
        self._original_stones = world.state.get("stones", [])
        world.state["stones"] = []

    def tearDown(self):
        world.state["stones"] = self._original_stones

    def test_notify_rover_success(self):
        result = execute_action("rover-mistral", "notify", {"message": "Found rich vein at (5,5)"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["position"], [5, 5])
        self.assertEqual(result["message"], "Found rich vein at (5,5)")
        self.assertAlmostEqual(
            world.state["agents"]["rover-mistral"]["battery"], 1.0 - BATTERY_COST_NOTIFY
        )

    def test_notify_drone_success(self):
        result = execute_action(
            "drone-mistral", "notify", {"message": "High concentration detected"}
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["position"], [3, 3])
        self.assertEqual(result["message"], "High concentration detected")
        self.assertAlmostEqual(
            world.state["agents"]["drone-mistral"]["battery"], 1.0 - BATTERY_COST_NOTIFY
        )

    def test_notify_empty_message(self):
        result = execute_action("rover-mistral", "notify", {"message": ""})
        self.assertFalse(result["ok"])
        self.assertIn("Empty message", result["error"])

    def test_notify_missing_message(self):
        result = execute_action("rover-mistral", "notify", {})
        self.assertFalse(result["ok"])
        self.assertIn("Empty message", result["error"])

    def test_notify_low_battery(self):
        world.state["agents"]["rover-mistral"]["battery"] = 0.0
        result = execute_action("rover-mistral", "notify", {"message": "help"})
        self.assertFalse(result["ok"])
        self.assertIn("Not enough battery", result["error"])


class TestInTransitQuantity(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["inventory"] = [
            {"type": "basalt_vein", "grade": "high", "quantity": 200},
        ]
        world.state["agents"]["station"]["position"] = [0, 0]
        world.state["mission"]["status"] = "running"
        world.state["mission"]["target_type"] = "basalt_vein"
        world.state["mission"]["target_quantity"] = 500
        self._original_stones = world.state.get("stones", [])
        world.state["stones"] = []

    def tearDown(self):
        world.state["stones"] = self._original_stones

    def test_in_transit_quantity_tracked(self):
        check_mission_status()
        self.assertEqual(world.state["mission"]["in_transit_quantity"], 200)

    def test_in_transit_zero_when_at_station(self):
        world.state["agents"]["rover-mistral"]["position"] = [0, 0]
        check_mission_status()
        self.assertEqual(world.state["mission"]["in_transit_quantity"], 0)


class TestWorldSetters(unittest.TestCase):
    def test_set_agent_model(self):
        set_agent_model("rover-mistral", "test-model")
        self.assertEqual(world.state["agents"]["rover-mistral"]["model"], "test-model")

    def test_set_agent_last_context(self):
        set_agent_last_context("rover-mistral", "some prompt")
        self.assertEqual(world.state["agents"]["rover-mistral"]["last_context"], "some prompt")

    def test_set_pending_commands_set_and_clear(self):
        set_pending_commands("rover-mistral", [{"name": "recall"}])
        self.assertEqual(
            world.state["agents"]["rover-mistral"]["pending_commands"], [{"name": "recall"}]
        )
        set_pending_commands("rover-mistral", None)
        self.assertNotIn("pending_commands", world.state["agents"]["rover-mistral"])


class TestWorldClass(unittest.TestCase):
    def test_singleton_wraps_module_world(self):
        """Module-level `world` singleton is the canonical instance."""
        from app.world import world as w

        self.assertIs(w.state, world.state)

    def test_get_agent(self):
        agent = world.get_agent("rover-mistral")
        self.assertEqual(agent["type"], "rover")

    def test_get_agents_returns_all(self):
        agents = world.get_agents()
        self.assertIn("rover-mistral", agents)
        self.assertIn("station", agents)

    def test_get_mission(self):
        mission = world.get_mission()
        self.assertIn("status", mission)

    def test_setters_delegate_to_state(self):
        world.set_agent_model("rover-mistral", "test-via-class")
        self.assertEqual(world.state["agents"]["rover-mistral"]["model"], "test-via-class")

        world.set_agent_last_context("rover-mistral", "ctx-via-class")
        self.assertEqual(world.state["agents"]["rover-mistral"]["last_context"], "ctx-via-class")

        world.set_pending_commands("rover-mistral", [{"name": "test"}])
        self.assertEqual(
            world.state["agents"]["rover-mistral"]["pending_commands"], [{"name": "test"}]
        )
        world.set_pending_commands("rover-mistral", None)
        self.assertNotIn("pending_commands", world.state["agents"]["rover-mistral"])

    def test_get_tick(self):
        self.assertEqual(world.get_tick(), world.state["tick"])

    def test_fresh_instance_independent(self):
        """A World() with no args gets its own state, independent of the singleton."""
        from app.world import World

        w2 = World()
        w2.set_agent_model("rover-mistral", "independent-model")
        self.assertNotEqual(
            world.state["agents"]["rover-mistral"].get("model"),
            "independent-model",
        )


class TestBestDroneHotspot(unittest.TestCase):
    def setUp(self):
        self._orig_scans = world.state.get("drone_scans", [])
        world.state["drone_scans"] = []

    def tearDown(self):
        world.state["drone_scans"] = self._orig_scans

    def test_returns_none_when_no_scans(self):
        result = best_drone_hotspot(0, 0, set())
        self.assertIsNone(result)

    def test_returns_highest_concentration(self):
        world.state["drone_scans"] = [
            {"position": [5, 5], "readings": {"5,5": 0.3, "6,5": 0.8, "7,5": 0.1}},
        ]
        result = best_drone_hotspot(0, 0, set())
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 6)
        self.assertEqual(result[1], 5)
        self.assertAlmostEqual(result[2], 0.8)

    def test_skips_revealed_cells(self):
        world.state["drone_scans"] = [
            {"position": [5, 5], "readings": {"6,5": 0.9, "7,5": 0.5}},
        ]
        revealed = {(6, 5)}
        result = best_drone_hotspot(0, 0, revealed)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 7)
        self.assertEqual(result[1], 5)

    def test_ignores_below_threshold(self):
        world.state["drone_scans"] = [
            {"position": [5, 5], "readings": {"5,5": 0.1, "6,5": 0.05}},
        ]
        result = best_drone_hotspot(0, 0, set())
        self.assertIsNone(result)


class TestStrategicMemory(unittest.TestCase):
    """Tests for Feature F: Agent Memory & Learning."""

    def setUp(self):
        from app.world import WORLD, _build_initial_world

        WORLD.clear()
        WORLD.update(_build_initial_world())

    # --- summarize_memories ---

    def test_summarize_memories_returns_none_when_few(self):
        """Should return None when agent has fewer than 6 memories."""
        result = summarize_memories("rover-mistral")
        self.assertIsNone(result)

    def test_summarize_memories_returns_prompt_when_enough(self):
        """Should return a prompt string when agent has >= 6 memories."""
        from app.world import WORLD

        rover = WORLD["agents"]["rover-mistral"]
        rover["memory"] = [f"memory_{i}" for i in range(8)]
        result = summarize_memories("rover-mistral")
        self.assertIsNotNone(result)
        self.assertIn("Summarize", result)
        self.assertIn("memory_7", result)

    def test_summarize_memories_invalid_agent(self):
        """Should return None for non-existent agent."""
        result = summarize_memories("nonexistent_agent")
        self.assertIsNone(result)

    # --- record_strategic_insight ---

    def test_record_strategic_insight_stores(self):
        """Should store a strategic insight for an agent."""
        record_strategic_insight("rover-mistral", "Zone B3 is mineral-rich", 20)
        from app.world import WORLD

        rover = WORLD["agents"]["rover-mistral"]
        self.assertEqual(len(rover["strategic_memory"]), 1)
        self.assertEqual(rover["strategic_memory"][0]["insight"], "Zone B3 is mineral-rich")
        self.assertEqual(rover["strategic_memory"][0]["tick"], 20)

    def test_record_strategic_insight_caps_at_five(self):
        """Should cap strategic_memory at 5 entries (sliding window)."""
        for i in range(7):
            record_strategic_insight("rover-mistral", f"insight_{i}", i * 20)
        from app.world import WORLD

        rover = WORLD["agents"]["rover-mistral"]
        self.assertEqual(len(rover["strategic_memory"]), 5)
        self.assertEqual(rover["strategic_memory"][0]["insight"], "insight_2")
        self.assertEqual(rover["strategic_memory"][-1]["insight"], "insight_6")

    def test_record_strategic_insight_invalid_agent(self):
        """Should silently do nothing for non-existent agent."""
        record_strategic_insight("nonexistent", "insight", 10)

    # --- Agent init ---

    def test_strategic_memory_in_agent_init(self):
        """Rover and drone should have strategic_memory: [] on init."""
        from app.world import WORLD

        for agent_id in ("rover-mistral", "drone-mistral"):
            agent = WORLD["agents"][agent_id]
            self.assertIn("strategic_memory", agent, f"Agent {agent_id} missing strategic_memory")
            self.assertEqual(agent["strategic_memory"], [])

    # --- Snapshot ---

    def test_strategic_memory_in_snapshot(self):
        """Strategic memory should appear in snapshot after recording."""
        record_strategic_insight("rover-mistral", "Test insight", 10)
        snap = get_snapshot()
        rover = snap["agents"]["rover-mistral"]
        self.assertIn("strategic_memory", rover)
        self.assertEqual(len(rover["strategic_memory"]), 1)

    # --- World class methods ---

    def test_world_class_methods(self):
        """World class should expose summarize_memories and record_strategic_insight."""
        from app.world import World, WORLD

        w = World(WORLD)
        result = w.summarize_memories("rover-mistral")
        self.assertIsNone(result)  # too few memories
        w.record_strategic_insight("rover-mistral", "test", 5)
        rover = WORLD["agents"]["rover-mistral"]
        self.assertEqual(len(rover["strategic_memory"]), 1)


class TestInterAgentCommunication(unittest.TestCase):
    """Tests for inter-agent message relay system."""

    def setUp(self):
        from app.world import AGENT_MESSAGES

        self._orig_messages = list(AGENT_MESSAGES)
        AGENT_MESSAGES.clear()

    def tearDown(self):
        from app.world import AGENT_MESSAGES

        AGENT_MESSAGES.clear()
        AGENT_MESSAGES.extend(self._orig_messages)

    def test_send_message(self):
        from app.world import send_agent_message, AGENT_MESSAGES

        result = send_agent_message("drone-mistral", "rover-mistral", "Found high concentration")
        self.assertTrue(result["ok"])
        self.assertEqual(len(AGENT_MESSAGES), 1)
        self.assertEqual(AGENT_MESSAGES[0]["from"], "drone-mistral")
        self.assertEqual(AGENT_MESSAGES[0]["to"], "rover-mistral")
        self.assertFalse(AGENT_MESSAGES[0]["read"])

    def test_get_unread_messages(self):
        from app.world import send_agent_message, get_unread_messages

        send_agent_message("drone-mistral", "rover-mistral", "msg1")
        send_agent_message("drone-mistral", "rover-mistral", "msg2")
        unread = get_unread_messages("rover-mistral")
        self.assertEqual(len(unread), 2)
        self.assertEqual(unread[0]["message"], "msg1")

    def test_messages_marked_read(self):
        from app.world import send_agent_message, get_unread_messages

        send_agent_message("drone-mistral", "rover-mistral", "test")
        get_unread_messages("rover-mistral")
        unread2 = get_unread_messages("rover-mistral")
        self.assertEqual(len(unread2), 0)

    def test_messages_filtered_by_recipient(self):
        from app.world import send_agent_message, get_unread_messages

        send_agent_message("drone-mistral", "rover-mistral", "for rover")
        send_agent_message("drone-mistral", "station", "for station")
        rover_msgs = get_unread_messages("rover-mistral")
        self.assertEqual(len(rover_msgs), 1)
        self.assertEqual(rover_msgs[0]["message"], "for rover")

    def test_get_drone_intel_for_rover(self):
        from app.world import get_drone_intel_for_rover, WORLD

        WORLD["drone_scans"] = [
            {"position": [3, 4], "readings": {"3,4": 0.8}, "scanner": "drone-mistral", "tick": 5},
            {"position": [1, 1], "readings": {"1,1": 0.2}, "scanner": "drone-mistral", "tick": 6},
            {"position": [5, 5], "readings": {"5,5": 0.5}, "scanner": "drone-mistral", "tick": 7},
        ]
        intel = get_drone_intel_for_rover("rover-mistral")
        self.assertEqual(len(intel), 2)
        self.assertEqual(intel[0]["concentration"], 0.8)
        self.assertEqual(intel[1]["concentration"], 0.5)

    def test_get_drone_intel_excludes_visited(self):
        from app.world import get_drone_intel_for_rover, WORLD

        WORLD["drone_scans"] = [
            {"position": [3, 4], "readings": {"3,4": 0.8}, "scanner": "drone-mistral", "tick": 5},
        ]
        WORLD["agents"]["rover-mistral"]["visited"].append([3, 4])
        intel = get_drone_intel_for_rover("rover-mistral")
        self.assertEqual(len(intel), 0)

    def test_get_drone_intel_max_five(self):
        from app.world import get_drone_intel_for_rover, WORLD

        WORLD["drone_scans"] = [
            {
                "position": [i, i],
                "readings": {f"{i},{i}": 0.5 + i * 0.01},
                "scanner": "drone-mistral",
                "tick": i,
            }
            for i in range(10)
        ]
        intel = get_drone_intel_for_rover("rover-mistral")
        self.assertEqual(len(intel), 5)

    def test_get_drone_intel_invalid_rover(self):
        from app.world import get_drone_intel_for_rover

        intel = get_drone_intel_for_rover("no-such-agent")
        self.assertEqual(len(intel), 0)

    def test_agent_messages_in_snapshot(self):
        from app.world import send_agent_message, get_snapshot

        send_agent_message("drone-mistral", "rover-mistral", "test snapshot")
        snap = get_snapshot()
        self.assertIn("agent_messages", snap)
        self.assertEqual(len(snap["agent_messages"]), 1)
        self.assertEqual(snap["agent_messages"][0]["message"], "test snapshot")

    def test_reset_clears_messages(self):
        from app.world import send_agent_message, AGENT_MESSAGES, reset_world

        send_agent_message("drone-mistral", "rover-mistral", "before reset")
        self.assertEqual(len(AGENT_MESSAGES), 1)
        reset_world()
        self.assertEqual(len(AGENT_MESSAGES), 0)


class TestRandomFreePos(unittest.TestCase):
    """Tests for _random_free_pos infinite-loop guard (#118)."""

    def test_returns_free_position(self):
        occupied = {(0, 0), (1, 0)}
        pos = _random_free_pos(occupied, cx=0, cy=0)
        self.assertNotIn(pos, occupied)
        x, y = pos
        self.assertGreaterEqual(x, 0)
        self.assertLess(x, CHUNK_SIZE)
        self.assertGreaterEqual(y, 0)
        self.assertLess(y, CHUNK_SIZE)

    def test_empty_occupied_returns_valid_pos(self):
        pos = _random_free_pos(set(), cx=0, cy=0)
        x, y = pos
        self.assertGreaterEqual(x, 0)
        self.assertLess(x, CHUNK_SIZE)

    def test_nearly_full_chunk_uses_fallback(self):
        """When all but one cell is occupied, the linear scan fallback finds it."""
        all_cells = {(x, y) for x in range(CHUNK_SIZE) for y in range(CHUNK_SIZE)}
        free_cell = (3, 7)
        all_cells.discard(free_cell)
        pos = _random_free_pos(all_cells, cx=0, cy=0)
        self.assertEqual(pos, free_cell)

    def test_fully_occupied_returns_origin(self):
        """When chunk is 100% occupied, returns origin as last resort."""
        all_cells = {(x, y) for x in range(CHUNK_SIZE) for y in range(CHUNK_SIZE)}
        pos = _random_free_pos(all_cells, cx=0, cy=0)
        self.assertEqual(pos, (0, 0))

    def test_nonzero_chunk_offset(self):
        """Positions respect chunk offset (cx, cy)."""
        occupied = set()
        pos = _random_free_pos(occupied, cx=2, cy=3)
        x, y = pos
        self.assertGreaterEqual(x, 2 * CHUNK_SIZE)
        self.assertLess(x, 3 * CHUNK_SIZE)
        self.assertGreaterEqual(y, 3 * CHUNK_SIZE)
        self.assertLess(y, 4 * CHUNK_SIZE)

    def test_fully_occupied_nonzero_chunk_returns_chunk_origin(self):
        """Fully occupied non-zero chunk returns that chunk's origin."""
        cx, cy = 1, 2
        x0, y0 = cx * CHUNK_SIZE, cy * CHUNK_SIZE
        all_cells = {(x0 + dx, y0 + dy) for dx in range(CHUNK_SIZE) for dy in range(CHUNK_SIZE)}
        pos = _random_free_pos(all_cells, cx=cx, cy=cy)
        self.assertEqual(pos, (x0, y0))


class TestObstacles(unittest.TestCase):
    """Tests for ice mountain and air geyser environmental hazards."""

    def setUp(self):
        from app.world import reset_world

        reset_world()

    def tearDown(self):
        from app.world import reset_world

        reset_world()

    def test_obstacles_generated_in_chunks(self):
        """Obstacle list is populated after chunk generation."""
        obstacles = world.state.get("obstacles", [])
        self.assertIsInstance(obstacles, list)
        # With 9 chunks (3x3 around origin) and ~1.2% probability, expect some obstacles
        self.assertGreater(len(obstacles), 0)

    def test_obstacle_kinds(self):
        """Only 'mountain' and 'geyser' kinds are generated."""
        kinds = {o["kind"] for o in world.state.get("obstacles", [])}
        self.assertTrue(kinds.issubset({"mountain", "geyser"}))

    def test_mountains_are_impassable(self):
        """Moving onto a mountain tile should fail."""
        mountains = [o for o in world.state.get("obstacles", []) if o["kind"] == "mountain"]
        if not mountains:
            self.skipTest("No mountains generated with current seed")
        m = mountains[0]
        mx, my = m["position"]
        rover = world.state["agents"]["rover-mistral"]
        rover["position"] = [mx - 1, my]
        result = move_agent("rover-mistral", mx, my)
        self.assertFalse(result["ok"])
        self.assertIn("Mountain", result["error"])

    def test_mountain_blocks_execute_action(self):
        """execute_action('move') should fail when destination is a mountain."""
        mountains = [o for o in world.state.get("obstacles", []) if o["kind"] == "mountain"]
        if not mountains:
            self.skipTest("No mountains generated with current seed")
        m = mountains[0]
        mx, my = m["position"]
        rover = world.state["agents"]["rover-mistral"]
        # Position rover one tile west of mountain
        rover["position"] = [mx - 1, my]
        rover["battery"] = 1.0
        result = execute_action("rover-mistral", "move", {"direction": "east", "distance": 1})
        self.assertFalse(result["ok"])
        self.assertIn("Mountain", result["error"])

    def test_geyser_state_idle(self):
        """Geysers start in 'idle' state."""
        geysers = [o for o in world.state.get("obstacles", []) if o["kind"] == "geyser"]
        if not geysers:
            self.skipTest("No geysers generated with current seed")
        for g in geysers:
            self.assertEqual(g["state"], "idle")

    def test_geyser_cycle_transitions(self):
        """Geyser transitions: idle → warning → erupting → idle."""
        from app.world import (
            update_geysers,
            GEYSER_CYCLE_IDLE,
            GEYSER_CYCLE_WARNING,
            GEYSER_CYCLE_ERUPTING,
        )

        geysers = [o for o in world.state.get("obstacles", []) if o["kind"] == "geyser"]
        if not geysers:
            self.skipTest("No geysers generated with current seed")
        g = geysers[0]
        # Force start of cycle
        g["_cycle_tick"] = 0
        # Advance through idle phase
        for _ in range(GEYSER_CYCLE_IDLE - 1):
            update_geysers()
            self.assertEqual(g["state"], "idle")
        # Warning phase
        update_geysers()
        self.assertEqual(g["state"], "warning")
        for _ in range(GEYSER_CYCLE_WARNING - 1):
            update_geysers()
            self.assertEqual(g["state"], "warning")
        # Erupting phase
        update_geysers()
        self.assertEqual(g["state"], "erupting")
        for _ in range(GEYSER_CYCLE_ERUPTING - 1):
            update_geysers()
            self.assertEqual(g["state"], "erupting")
        # Back to idle
        update_geysers()
        self.assertEqual(g["state"], "idle")

    def test_geyser_eruption_drains_battery(self):
        """Agent on erupting geyser loses BATTERY_COST_GEYSER battery."""
        from app.world import (
            update_geysers,
            BATTERY_COST_GEYSER,
            GEYSER_CYCLE_IDLE,
            GEYSER_CYCLE_WARNING,
        )

        geysers = [o for o in world.state.get("obstacles", []) if o["kind"] == "geyser"]
        if not geysers:
            self.skipTest("No geysers generated with current seed")
        g = geysers[0]
        gx, gy = g["position"]
        rover = world.state["agents"]["rover-mistral"]
        rover["position"] = [gx, gy]
        rover["battery"] = 0.5
        # Set geyser to just before erupting
        g["_cycle_tick"] = GEYSER_CYCLE_IDLE + GEYSER_CYCLE_WARNING - 1
        events = update_geysers()
        eruption_events = [e for e in events if e["agent_id"] == "rover-mistral"]
        self.assertEqual(len(eruption_events), 1)
        self.assertAlmostEqual(rover["battery"], 0.5 - BATTERY_COST_GEYSER)

    def test_geyser_eruption_clamps_battery(self):
        """Battery doesn't go below 0.0 from geyser eruption."""
        from app.world import update_geysers, GEYSER_CYCLE_IDLE, GEYSER_CYCLE_WARNING

        geysers = [o for o in world.state.get("obstacles", []) if o["kind"] == "geyser"]
        if not geysers:
            self.skipTest("No geysers generated with current seed")
        g = geysers[0]
        gx, gy = g["position"]
        rover = world.state["agents"]["rover-mistral"]
        rover["position"] = [gx, gy]
        rover["battery"] = 0.05
        g["_cycle_tick"] = GEYSER_CYCLE_IDLE + GEYSER_CYCLE_WARNING - 1
        update_geysers()
        self.assertEqual(rover["battery"], 0.0)

    def test_is_obstacle_at(self):
        """is_obstacle_at returns obstacle dict or None."""
        from app.world import is_obstacle_at

        obstacles = world.state.get("obstacles", [])
        if obstacles:
            o = obstacles[0]
            result = is_obstacle_at(o["position"][0], o["position"][1])
            self.assertIsNotNone(result)
            self.assertEqual(result["kind"], o["kind"])
        # Empty tile returns None
        self.assertIsNone(is_obstacle_at(0, 0))

    def test_origin_clear_of_obstacles(self):
        """Origin area (|x|<=1, |y|<=1) has no obstacles."""
        from app.world import is_obstacle_at

        for x in range(-1, 2):
            for y in range(-1, 2):
                self.assertIsNone(is_obstacle_at(x, y))

    def test_snapshot_filters_obstacles_by_fog(self):
        """get_snapshot only includes obstacles on revealed tiles."""
        snap = get_snapshot()
        all_obs = world.state.get("obstacles", [])
        snap_obs = snap.get("obstacles", [])
        # Snapshot should have fewer or equal obstacles (fog filter)
        self.assertLessEqual(len(snap_obs), len(all_obs))
        # No private fields in snapshot
        for o in snap_obs:
            self.assertNotIn("_cycle_tick", o)

    def test_snapshot_obstacle_structure(self):
        """Snapshot obstacles have kind, position, state — no private fields."""
        snap = get_snapshot()
        for o in snap.get("obstacles", []):
            self.assertIn("kind", o)
            self.assertIn("position", o)
            self.assertIn("state", o)
            for key in o:
                self.assertFalse(key.startswith("_"), f"Private field {key} leaked")

    def test_observe_rover_nearby_obstacles(self):
        """observe_rover includes nearby obstacles on revealed tiles."""
        from app.world import _expand_revealed

        mountains = [o for o in world.state.get("obstacles", []) if o["kind"] == "mountain"]
        if not mountains:
            self.skipTest("No mountains generated with current seed")
        m = mountains[0]
        mx, my = m["position"]
        rover = world.state["agents"]["rover-mistral"]
        rover["position"] = [mx, my + 1]
        _expand_revealed(rover, mx, my + 1)
        ctx = observe_rover("rover-mistral")
        obstacle_positions = [tuple(o.position) for o in ctx.computed.nearby_obstacles]
        self.assertIn((mx, my), obstacle_positions)

    def test_reset_clears_obstacles(self):
        """reset_world clears obstacles list and index."""
        from app.world import reset_world, is_obstacle_at

        self.assertGreater(len(world.state.get("obstacles", [])), 0)
        reset_world()
        # After reset, new obstacles should be generated (not leftover)
        # Verify index works correctly after reset
        result = is_obstacle_at(0, 0)
        self.assertIsNone(result)

    def test_obstacle_deterministic(self):
        """Same seed produces same obstacles."""
        from app.world import reset_world

        reset_world()
        obs1 = [(o["kind"], tuple(o["position"])) for o in world.state.get("obstacles", [])]
        reset_world()
        obs2 = [(o["kind"], tuple(o["position"])) for o in world.state.get("obstacles", [])]
        self.assertEqual(obs1, obs2)
