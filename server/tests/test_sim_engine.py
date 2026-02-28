import unittest

from app.sim.engine import SimulationEngine
from app.sim.models import Stone
from app.sim.world_factory import WorldFactory


class TestSimEngine(unittest.TestCase):

    def setUp(self):
        self.world = WorldFactory().create(seed=3)
        # Reset stones for deterministic behavior per test.
        for row in self.world.grid.cells:
            for cell in row:
                cell.stone = None
                cell.dug = False
        self.world.rover.inventory.clear()
        self.world.rover.dug_cells.clear()
        self.world.mission.collected_count = 0

    def test_move_updates_position_and_battery(self):
        engine = SimulationEngine(self.world)
        result = engine.step({"kind": "move", "to": (1, 0)})

        self.assertTrue(result.accepted)
        state = engine.get_world_state()
        self.assertEqual(state.rover.position, (1, 0))
        self.assertEqual(state.rover.battery, 99)

    def test_invalid_non_adjacent_move_does_not_mutate_or_advance_tick(self):
        engine = SimulationEngine(self.world)
        result = engine.step({"kind": "move", "to": (2, 0)})

        self.assertFalse(result.accepted)
        self.assertEqual(result.tick, 0)
        self.assertEqual(engine.get_world_state().rover.position, (0, 0))
        self.assertEqual(engine.get_world_state().tick, 0)

    def test_dig_and_pickup_change_cell_and_inventory(self):
        self.world.grid.cells[0][0].stone = Stone(kind="precious", extracted=False)
        engine = SimulationEngine(self.world)

        dig = engine.step({"kind": "dig"})
        self.assertTrue(dig.accepted)
        state_after_dig = engine.get_world_state()
        self.assertTrue(state_after_dig.grid.cells[0][0].dug)
        self.assertTrue(state_after_dig.grid.cells[0][0].stone.extracted)

        pickup = engine.step({"kind": "pickup"})
        self.assertTrue(pickup.accepted)
        state_after_pickup = engine.get_world_state()
        self.assertEqual(len(state_after_pickup.rover.inventory), 1)
        self.assertIsNone(state_after_pickup.grid.cells[0][0].stone)

    def test_charge_only_works_at_station(self):
        engine = SimulationEngine(self.world)
        engine.step({"kind": "move", "to": (1, 0)})

        result = engine.step({"kind": "charge"})
        self.assertFalse(result.accepted)

    def test_success_when_collecting_two_precious_stones(self):
        self.world.grid.cells[0][1].stone = Stone(kind="precious", extracted=False)
        self.world.grid.cells[0][2].stone = Stone(kind="precious", extracted=False)
        engine = SimulationEngine(self.world)

        steps = [
            {"kind": "move", "to": (1, 0)},
            {"kind": "dig"},
            {"kind": "pickup"},
            {"kind": "move", "to": (2, 0)},
            {"kind": "dig"},
            {"kind": "pickup"},
        ]
        last = None
        for action in steps:
            last = engine.step(action)
            self.assertTrue(last.accepted)

        self.assertEqual(engine.get_world_state().status, "success")
        self.assertEqual(engine.get_world_state().mission.collected_count, 2)
        self.assertEqual(last.terminal_status, "success")

    def test_failure_when_battery_depletes_away_from_station(self):
        self.world.rover.battery = 1
        engine = SimulationEngine(self.world)

        result = engine.step({"kind": "move", "to": (1, 0)})
        self.assertTrue(result.accepted)
        self.assertEqual(engine.get_world_state().status, "failed")
        self.assertEqual(result.terminal_status, "failed")

    def test_failure_on_timeout(self):
        engine = SimulationEngine(self.world, step_limit=2)

        first = engine.step({"kind": "wait"})
        self.assertTrue(first.accepted)
        self.assertEqual(engine.get_world_state().status, "running")

        second = engine.step({"kind": "wait"})
        self.assertTrue(second.accepted)
        self.assertEqual(engine.get_world_state().status, "failed")
        reasons = [
            event.payload.get("reason")
            for event in second.events
            if event.name == "mission_failed"
        ]
        self.assertIn("timeout", reasons)

    def test_terminal_world_rejects_further_actions(self):
        self.world.rover.battery = 1
        engine = SimulationEngine(self.world)
        engine.step({"kind": "move", "to": (1, 0)})

        follow_up = engine.step({"kind": "wait"})
        self.assertFalse(follow_up.accepted)
        names = [event.name for event in follow_up.events]
        self.assertIn("terminal_world", names)
