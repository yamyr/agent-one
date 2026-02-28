"""Tests for app.narrator — event filtering, prompt building, dialogue parsing, narrator lifecycle."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.narrator import (
    INTERESTING_EVENTS,
    Narrator,
    _build_narration_prompt,
    _is_interesting,
    _parse_dialogue,
    _strip_audio_tags,
)


class TestIsInteresting(unittest.TestCase):
    """Test event filtering logic."""

    def test_known_event_returns_weight(self):
        for name, expected_weight in INTERESTING_EVENTS.items():
            if name in ("thinking", "move"):
                continue  # special cases tested separately
            event = {"name": name, "payload": {}}
            self.assertEqual(
                _is_interesting(event),
                expected_weight,
                f"Event '{name}' should have weight {expected_weight}",
            )

    def test_unknown_event_returns_zero(self):
        self.assertEqual(_is_interesting({"name": "random_noise", "payload": {}}), 0)

    def test_empty_name_returns_zero(self):
        self.assertEqual(_is_interesting({"payload": {}}), 0)

    def test_move_always_returns_zero(self):
        """Move events are handled by batching, not individual filtering."""
        self.assertEqual(_is_interesting({"name": "move", "payload": {}}), 0)

    def test_thinking_with_keyword_returns_weight(self):
        event = {
            "name": "thinking",
            "payload": {"text": "Battery is getting low, should return to station"},
        }
        self.assertGreater(_is_interesting(event), 0)

    def test_thinking_without_keyword_returns_zero(self):
        event = {
            "name": "thinking",
            "payload": {"text": "Moving north to explore new terrain"},
        }
        self.assertEqual(_is_interesting(event), 0)

    def test_thinking_keyword_case_insensitive(self):
        event = {
            "name": "thinking",
            "payload": {"text": "STORM approaching from the west!"},
        }
        self.assertGreater(_is_interesting(event), 0)

    def test_mission_success_has_max_weight(self):
        self.assertEqual(_is_interesting({"name": "mission_success", "payload": {}}), 3)

    def test_mission_failed_has_max_weight(self):
        self.assertEqual(_is_interesting({"name": "mission_failed", "payload": {}}), 3)


class TestBuildNarrationPrompt(unittest.TestCase):
    """Test prompt construction from event batches."""

    def test_check_event_formats_stone(self):
        events = [
            {
                "source": "rover",
                "name": "check",
                "payload": {
                    "stone": {"type": "core"},
                },
            }
        ]
        prompt = _build_narration_prompt(events, "Mission: active")
        self.assertIn("rover", prompt)
        self.assertIn("core", prompt)

    def test_thinking_event_truncates(self):
        long_text = "x" * 300
        events = [
            {
                "source": "rover",
                "name": "thinking",
                "payload": {"text": long_text},
            }
        ]
        prompt = _build_narration_prompt(events, "")
        # Should truncate to 150 chars
        self.assertNotIn("x" * 300, prompt)
        self.assertIn("x" * 150, prompt)

    def test_assign_mission_event(self):
        events = [
            {
                "source": "station",
                "name": "assign_mission",
                "payload": {
                    "agent_id": "rover",
                    "objective": "Collect 3 core stones",
                },
            }
        ]
        prompt = _build_narration_prompt(events, "")
        self.assertIn("Station assigned mission", prompt)
        self.assertIn("Collect 3 core stones", prompt)

    def test_charge_rover_event(self):
        events = [
            {
                "source": "station",
                "name": "charge_rover",
                "payload": {"battery_before": 0.3, "battery_after": 1.0},
            }
        ]
        prompt = _build_narration_prompt(events, "")
        self.assertIn("charged", prompt)
        self.assertIn("30%", prompt)
        self.assertIn("100%", prompt)

    def test_mission_success_event(self):
        events = [{"source": "world", "name": "mission_success", "payload": {}}]
        prompt = _build_narration_prompt(events, "")
        self.assertIn("MISSION SUCCESS", prompt)

    def test_mission_failed_event(self):
        events = [
            {
                "source": "world",
                "name": "mission_failed",
                "payload": {"reason": "battery depleted"},
            }
        ]
        prompt = _build_narration_prompt(events, "")
        self.assertIn("MISSION FAILED", prompt)
        self.assertIn("battery depleted", prompt)

    def test_world_summary_included(self):
        prompt = _build_narration_prompt([], "Mission status: active\nRover: pos=(5,5)")
        self.assertIn("Mission status: active", prompt)
        self.assertIn("Rover: pos=(5,5)", prompt)

    def test_dig_event(self):
        events = [
            {
                "source": "rover",
                "name": "dig",
                "payload": {
                    "position": [3, 7],
                    "stone": {"type": "basalt"},
                },
            }
        ]
        prompt = _build_narration_prompt(events, "")
        self.assertIn("dig", prompt)
        self.assertIn("basalt", prompt)

    def test_multiple_events_combined(self):
        events = [
            {
                "source": "rover",
                "name": "check",
                "payload": {"stone": {"type": "core"}},
            },
            {
                "source": "station",
                "name": "alert",
                "payload": {"message": "Low power warning"},
            },
        ]
        prompt = _build_narration_prompt(events, "")
        self.assertIn("core", prompt)
        self.assertIn("Low power warning", prompt)


class TestNarrator(unittest.IsolatedAsyncioTestCase):
    """Test Narrator class lifecycle and event feeding."""

    def setUp(self):
        self.broadcast = AsyncMock()
        self.narrator = Narrator(broadcast_fn=self.broadcast)

    def tearDown(self):
        self.narrator.stop()

    def test_initial_state(self):
        self.assertFalse(self.narrator.enabled)
        self.assertEqual(len(self.narrator._event_buffer), 0)

    def test_toggle_enabled(self):
        self.narrator.enabled = False
        self.assertFalse(self.narrator.enabled)
        self.narrator.enabled = True
        self.assertTrue(self.narrator.enabled)

    async def test_feed_drops_when_disabled(self):
        """When narration is disabled, events are silently dropped."""
        self.narrator.enabled = False
        await self.narrator.feed({"name": "dig", "payload": {}})
        self.assertEqual(len(self.narrator._event_buffer), 0)

    async def test_feed_drops_without_api_key(self):
        """Without API key, narration defaults to disabled — events dropped."""
        narrator = Narrator(broadcast_fn=self.broadcast)
        await narrator.feed({"name": "dig", "payload": {}})
        self.assertEqual(len(narrator._event_buffer), 0)

    async def test_feed_skips_uninteresting_event(self):
        self.narrator._enabled = True
        # Patch settings to have an API key
        with patch("app.narrator.settings") as ms:
            ms.elevenlabs_api_key = "test-key"
            ms.narration_enabled = True
            ms.narration_min_interval_seconds = 60
            narrator = Narrator(broadcast_fn=self.broadcast)
            narrator._enabled = True
            await narrator.feed({"name": "unknown_event", "payload": {}})
            self.assertEqual(len(narrator._event_buffer), 0)

    async def test_feed_buffers_interesting_event(self):
        with patch("app.narrator.settings") as ms:
            ms.elevenlabs_api_key = "test-key"
            ms.narration_enabled = True
            ms.narration_min_interval_seconds = 999  # prevent immediate fire
            narrator = Narrator(broadcast_fn=self.broadcast)
            narrator._enabled = True
            narrator._task = MagicMock()  # fake running task
            narrator._last_narration_time = float("inf")  # prevent scheduling
            await narrator.feed({"name": "dig", "payload": {}})
            self.assertEqual(len(narrator._event_buffer), 1)

    def test_reset_clears_buffer(self):
        self.narrator._event_buffer = [{"name": "dig"}]
        self.narrator._last_narration_time = 100
        self.narrator.reset()
        self.assertEqual(len(self.narrator._event_buffer), 0)
        self.assertEqual(self.narrator._last_narration_time, 0)

    async def test_start_creates_task(self):
        self.narrator.start()
        self.assertIsNotNone(self.narrator._task)
        self.assertTrue(self.narrator._running)

    async def test_stop_cancels_task(self):
        self.narrator.start()
        self.narrator.stop()
        self.assertIsNone(self.narrator._task)
        self.assertFalse(self.narrator._running)

    async def test_start_idempotent(self):
        self.narrator.start()
        task1 = self.narrator._task
        self.narrator.start()
        task2 = self.narrator._task
        self.assertIs(task1, task2)

    async def test_streaming_skips_empty_choices(self):
        """Events with empty choices array should be skipped without error."""
        with patch("app.narrator.settings") as ms:
            ms.elevenlabs_api_key = "test-key"
            ms.narration_model = "test-model"
            narrator = Narrator(broadcast_fn=self.broadcast)

            # Build fake stream events
            empty_event = MagicMock()
            empty_event.data.choices = []  # empty choices

            normal_event = MagicMock()
            normal_event.data.choices = [MagicMock()]
            normal_event.data.choices[0].delta.content = "Hello Mars!"

            mock_client = MagicMock()
            mock_client.chat.stream.return_value = [empty_event, normal_event]

            with patch.object(narrator, "_get_mistral", return_value=mock_client):
                result = await narrator._generate_text_streaming("test prompt")
            self.assertEqual(result, "Hello Mars!")


class TestParseDialogue(unittest.TestCase):
    """Test dialogue parsing from LLM output."""

    def test_basic_dialogue(self):
        text = (
            "COMMANDER REX: Well, our rover just hit a new zone.\n"
            "DR. NOVA: Exciting! Let's see what we find."
        )
        result = _parse_dialogue(text)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], ("COMMANDER REX", "Well, our rover just hit a new zone."))
        self.assertEqual(result[1], ("DR. NOVA", "Exciting! Let's see what we find."))

    def test_empty_text_returns_empty(self):
        self.assertEqual(_parse_dialogue(""), [])

    def test_no_speakers_returns_empty(self):
        self.assertEqual(_parse_dialogue("Just some random text without labels."), [])

    def test_single_speaker(self):
        text = "COMMANDER REX: Solo line here."
        result = _parse_dialogue(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "COMMANDER REX")

    def test_case_insensitive_speakers(self):
        text = "commander rex: lowercase works\ndr. nova: also lowercase"
        result = _parse_dialogue(text)
        self.assertEqual(len(result), 2)
        # Should normalize to uppercase
        self.assertEqual(result[0][0], "COMMANDER REX")
        self.assertEqual(result[1][0], "DR. NOVA")

    def test_dr_nova_without_period(self):
        text = "DR NOVA: No period variant."
        result = _parse_dialogue(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "DR. NOVA")

    def test_audio_tags_preserved_in_parse(self):
        """Parsing should preserve audio tags — stripping happens separately."""
        text = "COMMANDER REX: [laughs] That's a good one."
        result = _parse_dialogue(text)
        self.assertEqual(len(result), 1)
        self.assertIn("[laughs]", result[0][1])

    def test_multiline_dialogue(self):
        text = (
            "COMMANDER REX: First line.\n"
            "DR. NOVA: Second line.\n"
            "COMMANDER REX: Third line.\n"
            "DR. NOVA: Fourth line."
        )
        result = _parse_dialogue(text)
        self.assertEqual(len(result), 4)


class TestStripAudioTags(unittest.TestCase):
    """Test audio tag stripping for text display."""

    def test_strips_laughs(self):
        self.assertEqual(_strip_audio_tags("[laughs] That's funny"), "That's funny")

    def test_strips_multiple_tags(self):
        text = "[sighs] Well [clears throat] let me think [gasps] wow!"
        result = _strip_audio_tags(text)
        self.assertEqual(result, "Well let me think wow!")

    def test_strips_whispers(self):
        self.assertEqual(_strip_audio_tags("[whispers] Can you hear me?"), "Can you hear me?")

    def test_no_tags_unchanged(self):
        text = "Just normal text here."
        self.assertEqual(_strip_audio_tags(text), text)

    def test_case_insensitive(self):
        self.assertEqual(_strip_audio_tags("[LAUGHS] funny"), "funny")

    def test_collapses_double_spaces(self):
        text = "Before [sighs] after"
        result = _strip_audio_tags(text)
        self.assertNotIn("  ", result)
