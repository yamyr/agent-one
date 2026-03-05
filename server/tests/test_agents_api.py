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


class TestConversationThreadPersistence(unittest.TestCase):
    """Tests for persistent conversation threads (US1)."""

    def setUp(self):
        from app.world import world

        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["mission"] = {
            "objective": "Explore the terrain",
            "plan": [],
        }
        world.state["agents"]["rover-mistral"]["visited"] = [[10, 10]]
        world.state["agents"]["drone-mistral"]["position"] = [5, 5]
        world.state["agents"]["drone-mistral"]["battery"] = 1.0
        world.state["agents"]["drone-mistral"]["mission"] = {
            "objective": "Scout terrain",
            "plan": [],
        }
        world.state["agents"]["drone-mistral"]["visited"] = [[5, 5]]

    def test_rover_conversation_id_initially_none(self):
        """Rover reasoner starts with no conversation thread."""
        from app.agents_api import AgentsApiRoverReasoner
        from app.world import world

        reasoner = AgentsApiRoverReasoner(agent_id="rover-mistral", world=world)
        self.assertIsNone(reasoner._conversation_id)

    def test_drone_conversation_id_initially_none(self):
        """Drone reasoner starts with no conversation thread."""
        from app.agents_api import AgentsApiDroneReasoner
        from app.world import world

        reasoner = AgentsApiDroneReasoner(agent_id="drone-mistral", world=world)
        self.assertIsNone(reasoner._conversation_id)

    def test_station_conversation_id_initially_none(self):
        """Station reasoner starts with no conversation thread."""
        from app.agents_api import AgentsApiStationReasoner

        reasoner = AgentsApiStationReasoner()
        self.assertIsNone(reasoner._conversation_id)

    def test_conversation_id_cleared_on_new_instance(self):
        """Creating a new reasoner instance gives a fresh conversation_id (None)."""
        from app.agents_api import AgentsApiRoverReasoner
        from app.world import world

        r1 = AgentsApiRoverReasoner(agent_id="rover-mistral", world=world)
        r1._conversation_id = "test-conv-123"
        r2 = AgentsApiRoverReasoner(agent_id="rover-mistral", world=world)
        self.assertIsNone(r2._conversation_id)

    def test_rover_conversation_thread_persists(self):
        """Verify rover stores conversation_id after first turn (mocked)."""
        from unittest.mock import MagicMock
        from app.agents_api import AgentsApiRoverReasoner
        from app.world import world

        reasoner = AgentsApiRoverReasoner(agent_id="rover-mistral", world=world)

        # Create a mock response with conversation_id and valid outputs
        mock_output = MagicMock()
        mock_output.tool_name = "move"
        mock_output.arguments = '{"direction": "north"}'
        del mock_output.content  # No content attr => it's a FunctionCallEntry

        mock_response = MagicMock()
        mock_response.conversation_id = "conv-rover-001"
        mock_response.outputs = [mock_output]

        mock_client = MagicMock()
        mock_client.beta.conversations.start.return_value = mock_response
        mock_client.beta.conversations.append.return_value = mock_response
        mock_client.beta.agents.create.return_value = MagicMock(id="agent-id-123")

        reasoner._client = mock_client
        reasoner._mistral_agent_id = "agent-id-123"

        # First turn should call start() and store conversation_id
        reasoner.run_turn()
        mock_client.beta.conversations.start.assert_called_once()
        self.assertEqual(reasoner._conversation_id, "conv-rover-001")

        # Second turn should call append() with the stored conversation_id
        mock_client.beta.conversations.start.reset_mock()
        reasoner.run_turn()
        mock_client.beta.conversations.append.assert_called_once()
        call_kwargs = mock_client.beta.conversations.append.call_args
        self.assertEqual(
            call_kwargs.kwargs.get("conversation_id")
            or call_kwargs[1].get("conversation_id", call_kwargs[0][0] if call_kwargs[0] else None),
            "conv-rover-001",
        )

    def test_drone_conversation_thread_persists(self):
        """Verify drone stores conversation_id after first turn (mocked)."""
        from unittest.mock import MagicMock
        from app.agents_api import AgentsApiDroneReasoner
        from app.world import world

        reasoner = AgentsApiDroneReasoner(agent_id="drone-mistral", world=world)

        mock_output = MagicMock()
        mock_output.tool_name = "scan"
        mock_output.arguments = "{}"
        del mock_output.content

        mock_response = MagicMock()
        mock_response.conversation_id = "conv-drone-001"
        mock_response.outputs = [mock_output]

        mock_client = MagicMock()
        mock_client.beta.conversations.start.return_value = mock_response
        mock_client.beta.conversations.append.return_value = mock_response
        mock_client.beta.agents.create.return_value = MagicMock(id="agent-id-456")

        reasoner._client = mock_client
        reasoner._mistral_agent_id = "agent-id-456"

        # First turn
        reasoner.run_turn()
        mock_client.beta.conversations.start.assert_called_once()
        self.assertEqual(reasoner._conversation_id, "conv-drone-001")

        # Second turn
        mock_client.beta.conversations.start.reset_mock()
        reasoner.run_turn()
        mock_client.beta.conversations.append.assert_called_once()

    def test_station_conversation_thread_persists(self):
        """Verify station stores conversation_id after first call (mocked)."""
        from unittest.mock import MagicMock
        from app.agents_api import AgentsApiStationReasoner
        from app.world import observe_station

        reasoner = AgentsApiStationReasoner()

        mock_output = MagicMock()
        mock_output.tool_name = "assign_mission"
        mock_output.arguments = '{"agent_id": "rover-mistral", "objective": "test"}'
        del mock_output.content

        mock_response = MagicMock()
        mock_response.conversation_id = "conv-station-001"
        mock_response.outputs = [mock_output]

        mock_client = MagicMock()
        mock_client.beta.conversations.start.return_value = mock_response
        mock_client.beta.conversations.append.return_value = mock_response
        mock_client.beta.agents.create.return_value = MagicMock(id="agent-id-789")

        reasoner._client = mock_client
        reasoner._mistral_agent_id = "agent-id-789"

        ctx = observe_station()
        # First call
        reasoner.define_mission(ctx)
        mock_client.beta.conversations.start.assert_called_once()
        self.assertEqual(reasoner._conversation_id, "conv-station-001")

        # Second call
        mock_client.beta.conversations.start.reset_mock()
        reasoner.evaluate_situation(ctx, [])
        mock_client.beta.conversations.append.assert_called_once()


