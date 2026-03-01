"""Tests for HuggingFace Inference API integration — rover, drone, station, narrator."""

import json
import unittest
from unittest.mock import AsyncMock, MagicMock

from app.agent import (
    HuggingFaceDroneAgent,
    HuggingFaceRoverReasoner,
    RoverHuggingFaceLoop,
    DroneHuggingFaceLoop,
)
from app.config import settings
from app.models import AgentMission, RoverSummary, StationContext, StoneInfo
from app.narrator import Narrator
from app.station import StationAgent
from app.world import world


def _mock_tool_call(name, arguments):
    """Create a mock tool call object matching HuggingFace response format."""
    tc = MagicMock()
    tc.function.name = name
    tc.function.arguments = json.dumps(arguments)
    return tc


def _mock_hf_response(content=None, tool_calls=None):
    """Create a mock HuggingFace chat_completion response."""
    choice = MagicMock()
    choice.message.content = content
    choice.message.tool_calls = tool_calls
    response = MagicMock()
    response.choices = [choice]
    return response


def _make_station_context():
    """Build a typed StationContext for testing."""
    return StationContext(
        grid_w=20,
        grid_h=20,
        rovers=[
            RoverSummary(
                id="rover-huggingface",
                position=[0, 0],
                battery=1.0,
                mission=AgentMission(objective="Explore the terrain", plan=[]),
                visited_count=1,
            ),
        ],
        stones=[
            StoneInfo(type="unknown", position=[5, 5]),
        ],
    )


# ── HuggingFace Rover Reasoner ──────────────────────────────────────────────


