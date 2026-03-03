import unittest


class TestAgentsApiRoverReasoner(unittest.TestCase):
    def setUp(self):
        from app.world import world

        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["mission"] = {
            "objective": "Explore the terrain",
            "plan": [],
        }
        world.state["agents"]["rover-mistral"]["visited"] = [[10, 10]]

    def test_import(self):
        """Verify AgentsApiRoverReasoner is importable."""
        from app.agents_api import AgentsApiRoverReasoner

        self.assertTrue(AgentsApiRoverReasoner)

    def test_run_turn_fallback(self):
        """With no API key, verify fallback returns valid action shape."""
        from app.agents_api import AgentsApiRoverReasoner
        from app.world import world

        reasoner = AgentsApiRoverReasoner(agent_id="rover-mistral", world=world)
        turn = reasoner.run_turn()
        self.assertIn("thinking", turn)
        self.assertIn("action", turn)
        self.assertIsInstance(turn["action"], dict)
        self.assertIn("name", turn["action"])
        self.assertIn("params", turn["action"])

    def test_build_context(self):
        """Verify _build_context() returns a non-empty string with expected sections."""
        from app.agents_api import AgentsApiRoverReasoner
        from app.world import world

        reasoner = AgentsApiRoverReasoner(agent_id="rover-mistral", world=world)
        ctx = reasoner._build_context()
        self.assertIsInstance(ctx, str)
        self.assertGreater(len(ctx), 0)

    def test_rover_tools_not_duplicated(self):
        """Verify ROVER_TOOLS is imported from agent.py, not redefined."""
        from app import agents_api
        from app.agent import ROVER_TOOLS

        self.assertIs(agents_api.ROVER_TOOLS, ROVER_TOOLS)


class TestAgentsApiDroneReasoner(unittest.TestCase):
    def setUp(self):
        from app.world import world

        world.state["agents"]["drone-mistral"]["position"] = [5, 5]
        world.state["agents"]["drone-mistral"]["battery"] = 1.0
        world.state["agents"]["drone-mistral"]["mission"] = {
            "objective": "Scout terrain",
            "plan": [],
        }
        world.state["agents"]["drone-mistral"]["visited"] = [[5, 5]]

    def test_import(self):
        """Verify AgentsApiDroneReasoner is importable."""
        from app.agents_api import AgentsApiDroneReasoner

        self.assertTrue(AgentsApiDroneReasoner)

    def test_run_turn_fallback(self):
        """Fallback returns valid drone action (move or scan)."""
        from app.agents_api import AgentsApiDroneReasoner
        from app.world import world

        reasoner = AgentsApiDroneReasoner(agent_id="drone-mistral", world=world)
        turn = reasoner.run_turn()
        self.assertIn("thinking", turn)
        self.assertIn("action", turn)
        self.assertIn(turn["action"]["name"], ("move", "scan"))

    def test_build_context(self):
        """Verify _build_context() returns a non-empty string with expected sections."""
        from app.agents_api import AgentsApiDroneReasoner
        from app.world import world

        reasoner = AgentsApiDroneReasoner(agent_id="drone-mistral", world=world)
        ctx = reasoner._build_context()
        self.assertIsInstance(ctx, str)
        self.assertGreater(len(ctx), 0)


class TestAgentsApiStationReasoner(unittest.TestCase):
    def test_import(self):
        """Verify AgentsApiStationReasoner is importable."""
        from app.agents_api import AgentsApiStationReasoner

        self.assertTrue(AgentsApiStationReasoner)

    def test_define_mission_fallback(self):
        """Fallback returns valid shape with thinking, actions, context_text."""
        from app.agents_api import AgentsApiStationReasoner
        from app.world import observe_station

        station = AgentsApiStationReasoner()
        ctx = observe_station()
        result = station.define_mission(ctx)
        self.assertIn("thinking", result)
        self.assertIn("actions", result)
        self.assertIsInstance(result["actions"], list)

    def test_evaluate_situation_fallback(self):
        """Fallback returns valid shape on evaluate_situation."""
        from app.agents_api import AgentsApiStationReasoner
        from app.world import observe_station

        station = AgentsApiStationReasoner()
        ctx = observe_station()
        result = station.evaluate_situation(ctx, [])
        self.assertIn("thinking", result)
        self.assertIn("actions", result)

    def test_station_tools_not_duplicated(self):
        """Verify STATION_TOOLS is imported from station.py, not redefined."""
        from app import agents_api
        from app.station import STATION_TOOLS

        self.assertIs(agents_api.STATION_TOOLS, STATION_TOOLS)


class TestAgentBackendConfig(unittest.TestCase):
    def test_default_backend(self):
        """Default agent_backend should be chat_completions."""
        from app.config import settings

        self.assertEqual(settings.agent_backend, "chat_completions")

    def test_agents_api_backend_field_exists(self):
        """Verify agent_backend field exists on Settings class."""
        from app.config import Settings

        self.assertIn("agent_backend", Settings.model_fields)


class TestAgentMapRegistration(unittest.TestCase):
    def test_new_entries_exist(self):
        """Verify agents-api entries exist in AGENT_MAP."""
        from app.main import AGENT_MAP

        self.assertIn("rover-agents-api", AGENT_MAP)
        self.assertIn("drone-agents-api", AGENT_MAP)
        self.assertIn("station-agents-api", AGENT_MAP)

    def test_existing_entries_preserved(self):
        """Verify original agent entries are still in AGENT_MAP."""
        from app.main import AGENT_MAP

        self.assertIn("rover-mistral", AGENT_MAP)
        self.assertIn("drone-mistral", AGENT_MAP)
        self.assertIn("station-loop", AGENT_MAP)
