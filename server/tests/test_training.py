"""Tests for TrainingDataCollector."""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch


def _mock_response(content=None, tool_calls=None):
    """Create a mock Mistral chat response."""
    choice = MagicMock()
    choice.message.content = content
    choice.message.tool_calls = tool_calls
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _mock_tool_call(name, arguments, call_id="call_1"):
    """Create a mock tool call object."""
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = name
    tc.function.arguments = json.dumps(arguments)
    return tc


class TestTrainingDataCollector(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        patcher = patch("app.training.settings")
        self.mock_settings = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_settings.training_data_enabled = True
        self.mock_settings.training_data_dir = self.tmpdir

        # Re-import to get a fresh collector with patched settings
        from app.training import TrainingDataCollector

        self.collector = TrainingDataCollector()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_record_agent_interaction_writes_jsonl(self):
        messages = [
            {"role": "system", "content": "You are a rover."},
            {"role": "user", "content": "Move north."},
        ]
        tc = _mock_tool_call("move", {"direction": "north"})
        response = _mock_response(content="Moving north.", tool_calls=[tc])

        self.collector.record_agent_interaction(
            agent_id="rover-1",
            agent_type="rover",
            messages=messages,
            tools=[],
            response=response,
        )

        # Check file was written
        files = os.listdir(self.tmpdir)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].startswith("rover_training_"))

        with open(os.path.join(self.tmpdir, files[0])) as f:
            record = json.loads(f.readline())

        self.assertIn("messages", record)
        # system + user + assistant + tool = 4 messages
        self.assertEqual(len(record["messages"]), 4)
        self.assertEqual(record["messages"][2]["role"], "assistant")
        self.assertEqual(record["messages"][2]["content"], "Moving north.")
        self.assertIn("tool_calls", record["messages"][2])
        self.assertEqual(record["messages"][3]["role"], "tool")

    def test_record_agent_interaction_no_tool_calls(self):
        messages = [{"role": "user", "content": "Hello"}]
        response = _mock_response(content="Hi there.", tool_calls=None)

        self.collector.record_agent_interaction(
            agent_id="rover-1",
            agent_type="rover",
            messages=messages,
            tools=[],
            response=response,
        )

        files = os.listdir(self.tmpdir)
        self.assertEqual(len(files), 1)
        with open(os.path.join(self.tmpdir, files[0])) as f:
            record = json.loads(f.readline())
        # user + assistant = 2 messages, no tool message
        self.assertEqual(len(record["messages"]), 2)
        self.assertNotIn("tool_calls", record["messages"][1])

    def test_record_narration_interaction_writes_jsonl(self):
        messages = [
            {"role": "system", "content": "You are a narrator."},
            {"role": "user", "content": "Narrate."},
        ]
        self.collector.record_narration_interaction(messages, "The rover moved north.")

        files = os.listdir(self.tmpdir)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].startswith("narration_training_"))

        with open(os.path.join(self.tmpdir, files[0])) as f:
            record = json.loads(f.readline())
        self.assertEqual(len(record["messages"]), 3)
        self.assertEqual(record["messages"][2]["role"], "assistant")
        self.assertEqual(record["messages"][2]["content"], "The rover moved north.")

    def test_disabled_collector_does_not_write(self):
        self.collector._enabled = False
        messages = [{"role": "user", "content": "Hello"}]
        response = _mock_response(content="Hi.")

        self.collector.record_agent_interaction("r1", "rover", messages, [], response)
        self.collector.record_narration_interaction(messages, "Hi.")

        files = [f for f in os.listdir(self.tmpdir) if f.endswith(".jsonl")]
        self.assertEqual(len(files), 0)

    def test_get_stats_returns_correct_counts(self):
        messages = [{"role": "user", "content": "Go"}]
        response = _mock_response(content="Going.", tool_calls=None)

        self.collector.record_agent_interaction("r1", "rover", messages, [], response)
        self.collector.record_agent_interaction("r1", "rover", messages, [], response)
        self.collector.record_narration_interaction(messages, "Narrating.")

        stats = self.collector.get_stats()
        self.assertEqual(len(stats), 2)  # rover + narration files
        rover_file = [k for k in stats if k.startswith("rover_")][0]
        self.assertEqual(stats[rover_file]["samples"], 2)

    def test_multiple_agent_types_separate_files(self):
        messages = [{"role": "user", "content": "Go"}]
        response = _mock_response(content="Ok.", tool_calls=None)

        self.collector.record_agent_interaction("r1", "rover", messages, [], response)
        self.collector.record_agent_interaction("d1", "drone", messages, [], response)
        self.collector.record_agent_interaction("s1", "station", messages, [], response)

        files = os.listdir(self.tmpdir)
        self.assertEqual(len(files), 3)
        prefixes = sorted(f.split("_training_")[0] for f in files)
        self.assertEqual(prefixes, ["drone", "rover", "station"])

    def test_tool_call_with_string_arguments(self):
        """Ensure string arguments are parsed to dict then re-serialized."""
        tc = _mock_tool_call("drill", {"depth": 5})
        response = _mock_response(content=None, tool_calls=[tc])
        messages = [{"role": "user", "content": "Drill."}]

        self.collector.record_agent_interaction("r1", "rover", messages, [], response)

        files = os.listdir(self.tmpdir)
        with open(os.path.join(self.tmpdir, files[0])) as f:
            record = json.loads(f.readline())
        tc_data = record["messages"][1]["tool_calls"][0]
        self.assertEqual(tc_data["function"]["name"], "drill")
        # arguments should be a JSON string
        args = json.loads(tc_data["function"]["arguments"])
        self.assertEqual(args["depth"], 5)

    def test_record_does_not_crash_on_bad_response(self):
        """Ensure recording doesn't crash the caller on malformed response."""
        bad_response = MagicMock()
        bad_response.choices = []  # No choices — will IndexError

        # Should log but not raise
        self.collector.record_agent_interaction(
            "r1", "rover", [{"role": "user", "content": "x"}], [], bad_response
        )
        # No crash = pass