class TestHuggingFaceRoverReasoner(unittest.TestCase):
    def setUp(self):
        self._orig_hf_key = settings.hugging_face_read
        self._orig_model = settings.huggingface_model
        settings.hugging_face_read = "test-hf-key"
        world.state["agents"]["rover-huggingface"] = {
            "type": "rover",
            "position": [5, 5],
            "battery": 1.0,
            "mission": {"objective": "Explore the terrain", "plan": []},
            "visited": [[5, 5]],
            "revealed": [[5, 5]],
            "inventory": [],
            "memory": [],
            "solar_panels_remaining": 2,
            "pending_commands": [],
        }

    def tearDown(self):
        settings.hugging_face_read = self._orig_hf_key
        settings.huggingface_model = self._orig_model
        world.state["agents"].pop("rover-huggingface", None)

    def test_run_turn_returns_action(self):
        agent = HuggingFaceRoverReasoner(agent_id="rover-huggingface")
        mock_client = MagicMock()
        agent._client = mock_client

        tool_calls = [_mock_tool_call("move", {"direction": "north"})]
        mock_client.chat_completion.return_value = _mock_hf_response(
            content="Moving north to explore.", tool_calls=tool_calls
        )

        turn = agent.run_turn()

        self.assertEqual(turn["thinking"], "Moving north to explore.")
        self.assertIsNotNone(turn["action"])
        self.assertEqual(turn["action"]["name"], "move")
        self.assertEqual(turn["action"]["params"]["direction"], "north")
        mock_client.chat_completion.assert_called_once()

    def test_run_turn_dig_action(self):
        agent = HuggingFaceRoverReasoner(agent_id="rover-huggingface")
        mock_client = MagicMock()
        agent._client = mock_client

        tool_calls = [_mock_tool_call("dig", {})]
        mock_client.chat_completion.return_value = _mock_hf_response(
            content="Digging for basalt.", tool_calls=tool_calls
        )

        turn = agent.run_turn()
        self.assertEqual(turn["action"]["name"], "dig")

    def test_run_turn_analyze_action(self):
        agent = HuggingFaceRoverReasoner(agent_id="rover-huggingface")
        mock_client = MagicMock()
        agent._client = mock_client

        tool_calls = [_mock_tool_call("analyze", {})]
        mock_client.chat_completion.return_value = _mock_hf_response(
            content="Analyzing vein.", tool_calls=tool_calls
        )

        turn = agent.run_turn()
        self.assertEqual(turn["action"]["name"], "analyze")

    def test_run_turn_notify_action(self):
        agent = HuggingFaceRoverReasoner(agent_id="rover-huggingface")
        mock_client = MagicMock()
        agent._client = mock_client

        tool_calls = [_mock_tool_call("notify", {"message": "Found basalt!"})]
        mock_client.chat_completion.return_value = _mock_hf_response(
            content="Notifying station.", tool_calls=tool_calls
        )

        turn = agent.run_turn()
        self.assertEqual(turn["action"]["name"], "notify")
        self.assertEqual(turn["action"]["params"]["message"], "Found basalt!")

    def test_fallback_on_error(self):
        from huggingface_hub.errors import HfHubHTTPError

        agent = HuggingFaceRoverReasoner(agent_id="rover-huggingface")
        mock_client = MagicMock()
        agent._client = mock_client

        mock_response = MagicMock()
        mock_client.chat_completion.side_effect = HfHubHTTPError(
            "API error", response=mock_response
        )

        turn = agent.run_turn()

        self.assertIn("LLM fallback", turn["thinking"])
        self.assertIsNotNone(turn["action"])
        self.assertEqual(turn["action"]["name"], "move")

    def test_fallback_on_timeout(self):
        from huggingface_hub.errors import InferenceTimeoutError

        agent = HuggingFaceRoverReasoner(agent_id="rover-huggingface")
        mock_client = MagicMock()
        agent._client = mock_client

        mock_client.chat_completion.side_effect = InferenceTimeoutError("Timeout")

        turn = agent.run_turn()

        self.assertIn("LLM fallback", turn["thinking"])
        self.assertEqual(turn["action"]["name"], "move")

    def test_fallback_on_connection_error(self):
        agent = HuggingFaceRoverReasoner(agent_id="rover-huggingface")
        mock_client = MagicMock()
        agent._client = mock_client

        mock_client.chat_completion.side_effect = ConnectionError("Connection refused")

        turn = agent.run_turn()

        self.assertIn("LLM fallback", turn["thinking"])

    def test_get_client_raises_without_key(self):
        settings.hugging_face_read = ""
        agent = HuggingFaceRoverReasoner(agent_id="rover-huggingface")
        agent._client = None
        with self.assertRaises(RuntimeError) as ctx:
            agent._get_client()
        self.assertIn("HUGGING_FACE_READ not set", str(ctx.exception))

    def test_default_model(self):
        settings.huggingface_model = ""
        agent = HuggingFaceRoverReasoner(agent_id="rover-huggingface")
        self.assertEqual(agent.model, "Qwen/Qwen2.5-72B-Instruct")

    def test_custom_model(self):
        settings.huggingface_model = "custom/model"
        agent = HuggingFaceRoverReasoner(agent_id="rover-huggingface")
        self.assertEqual(agent.model, "custom/model")

    def test_unknown_tool_ignored(self):
        agent = HuggingFaceRoverReasoner(agent_id="rover-huggingface")
        mock_client = MagicMock()
        agent._client = mock_client

        tool_calls = [_mock_tool_call("self_destruct", {})]
        mock_client.chat_completion.return_value = _mock_hf_response(
            content="Unknown tool.", tool_calls=tool_calls
        )

        # Should raise RuntimeError because no valid tool action
        with self.assertRaises(RuntimeError):
            agent.run_turn()

    def test_inherits_build_context(self):
        """HuggingFaceRoverReasoner should inherit _build_context from MistralRoverReasoner."""
        agent = HuggingFaceRoverReasoner(agent_id="rover-huggingface")
        context = agent._build_context()
        self.assertIn("rover-huggingface", context)
        self.assertIn("autonomous Mars rover", context)


# ── HuggingFace Drone Agent ──────────────────────────────────────────────────


