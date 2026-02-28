"""Tests for MockSimAgent wrapper."""
import unittest

from app.sim_agent import MockSimAgent


class TestMockSimAgent(unittest.TestCase):
    """Verify MockSimAgent instantiation and run_turn protocol."""

    def test_instantiation(self):
        agent = MockSimAgent(seed=42)
        self.assertFalse(agent.is_terminal())

    def test_get_observation_shape(self):
        agent = MockSimAgent(seed=42)
        obs = agent.get_observation()
        self.assertIsInstance(obs, dict)
        for key in ("tick", "status", "mission", "rover", "station", "known_cells"):
            self.assertIn(key, obs, f"Missing key: {key}")
        self.assertIsInstance(obs["known_cells"], list)
        self.assertIsInstance(obs["rover"], dict)
        self.assertIn("position", obs["rover"])
        self.assertIn("battery", obs["rover"])

    def test_run_turn_returns_step_and_obs(self):
        agent = MockSimAgent(seed=42)
        step_result, observation = agent.run_turn()
        self.assertIsInstance(step_result, dict)
        self.assertIsInstance(observation, dict)
        # step_result keys
        for key in ("tick", "accepted", "action", "events", "terminal_status"):
            self.assertIn(key, step_result, f"Missing step key: {key}")
        # observation keys
        for key in ("tick", "status", "mission", "rover", "station", "known_cells"):
            self.assertIn(key, observation, f"Missing obs key: {key}")

    def test_multiple_turns(self):
        agent = MockSimAgent(seed=42)
        for _ in range(10):
            step_result, obs = agent.run_turn()
            self.assertIsInstance(step_result["tick"], int)
            self.assertIn(step_result["terminal_status"], ("running", "success", "failed"))

    def test_serialization_json_safe(self):
        """Ensure no tuples or sets in serialized output."""
        agent = MockSimAgent(seed=42)
        obs = agent.get_observation()
        # known_cells coords should be lists not tuples
        for cell in obs["known_cells"]:
            self.assertIsInstance(cell["coord"], list)
        # rover position should be a list
        self.assertIsInstance(obs["rover"]["position"], list)

    def test_terminal_handling(self):
        """Run until terminal and verify graceful handling."""
        agent = MockSimAgent(seed=99)
        turns = 0
        while not agent.is_terminal() and turns < 500:
            step_result, _ = agent.run_turn()
            turns += 1
        # After reaching terminal (or max turns), run_turn should still work
        step_result, obs = agent.run_turn()
        self.assertIsInstance(step_result, dict)
        self.assertIsInstance(obs, dict)


if __name__ == "__main__":
    unittest.main()