class TestPersistThreadsConfig(unittest.TestCase):
    """Tests for agents_api_persist_threads config toggle (US3)."""

    def test_persist_threads_setting_exists(self):
        """Verify agents_api_persist_threads field exists in Settings."""
        from app.config import Settings

        self.assertIn("agents_api_persist_threads", Settings.model_fields)

    def test_persist_threads_default_true(self):
        """Default value for agents_api_persist_threads should be True."""
        from app.config import settings

        self.assertTrue(settings.agents_api_persist_threads)

    def test_persist_threads_false_skips_storing(self):
        """When persist_threads=False, conversation_id is NOT stored after start()."""
        from unittest.mock import MagicMock, patch
        from app.agents_api import AgentsApiRoverReasoner
        from app.world import world

        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["mission"] = {
            "objective": "Explore the terrain",
            "plan": [],
        }
        world.state["agents"]["rover-mistral"]["visited"] = [[10, 10]]

        reasoner = AgentsApiRoverReasoner(agent_id="rover-mistral", world=world)

        mock_output = MagicMock()
        mock_output.tool_name = "move"
        mock_output.arguments = '{"direction": "north"}'
        del mock_output.content

        mock_response = MagicMock()
        mock_response.conversation_id = "conv-should-not-store"
        mock_response.outputs = [mock_output]

        mock_client = MagicMock()
        mock_client.beta.conversations.start.return_value = mock_response
        mock_client.beta.agents.create.return_value = MagicMock(id="agent-id-x")

        reasoner._client = mock_client
        reasoner._mistral_agent_id = "agent-id-x"

        with patch("app.agents_api.settings") as mock_settings:
            mock_settings.agents_api_persist_threads = False
            mock_settings.mistral_api_key = "test-key"
            reasoner.run_turn()

        # conversation_id should NOT be stored when persist_threads=False
        self.assertIsNone(reasoner._conversation_id)

        # Second turn should also call start() (not append())
        with patch("app.agents_api.settings") as mock_settings:
            mock_settings.agents_api_persist_threads = False
            mock_settings.mistral_api_key = "test-key"
            reasoner.run_turn()

        # Both calls should be start(), never append()
        mock_client.beta.conversations.append.assert_not_called()


class TestTrainingLoggerIntegration(unittest.TestCase):
    """Tests for training logger integration via Loop inheritance (US2)."""

    def test_rover_loop_inherits_tick(self):
        """RoverAgentsApiLoop inherits tick() from RoverLoop."""
        from app.agents_api import RoverAgentsApiLoop
        from app.agent import RoverLoop

        self.assertTrue(issubclass(RoverAgentsApiLoop, RoverLoop))
        # tick() should come from parent, not overridden
        self.assertIs(RoverAgentsApiLoop.tick, RoverLoop.tick)

    def test_drone_loop_inherits_tick(self):
        """DroneAgentsApiLoop inherits tick() from DroneLoop."""
        from app.agents_api import DroneAgentsApiLoop
        from app.agent import DroneLoop

        self.assertTrue(issubclass(DroneAgentsApiLoop, DroneLoop))
        self.assertIs(DroneAgentsApiLoop.tick, DroneLoop.tick)

    def test_station_loop_inherits_from_station_loop(self):
        """StationAgentsApiLoop inherits from StationLoop."""
        from app.agents_api import StationAgentsApiLoop
        from app.agent import StationLoop

        self.assertTrue(issubclass(StationAgentsApiLoop, StationLoop))

    def test_todo_comment_removed(self):
        """The # TODO: integrate training logger comment should be removed."""
        import inspect
        import app.agents_api as module

        source = inspect.getsource(module)
        self.assertNotIn("# TODO: integrate training logger", source)