class TestHuggingFaceDroneAgent(unittest.TestCase):
    def setUp(self):
        self._orig_hf_key = settings.hugging_face_read
        self._orig_model = settings.huggingface_model
        settings.hugging_face_read = "test-hf-key"
        world.state["agents"]["drone-huggingface"] = {
            "type": "drone",
            "position": [3, 3],
            "battery": 1.0,
            "mission": {"objective": "Scout the terrain", "plan": []},
            "visited": [[3, 3]],
            "revealed": [[3, 3]],
            "memory": [],
            "pending_commands": [],
        }

    def tearDown(self):
        settings.hugging_face_read = self._orig_hf_key
        settings.huggingface_model = self._orig_model
        world.state["agents"].pop("drone-huggingface", None)

    def test_run_turn_returns_action(self):
        agent = HuggingFaceDroneAgent(agent_id="drone-huggingface")
        mock_client = MagicMock()
        agent._client = mock_client

        tool_calls = [_mock_tool_call("scan", {})]
        mock_client.chat_completion.return_value = _mock_hf_response(
            content="Scanning area.", tool_calls=tool_calls
        )

        turn = agent.run_turn()

        self.assertEqual(turn["thinking"], "Scanning area.")
        self.assertEqual(turn["action"]["name"], "scan")
        mock_client.chat_completion.assert_called_once()

    def test_run_turn_move_action(self):
        agent = HuggingFaceDroneAgent(agent_id="drone-huggingface")
        mock_client = MagicMock()
        agent._client = mock_client

        tool_calls = [_mock_tool_call("move", {"direction": "east", "distance": 5})]
        mock_client.chat_completion.return_value = _mock_hf_response(
            content="Flying east.", tool_calls=tool_calls
        )

        turn = agent.run_turn()
        self.assertEqual(turn["action"]["name"], "move")
        self.assertEqual(turn["action"]["params"]["direction"], "east")
        self.assertEqual(turn["action"]["params"]["distance"], 5)

    def test_fallback_on_error(self):
        from huggingface_hub.errors import HfHubHTTPError

        agent = HuggingFaceDroneAgent(agent_id="drone-huggingface")
        mock_client = MagicMock()
        agent._client = mock_client

        mock_response = MagicMock()
        mock_client.chat_completion.side_effect = HfHubHTTPError(
            "API error", response=mock_response
        )

        turn = agent.run_turn()

        self.assertIn("LLM fallback", turn["thinking"])
        self.assertIsNotNone(turn["action"])

    def test_get_client_raises_without_key(self):
        settings.hugging_face_read = ""
        agent = HuggingFaceDroneAgent(agent_id="drone-huggingface")
        agent._client = None
        with self.assertRaises(RuntimeError) as ctx:
            agent._get_client()
        self.assertIn("HUGGING_FACE_READ not set", str(ctx.exception))

    def test_first_turn_no_tool_falls_back_to_scan(self):
        """On first turn with no tool call, drone should default to scan."""
        agent = HuggingFaceDroneAgent(agent_id="drone-huggingface")
        mock_client = MagicMock()
        agent._client = mock_client

        # No tool calls, first turn (no memory)
        mock_client.chat_completion.return_value = _mock_hf_response(
            content="Thinking...", tool_calls=None
        )

        turn = agent.run_turn()
        self.assertEqual(turn["action"]["name"], "scan")

    def test_inherits_build_context(self):
        """HuggingFaceDroneAgent should inherit _build_context from DroneAgent."""
        agent = HuggingFaceDroneAgent(agent_id="drone-huggingface")
        context = agent._build_context()
        self.assertIn("drone-huggingface", context)
        self.assertIn("autonomous Mars drone scout", context)


# ── HuggingFace Loop Classes ────────────────────────────────────────────────


class TestHuggingFaceLoopClasses(unittest.TestCase):
    def setUp(self):
        self._orig_hf_key = settings.hugging_face_read
        settings.hugging_face_read = "test-hf-key"
        world.state["agents"]["rover-huggingface"] = {
            "type": "rover",
            "position": [0, 0],
            "battery": 1.0,
            "mission": {"objective": "Explore", "plan": []},
            "visited": [[0, 0]],
            "revealed": [[0, 0]],
            "inventory": [],
            "memory": [],
            "solar_panels_remaining": 2,
            "pending_commands": [],
        }
        world.state["agents"]["drone-huggingface"] = {
            "type": "drone",
            "position": [0, 0],
            "battery": 1.0,
            "mission": {"objective": "Scout", "plan": []},
            "visited": [[0, 0]],
            "revealed": [[0, 0]],
            "memory": [],
            "pending_commands": [],
        }

    def tearDown(self):
        settings.hugging_face_read = self._orig_hf_key
        world.state["agents"].pop("rover-huggingface", None)
        world.state["agents"].pop("drone-huggingface", None)

    def test_rover_loop_has_hf_reasoner(self):
        loop = RoverHuggingFaceLoop(agent_id="rover-huggingface")
        self.assertIsInstance(loop._reasoner, HuggingFaceRoverReasoner)

    def test_drone_loop_has_hf_reasoner(self):
        loop = DroneHuggingFaceLoop()
        self.assertIsInstance(loop._reasoner, HuggingFaceDroneAgent)

    def test_rover_loop_agent_id(self):
        loop = RoverHuggingFaceLoop(agent_id="rover-huggingface")
        self.assertEqual(loop.agent_id, "rover-huggingface")

    def test_drone_loop_agent_id(self):
        loop = DroneHuggingFaceLoop()
        self.assertEqual(loop.agent_id, "drone-huggingface")


# ── Station HuggingFace ─────────────────────────────────────────────────────


