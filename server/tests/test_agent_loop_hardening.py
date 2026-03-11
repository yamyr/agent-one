"""Tests for agent loop hardening fixes (branch 191-agent-loop-hardening).

Covers 6 bugs:
  1. Tool whitelist: drop_item/request_confirm accepted by rover reasoners
  2. RuntimeError caught in all run_turn() except clauses
  3. json.JSONDecodeError caught in all run_turn() except clauses
  4. Drone intel relay sends to ALL active rovers, not just rover-mistral
  5. HaulerMistralLoop defaults to agent_id='hauler-mistral'
  6. Dead HaulerReasoner class removed; backward-compat alias preserved
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from app.agent import (
    DroneAgent,
    HaulerAgent,
    HaulerMistralLoop,
    HuggingFaceDroneAgent,
    HuggingFaceRoverReasoner,
    MistralRoverReasoner,
    ROVER_TOOLS,
)
from app.world import world


def _make_mock_tool_call(name, arguments):
    tc = MagicMock()
    tc.function.name = name
    tc.function.arguments = json.dumps(arguments) if isinstance(arguments, dict) else arguments
    return tc


def _make_mock_response(tool_name, tool_args, thinking="test thinking"):
    response = MagicMock()
    choice = MagicMock()
    choice.message.content = thinking
    choice.message.tool_calls = [_make_mock_tool_call(tool_name, tool_args)]
    response.choices = [choice]
    return response


def _make_empty_response(thinking="no action decided"):
    response = MagicMock()
    choice = MagicMock()
    choice.message.content = thinking
    choice.message.tool_calls = None
    response.choices = [choice]
    return response


# ── Bug 1: Tool whitelist includes drop_item and request_confirm ──


class TestRoverWhitelistDropItem(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["mission"] = {
            "objective": "Test",
            "plan": [],
        }
        world.state["agents"]["rover-mistral"]["visited"] = [[5, 5]]

    @patch.object(MistralRoverReasoner, "_get_client")
    def test_drop_item_accepted_by_mistral_rover(self, mock_client):
        mock_client.return_value.chat.complete.return_value = _make_mock_response(
            "drop_item", {"item_index": 0}
        )
        reasoner = MistralRoverReasoner()
        turn = reasoner.run_turn()
        self.assertEqual(turn["action"]["name"], "drop_item")
        self.assertEqual(turn["action"]["params"]["item_index"], 0)

    @patch.object(MistralRoverReasoner, "_get_client")
    def test_request_confirm_accepted_by_mistral_rover(self, mock_client):
        mock_client.return_value.chat.complete.return_value = _make_mock_response(
            "request_confirm", {"question": "Cross hazard zone?"}
        )
        reasoner = MistralRoverReasoner()
        turn = reasoner.run_turn()
        self.assertEqual(turn["action"]["name"], "request_confirm")
        self.assertEqual(turn["action"]["params"]["question"], "Cross hazard zone?")

    def test_drop_item_in_rover_tools_list(self):
        names = [t["function"]["name"] for t in ROVER_TOOLS]
        self.assertIn("drop_item", names)

    def test_request_confirm_in_rover_tools_list(self):
        names = [t["function"]["name"] for t in ROVER_TOOLS]
        self.assertIn("request_confirm", names)


class TestHFRoverWhitelistDropItem(unittest.TestCase):
    def setUp(self):
        world.state["agents"].setdefault(
            "rover-huggingface",
            {
                "type": "rover",
                "position": [5, 5],
                "battery": 1.0,
                "mission": {"objective": "Test", "plan": []},
                "visited": [[5, 5]],
                "memory": [],
                "inventory": [],
                "goal_confidence": 0.5,
            },
        )
        world.state["agents"]["rover-huggingface"]["position"] = [5, 5]
        world.state["agents"]["rover-huggingface"]["battery"] = 1.0

    @patch.object(HuggingFaceRoverReasoner, "_get_client")
    def test_drop_item_accepted_by_hf_rover(self, mock_client):
        mock_client.return_value.chat_completion.return_value = _make_mock_response(
            "drop_item", {"item_index": 0}
        )
        reasoner = HuggingFaceRoverReasoner(world=world)
        turn = reasoner.run_turn()
        self.assertEqual(turn["action"]["name"], "drop_item")

    @patch.object(HuggingFaceRoverReasoner, "_get_client")
    def test_request_confirm_accepted_by_hf_rover(self, mock_client):
        mock_client.return_value.chat_completion.return_value = _make_mock_response(
            "request_confirm", {"question": "Proceed?"}
        )
        reasoner = HuggingFaceRoverReasoner(world=world)
        turn = reasoner.run_turn()
        self.assertEqual(turn["action"]["name"], "request_confirm")


# ── Bug 2: RuntimeError caught in all run_turn() methods ──


class TestRuntimeErrorCaught(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["mission"] = {
            "objective": "Test",
            "plan": [],
        }
        world.state["agents"]["rover-mistral"]["visited"] = [[5, 5]]

    @patch.object(MistralRoverReasoner, "_get_client")
    def test_mistral_rover_catches_runtime_error(self, mock_client):
        mock_client.return_value.chat.complete.return_value = _make_empty_response()
        reasoner = MistralRoverReasoner()
        turn = reasoner.run_turn()
        self.assertIn("LLM fallback", turn["thinking"])
        self.assertEqual(turn["action"]["name"], "move")

    @patch.object(HaulerAgent, "_get_client")
    def test_hauler_catches_runtime_error(self, mock_client):
        mock_client.return_value.chat.complete.return_value = _make_empty_response()
        reasoner = HaulerAgent(world=world)
        turn = reasoner.run_turn()
        self.assertIn("LLM fallback", turn["thinking"])

    @patch.object(DroneAgent, "_get_client")
    def test_drone_catches_runtime_error(self, mock_client):
        world.state["agents"]["drone-mistral"]["memory"] = ["previous action"]
        mock_client.return_value.chat.complete.return_value = _make_empty_response()
        reasoner = DroneAgent(world=world)
        turn = reasoner.run_turn()
        self.assertIn("LLM fallback", turn["thinking"])


# ── Bug 3: json.JSONDecodeError caught in all run_turn() methods ──


class TestJSONDecodeErrorCaught(unittest.TestCase):
    def setUp(self):
        world.state["agents"]["rover-mistral"]["position"] = [5, 5]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["mission"] = {
            "objective": "Test",
            "plan": [],
        }
        world.state["agents"]["rover-mistral"]["visited"] = [[5, 5]]

    @patch.object(MistralRoverReasoner, "_get_client")
    def test_mistral_rover_catches_json_error(self, mock_client):
        response = MagicMock()
        choice = MagicMock()
        choice.message.content = "thinking"
        tc = MagicMock()
        tc.function.name = "move"
        tc.function.arguments = "{invalid json"
        choice.message.tool_calls = [tc]
        response.choices = [choice]
        mock_client.return_value.chat.complete.return_value = response
        reasoner = MistralRoverReasoner()
        turn = reasoner.run_turn()
        self.assertIn("LLM fallback", turn["thinking"])
        self.assertEqual(turn["action"]["name"], "move")

    @patch.object(HaulerAgent, "_get_client")
    def test_hauler_catches_json_error(self, mock_client):
        response = MagicMock()
        choice = MagicMock()
        choice.message.content = "thinking"
        tc = MagicMock()
        tc.function.name = "move"
        tc.function.arguments = "{bad"
        choice.message.tool_calls = [tc]
        response.choices = [choice]
        mock_client.return_value.chat.complete.return_value = response
        reasoner = HaulerAgent(world=world)
        turn = reasoner.run_turn()
        self.assertIn("LLM fallback", turn["thinking"])

    @patch.object(DroneAgent, "_get_client")
    def test_drone_catches_json_error(self, mock_client):
        world.state["agents"]["drone-mistral"]["memory"] = ["previous action"]
        response = MagicMock()
        choice = MagicMock()
        choice.message.content = "thinking"
        tc = MagicMock()
        tc.function.name = "scan"
        tc.function.arguments = "not-json"
        choice.message.tool_calls = [tc]
        response.choices = [choice]
        mock_client.return_value.chat.complete.return_value = response
        reasoner = DroneAgent(world=world)
        turn = reasoner.run_turn()
        self.assertIn("LLM fallback", turn["thinking"])


# ── Bug 4: Drone intel relay sends to all rovers ──


class TestDroneIntelRelay(unittest.TestCase):
    def test_relay_code_references_all_rovers(self):
        import inspect

        from app.agent import DroneLoop

        source = inspect.getsource(DroneLoop.tick)
        self.assertNotIn('"rover-mistral"', source, "Drone relay still hardcoded to rover-mistral")
        self.assertIn("get_agents", source, "Drone relay should iterate over agents")

    def test_relay_uses_type_rover_filter(self):
        import inspect

        from app.agent import DroneLoop

        source = inspect.getsource(DroneLoop.tick)
        self.assertIn('"rover"', source, "Drone relay should filter by type='rover'")


# ── Bug 5: HaulerMistralLoop default agent_id ──


class TestHaulerMistralLoopDefaultId(unittest.TestCase):
    def test_default_agent_id_is_hauler_mistral(self):
        import inspect

        sig = inspect.signature(HaulerMistralLoop.__init__)
        default = sig.parameters["agent_id"].default
        self.assertEqual(default, "hauler-mistral")

    def test_hauler_agent_default_id_is_hauler_mistral(self):
        import inspect

        sig = inspect.signature(HaulerAgent.__init__)
        default = sig.parameters["agent_id"].default
        self.assertEqual(default, "hauler-mistral")


# ── Bug 6: Dead HaulerReasoner class removed ──


class TestDeadCodeRemoved(unittest.TestCase):
    def test_no_standalone_hauler_reasoner_class(self):
        import inspect

        from app import agent as agent_module

        members = dict(inspect.getmembers(agent_module, inspect.isclass))
        if "HaulerReasoner" in members:
            self.assertIs(
                members["HaulerReasoner"],
                HaulerAgent,
                "HaulerReasoner should be an alias for HaulerAgent, not a separate class",
            )

    def test_hauler_reasoner_alias_points_to_hauler_agent(self):
        from app.agent import HaulerReasoner

        self.assertIs(HaulerReasoner, HaulerAgent)

    def test_no_mistral_hauler_reasoner_alias(self):
        from app import agent as agent_module

        self.assertFalse(
            hasattr(agent_module, "MistralHaulerReasoner"),
            "MistralHaulerReasoner alias should be removed",
        )

    def test_no_pickup_cargo_in_hauler_tools(self):
        from app.agent import HAULER_TOOLS

        names = [t["function"]["name"] for t in HAULER_TOOLS]
        self.assertNotIn(
            "pickup_cargo", names, "Dead code referenced pickup_cargo; live code uses load_cargo"
        )
        self.assertIn("load_cargo", names)


# ── Additional: Verify all except clauses are consistent ──


class TestExceptClauseConsistency(unittest.TestCase):
    def test_all_run_turn_catch_runtime_error(self):
        import inspect

        for cls in [MistralRoverReasoner, HaulerAgent, DroneAgent]:
            source = inspect.getsource(cls.run_turn)
            self.assertIn(
                "RuntimeError",
                source,
                f"{cls.__name__}.run_turn does not catch RuntimeError",
            )

    def test_all_run_turn_catch_json_decode_error(self):
        import inspect

        for cls in [MistralRoverReasoner, HaulerAgent, DroneAgent]:
            source = inspect.getsource(cls.run_turn)
            self.assertIn(
                "JSONDecodeError",
                source,
                f"{cls.__name__}.run_turn does not catch json.JSONDecodeError",
            )

    def test_hf_run_turn_catch_runtime_error(self):
        import inspect

        for cls in [HuggingFaceRoverReasoner, HuggingFaceDroneAgent]:
            source = inspect.getsource(cls.run_turn)
            self.assertIn(
                "RuntimeError",
                source,
                f"{cls.__name__}.run_turn does not catch RuntimeError",
            )

    def test_hf_run_turn_catch_json_decode_error(self):
        import inspect

        for cls in [HuggingFaceRoverReasoner, HuggingFaceDroneAgent]:
            source = inspect.getsource(cls.run_turn)
            self.assertIn(
                "JSONDecodeError",
                source,
                f"{cls.__name__}.run_turn does not catch json.JSONDecodeError",
            )


# ── Whitelist completeness: every ROVER_TOOLS name is in whitelist ──


class TestWhitelistCompleteness(unittest.TestCase):
    def test_mistral_rover_whitelist_covers_all_tools(self):
        import inspect

        tool_names = {t["function"]["name"] for t in ROVER_TOOLS}
        source = inspect.getsource(MistralRoverReasoner.run_turn)
        for name in tool_names:
            self.assertIn(
                f'"{name}"',
                source,
                f"MistralRoverReasoner whitelist missing tool: {name}",
            )

    def test_hf_rover_whitelist_covers_all_tools(self):
        import inspect

        tool_names = {t["function"]["name"] for t in ROVER_TOOLS}
        source = inspect.getsource(HuggingFaceRoverReasoner.run_turn)
        for name in tool_names:
            self.assertIn(
                f'"{name}"',
                source,
                f"HuggingFaceRoverReasoner whitelist missing tool: {name}",
            )


if __name__ == "__main__":
    unittest.main()
