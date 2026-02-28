"""Tests for TrainingDataCollector — JSONL recording of LLM interactions."""

import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import MagicMock, patch


def _mock_mistral_response(content="thinking", tool_calls=None):
    """Create a mock Mistral chat.complete response."""
    choice = MagicMock()
    choice.message.content = content
    choice.message.tool_calls = tool_calls or []
    response = MagicMock()
    response.choices = [choice]
    return response


def _mock_tool_call(name, arguments, call_id="call_1"):
    """Create a mock tool call object matching Mistral response format."""
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = name
    tc.function.arguments = json.dumps(arguments) if isinstance(arguments, dict) else arguments
    return tc


class TestTrainingDataCollector(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.data_dir = self._tmpdir.name

    def tearDown(self):
        self._tmpdir.cleanup()

    def _make_collector(self, enabled=True):
        """Create a fresh TrainingDataCollector with patched settings."""
        with patch("app.training.settings") as mock_settings:
            mock_settings.training_data_enabled = enabled
            mock_settings.training_data_dir = self.data_dir
            from app.training import TrainingDataCollector

            c = TrainingDataCollector()
        return c

    # 1
    def test_recording_disabled_by_default(self):
        """When training_data_enabled=False, record_agent_interaction writes nothing."""
        collector = self._make_collector(enabled=False)
        response = _mock_mistral_response("thinking")

        collector.record_agent_interaction(
            agent_id="rover-mistral",
            agent_type="rover",
            messages=[
                {"role": "system", "content": "You are a rover."},
                {"role": "user", "content": "Move north."},
            ],
            tools=[],
            response=response,
        )

        # No files should be created
        files = list(Path(self.data_dir).glob("*.jsonl"))
        self.assertEqual(len(files), 0)

    # 2
    def test_record_agent_interaction_creates_jsonl(self):
        """Enable collection, call record_agent_interaction, verify JSONL file created."""
        collector = self._make_collector(enabled=True)
        tc = _mock_tool_call("move", {"direction": "north"})
        response = _mock_mistral_response("Moving north", tool_calls=[tc])

        collector.record_agent_interaction(
            agent_id="rover-mistral",
            agent_type="rover",
            messages=[
                {"role": "system", "content": "You are a rover."},
                {"role": "user", "content": "Move north."},
            ],
            tools=[{"type": "function", "function": {"name": "move"}}],
            response=response,
        )

        files = list(Path(self.data_dir).glob("rover_training_*.jsonl"))
        self.assertEqual(len(files), 1)

        with open(files[0]) as f:
            line = f.readline()
        data = json.loads(line)
        self.assertIn("messages", data)
        self.assertGreater(len(data["messages"]), 0)

    # 3
    def test_record_narration_interaction_creates_jsonl(self):
        """Enable collection, call record_narration_interaction, verify JSONL file created."""
        collector = self._make_collector(enabled=True)

        collector.record_narration_interaction(
            messages=[
                {"role": "system", "content": "You are a narrator."},
                {"role": "user", "content": "Describe the scene."},
            ],
            response_text="The rover moves across the red terrain...",
        )

        files = list(Path(self.data_dir).glob("narration_training_*.jsonl"))
        self.assertEqual(len(files), 1)

        with open(files[0]) as f:
            line = f.readline()
        data = json.loads(line)
        self.assertIn("messages", data)
        # system + user + assistant = 3
        self.assertEqual(len(data["messages"]), 3)
        self.assertEqual(data["messages"][-1]["role"], "assistant")
        self.assertEqual(
            data["messages"][-1]["content"],
            "The rover moves across the red terrain...",
        )

    # 4
    def test_jsonl_format_agent_with_tool_calls(self):
        """Verify the JSONL line includes system/user/assistant with tool_calls array."""
        collector = self._make_collector(enabled=True)
        tc1 = _mock_tool_call("drill", {"depth": 5}, call_id="call_a")
        tc2 = _mock_tool_call("pickup", {"target": "basalt"}, call_id="call_b")
        response = _mock_mistral_response("Drilling and picking up", tool_calls=[tc1, tc2])

        collector.record_agent_interaction(
            agent_id="rover-mistral",
            agent_type="rover",
            messages=[
                {"role": "system", "content": "System prompt"},
                {"role": "user", "content": "User prompt"},
            ],
            tools=[],
            response=response,
        )

        files = list(Path(self.data_dir).glob("rover_training_*.jsonl"))
        with open(files[0]) as f:
            data = json.loads(f.readline())

        msgs = data["messages"]
        # system, user, assistant, tool (drill), tool (pickup) = 5
        self.assertEqual(len(msgs), 5)
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[1]["role"], "user")
        self.assertEqual(msgs[2]["role"], "assistant")
        self.assertIn("tool_calls", msgs[2])
        self.assertEqual(len(msgs[2]["tool_calls"]), 2)
        self.assertEqual(msgs[2]["tool_calls"][0]["function"]["name"], "drill")
        self.assertEqual(msgs[2]["tool_calls"][1]["function"]["name"], "pickup")
        # Tool result placeholders
        self.assertEqual(msgs[3]["role"], "tool")
        self.assertEqual(msgs[3]["tool_call_id"], "call_a")
        self.assertEqual(msgs[4]["role"], "tool")
        self.assertEqual(msgs[4]["tool_call_id"], "call_b")

    # 5
    def test_jsonl_format_narration_no_tools(self):
        """Verify narration JSONL has system/user/assistant without tool_calls."""
        collector = self._make_collector(enabled=True)

        collector.record_narration_interaction(
            messages=[
                {"role": "system", "content": "You narrate Mars missions."},
                {"role": "user", "content": "What happened?"},
            ],
            response_text="The drone soared above the canyon.",
        )

        files = list(Path(self.data_dir).glob("narration_training_*.jsonl"))
        with open(files[0]) as f:
            data = json.loads(f.readline())

        msgs = data["messages"]
        self.assertEqual(len(msgs), 3)
        assistant_msg = msgs[2]
        self.assertEqual(assistant_msg["role"], "assistant")
        self.assertNotIn("tool_calls", assistant_msg)
        self.assertEqual(assistant_msg["content"], "The drone soared above the canyon.")

    # 6
    def test_file_naming_convention(self):
        """Verify file names match {agent_type}_training_*.jsonl pattern."""
        collector = self._make_collector(enabled=True)
        response = _mock_mistral_response("ok")

        collector.record_agent_interaction(
            agent_id="drone-mistral",
            agent_type="drone",
            messages=[{"role": "user", "content": "scan"}],
            tools=[],
            response=response,
        )

        files = list(Path(self.data_dir).glob("*.jsonl"))
        self.assertEqual(len(files), 1)
        filename = files[0].name
        self.assertTrue(filename.startswith("drone_training_"))
        self.assertTrue(filename.endswith(".jsonl"))

    # 7
    def test_auto_creates_directory(self):
        """Verify output directory is auto-created on first write."""
        nested_dir = os.path.join(self.data_dir, "deep", "nested", "dir")
        with patch("app.training.settings") as mock_settings:
            mock_settings.training_data_enabled = True
            mock_settings.training_data_dir = nested_dir
            from app.training import TrainingDataCollector

            collector = TrainingDataCollector()

        response = _mock_mistral_response("ok")
        collector.record_agent_interaction(
            agent_id="rover-1",
            agent_type="rover",
            messages=[{"role": "user", "content": "go"}],
            tools=[],
            response=response,
        )

        self.assertTrue(os.path.isdir(nested_dir))
        files = list(Path(nested_dir).glob("*.jsonl"))
        self.assertEqual(len(files), 1)

    # 8
    def test_multiple_recordings_append(self):
        """Call record multiple times, verify all lines in same file."""
        collector = self._make_collector(enabled=True)
        response = _mock_mistral_response("ok")

        for i in range(5):
            collector.record_agent_interaction(
                agent_id="rover-mistral",
                agent_type="rover",
                messages=[{"role": "user", "content": f"action {i}"}],
                tools=[],
                response=response,
            )

        files = list(Path(self.data_dir).glob("rover_training_*.jsonl"))
        self.assertEqual(len(files), 1)

        with open(files[0]) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 5)

        # Verify each line is valid JSON
        for line in lines:
            data = json.loads(line)
            self.assertIn("messages", data)

    # 9
    def test_different_agent_types_separate_files(self):
        """Record rover and drone, verify separate files."""
        collector = self._make_collector(enabled=True)
        response = _mock_mistral_response("ok")

        collector.record_agent_interaction(
            agent_id="rover-mistral",
            agent_type="rover",
            messages=[{"role": "user", "content": "move"}],
            tools=[],
            response=response,
        )
        collector.record_agent_interaction(
            agent_id="drone-mistral",
            agent_type="drone",
            messages=[{"role": "user", "content": "scan"}],
            tools=[],
            response=response,
        )

        rover_files = list(Path(self.data_dir).glob("rover_training_*.jsonl"))
        drone_files = list(Path(self.data_dir).glob("drone_training_*.jsonl"))
        self.assertEqual(len(rover_files), 1)
        self.assertEqual(len(drone_files), 1)
        self.assertNotEqual(rover_files[0].name, drone_files[0].name)

    # 10
    def test_thread_safety(self):
        """Use ThreadPoolExecutor to record 20 interactions simultaneously."""
        collector = self._make_collector(enabled=True)
        response = _mock_mistral_response("concurrent")

        def record_one(idx):
            collector.record_agent_interaction(
                agent_id=f"rover-{idx}",
                agent_type="rover",
                messages=[{"role": "user", "content": f"action {idx}"}],
                tools=[],
                response=response,
            )
            return idx

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(record_one, i) for i in range(20)]
            results = [f.result() for f in as_completed(futures)]

        self.assertEqual(len(results), 20)

        files = list(Path(self.data_dir).glob("rover_training_*.jsonl"))
        self.assertEqual(len(files), 1)

        with open(files[0]) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 20)

        # Verify no data corruption — each line must be valid JSON
        for line in lines:
            data = json.loads(line)
            self.assertIn("messages", data)