class TestStationHuggingFace(unittest.TestCase):
    def setUp(self):
        self._orig_provider = settings.llm_provider
        self._orig_hf_key = settings.hugging_face_read
        self._orig_mistral_key = settings.mistral_api_key
        self._orig_hf_model = settings.huggingface_model

    def tearDown(self):
        settings.llm_provider = self._orig_provider
        settings.hugging_face_read = self._orig_hf_key
        settings.mistral_api_key = self._orig_mistral_key
        settings.huggingface_model = self._orig_hf_model

    def test_call_llm_uses_hf_client(self):
        settings.llm_provider = "huggingface"
        settings.hugging_face_read = "test-hf-key"
        settings.huggingface_model = "Qwen/Qwen2.5-72B-Instruct"

        station = StationAgent()
        mock_hf = MagicMock()
        station._hf_client = mock_hf

        tool_calls = [
            _mock_tool_call(
                "assign_mission",
                {"agent_id": "rover-huggingface", "objective": "Explore north"},
            )
        ]
        mock_hf.chat_completion.return_value = _mock_hf_response(
            content="Assigning missions.", tool_calls=tool_calls
        )

        ctx = _make_station_context()
        result = station.define_mission(ctx)

        self.assertEqual(result["thinking"], "Assigning missions.")
        self.assertEqual(len(result["actions"]), 1)
        self.assertEqual(result["actions"][0]["name"], "assign_mission")
        mock_hf.chat_completion.assert_called_once()

    def test_call_llm_defaults_to_mistral(self):
        settings.llm_provider = "mistral"
        settings.mistral_api_key = "test-mistral-key"

        station = StationAgent()
        mock_mistral = MagicMock()
        station._client = mock_mistral

        tool_calls = [_mock_tool_call("broadcast_alert", {"message": "Mission start"})]
        mock_mistral.chat.complete.return_value = _mock_hf_response(
            content="Starting.", tool_calls=tool_calls
        )

        ctx = _make_station_context()
        result = station.define_mission(ctx)

        self.assertEqual(result["thinking"], "Starting.")
        mock_mistral.chat.complete.assert_called_once()

    def test_get_hf_client_raises_without_key(self):
        settings.hugging_face_read = ""
        station = StationAgent()
        with self.assertRaises(RuntimeError) as ctx:
            station._get_hf_client()
        self.assertIn("HUGGING_FACE_READ not set", str(ctx.exception))

    def test_hf_client_caches(self):
        settings.hugging_face_read = "test-hf-key"
        station = StationAgent()
        mock_hf = MagicMock()
        station._hf_client = mock_hf

        client = station._get_hf_client()
        self.assertIs(client, mock_hf)

    def test_station_has_hf_client_attr(self):
        station = StationAgent()
        self.assertIsNone(station._hf_client)


# ── Narrator HuggingFace ────────────────────────────────────────────────────


class TestNarratorHuggingFace(unittest.TestCase):
    def setUp(self):
        self._orig_provider = settings.llm_provider
        self._orig_hf_key = settings.hugging_face_read
        self._orig_hf_narration_model = settings.huggingface_narration_model
        self.broadcast = AsyncMock()

    def tearDown(self):
        settings.llm_provider = self._orig_provider
        settings.hugging_face_read = self._orig_hf_key
        settings.huggingface_narration_model = self._orig_hf_narration_model

    def test_generate_text_uses_hf_client(self):
        settings.llm_provider = "huggingface"
        settings.hugging_face_read = "test-hf-key"
        settings.huggingface_narration_model = "Qwen/Qwen2.5-72B-Instruct"

        narrator = Narrator(broadcast_fn=self.broadcast)
        mock_hf = MagicMock()
        narrator._huggingface = mock_hf

        choice = MagicMock()
        choice.message.content = "COMMANDER REX: Great news from the surface."
        response = MagicMock()
        response.choices = [choice]
        mock_hf.chat_completion.return_value = response

        result = narrator._generate_text("Test prompt")

        self.assertEqual(result, "COMMANDER REX: Great news from the surface.")
        mock_hf.chat_completion.assert_called_once()
        call_kwargs = mock_hf.chat_completion.call_args[1]
        self.assertEqual(call_kwargs["model"], "Qwen/Qwen2.5-72B-Instruct")
        self.assertEqual(call_kwargs["max_tokens"], 350)
        self.assertEqual(call_kwargs["temperature"], 0.9)

    def test_generate_text_uses_mistral_by_default(self):
        settings.llm_provider = "mistral"

        narrator = Narrator(broadcast_fn=self.broadcast)
        mock_mistral = MagicMock()
        narrator._mistral = mock_mistral

        choice = MagicMock()
        choice.message.content = "DR. NOVA: Exciting discovery!"
        response = MagicMock()
        response.choices = [choice]
        mock_mistral.chat.complete.return_value = response

        result = narrator._generate_text("Test prompt")

        self.assertEqual(result, "DR. NOVA: Exciting discovery!")
        mock_mistral.chat.complete.assert_called_once()

    def test_generate_text_returns_none_on_error(self):
        settings.llm_provider = "huggingface"
        settings.hugging_face_read = "test-hf-key"

        narrator = Narrator(broadcast_fn=self.broadcast)
        mock_hf = MagicMock()
        narrator._huggingface = mock_hf
        mock_hf.chat_completion.side_effect = Exception("API error")

        result = narrator._generate_text("Test prompt")
        self.assertIsNone(result)

    def test_get_huggingface_raises_without_key(self):
        settings.hugging_face_read = ""
        narrator = Narrator(broadcast_fn=self.broadcast)
        with self.assertRaises(RuntimeError) as ctx:
            narrator._get_huggingface()
        self.assertIn("HUGGING_FACE_READ not set", str(ctx.exception))

    def test_get_huggingface_caches(self):
        settings.hugging_face_read = "test-hf-key"
        narrator = Narrator(broadcast_fn=self.broadcast)
        mock_hf = MagicMock()
        narrator._huggingface = mock_hf
        client = narrator._get_huggingface()
        self.assertIs(client, mock_hf)

    def test_narrator_has_huggingface_attr(self):
        narrator = Narrator(broadcast_fn=self.broadcast)
        self.assertIsNone(narrator._huggingface)


