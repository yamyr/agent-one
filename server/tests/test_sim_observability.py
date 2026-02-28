import unittest

from app.sim.engine import SimulationEngine
from app.sim.models import Stone
from app.sim.world_factory import WorldFactory


class TestSimObservability(unittest.TestCase):

    def setUp(self):
        world = WorldFactory().create(seed=10)
        # Force a known far stone outside initial reveal radius.
        world.grid.cells[11][11].stone = Stone(kind="precious", extracted=False)
        self.engine = SimulationEngine(world)

    def test_rover_observation_only_contains_revealed_cells(self):
        obs = self.engine.get_observation("rover")

        known_coords = {tuple(cell["coord"]) for cell in obs.known_cells}
        self.assertIn((0, 0), known_coords)
        self.assertNotIn((11, 11), known_coords)

    def test_station_observation_tracks_rover_discovered_map(self):
        rover_obs = self.engine.get_observation("rover")
        station_obs = self.engine.get_observation("station")

        rover_coords = {tuple(cell["coord"]) for cell in rover_obs.known_cells}
        station_coords = {tuple(cell["coord"]) for cell in station_obs.known_cells}
        self.assertEqual(rover_coords, station_coords)

    def test_revealed_cells_expand_after_move(self):
        before = self.engine.get_observation("rover")
        before_coords = {tuple(cell["coord"]) for cell in before.known_cells}

        result = self.engine.step({"kind": "move", "to": (1, 0)})
        self.assertTrue(result.accepted)

        after = self.engine.get_observation("rover")
        after_coords = {tuple(cell["coord"]) for cell in after.known_cells}
        self.assertGreater(len(after_coords), len(before_coords))
        self.assertIn((3, 0), after_coords)
