import json
import unittest

from app.sim.models import world_to_dict
from app.sim.world_factory import WorldFactory


class TestSimGeneration(unittest.TestCase):

    def test_seeded_generation_is_deterministic(self):
        factory = WorldFactory()
        w1 = factory.create(seed=42)
        w2 = factory.create(seed=42)

        self.assertEqual(world_to_dict(w1), world_to_dict(w2))

    def test_generation_guarantees_target_stones(self):
        factory = WorldFactory(target_count=2)
        world = factory.create(seed=7)

        precious = 0
        for row in world.grid.cells:
            for cell in row:
                if cell.stone is not None and cell.stone.kind == "precious":
                    precious += 1

        self.assertGreaterEqual(precious, 2)

    def test_different_seeds_change_layout(self):
        factory = WorldFactory()
        w1 = world_to_dict(factory.create(seed=1))
        w2 = world_to_dict(factory.create(seed=2))

        self.assertNotEqual(json.dumps(w1, sort_keys=True), json.dumps(w2, sort_keys=True))

    def test_initial_fog_of_war_reveal_radius(self):
        factory = WorldFactory()
        world = factory.create(seed=5)

        self.assertIn((0, 0), world.rover.revealed_cells)
        self.assertIn((2, 0), world.rover.revealed_cells)
        self.assertIn((1, 1), world.rover.revealed_cells)
        self.assertNotIn((3, 0), world.rover.revealed_cells)
        self.assertNotIn((2, 1), world.rover.revealed_cells)