class TestNarratorHuggingFaceStreaming(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._orig_provider = settings.llm_provider
        self._orig_hf_key = settings.hugging_face_read
        self._orig_hf_narration_model = settings.huggingface_narration_model
        self.broadcast = AsyncMock()

    def tearDown(self):
        settings.llm_provider = self._orig_provider
        settings.hugging_face_read = self._orig_hf_key
        settings.huggingface_narration_model = self._orig_hf_narration_model

    async def test_generate_text_streaming_uses_hf(self):
        settings.llm_provider = "huggingface"
        settings.hugging_face_read = "test-hf-key"
        settings.huggingface_narration_model = "Qwen/Qwen2.5-72B-Instruct"

        narrator = Narrator(broadcast_fn=self.broadcast)
        mock_hf = MagicMock()
        narrator._huggingface = mock_hf

        # Mock streaming response — list of chunk objects
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "COMMANDER REX: "
        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = "Looks good out there."
        chunk3 = MagicMock()
        chunk3.choices = [MagicMock()]
        chunk3.choices[0].delta.content = None  # End of stream

        mock_hf.chat_completion.return_value = [chunk1, chunk2, chunk3]

        result = await narrator._generate_text_streaming("Test prompt")

        self.assertEqual(result, "COMMANDER REX: Looks good out there.")
        mock_hf.chat_completion.assert_called_once()
        call_kwargs = mock_hf.chat_completion.call_args[1]
        self.assertTrue(call_kwargs["stream"])
        # Should have broadcast 2 chunks (chunk3 has None content)
        self.assertEqual(self.broadcast.call_count, 2)

    async def test_generate_text_streaming_returns_none_on_error(self):
        settings.llm_provider = "huggingface"
        settings.hugging_face_read = "test-hf-key"

        narrator = Narrator(broadcast_fn=self.broadcast)
        mock_hf = MagicMock()
        narrator._huggingface = mock_hf
        mock_hf.chat_completion.side_effect = Exception("Stream error")

        result = await narrator._generate_text_streaming("Test prompt")
        self.assertIsNone(result)

    async def test_generate_text_streaming_mistral_by_default(self):
        settings.llm_provider = "mistral"

        narrator = Narrator(broadcast_fn=self.broadcast)
        mock_mistral = MagicMock()
        narrator._mistral = mock_mistral

        event1 = MagicMock()
        event1.data.choices = [MagicMock()]
        event1.data.choices[0].delta.content = "Hello"

        mock_mistral.chat.stream.return_value = [event1]

        result = await narrator._generate_text_streaming("Test prompt")

        self.assertEqual(result, "Hello")
        mock_mistral.chat.stream.assert_called_once()


# ── Main AGENT_MAP ──────────────────────────────────────────────────────────


class TestAgentMap(unittest.TestCase):
    def test_agent_map_has_huggingface_entries(self):
        from app.main import AGENT_MAP

        self.assertIn("rover-huggingface", AGENT_MAP)
        self.assertIn("drone-huggingface", AGENT_MAP)
        self.assertTrue(callable(AGENT_MAP["rover-huggingface"]))
        self.assertTrue(callable(AGENT_MAP["drone-huggingface"]))
