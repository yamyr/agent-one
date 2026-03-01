"""Tests for app.narrator — event filtering, prompt building, dialogue parsing, narrator lifecycle."""

import asyncio
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

    def test_charge_agent_event(self):
        events = [
            {
                "source": "station",
                "name": "charge_agent",
                "payload": {
                    "agent_id": "rover-mistral",
                    "battery_before": 0.3,
                    "battery_after": 1.0,
                },
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
        self.assertTrue(self.narrator.enabled)
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
        """Without API key, narration is enabled by config default but events still buffer."""
        narrator = Narrator(broadcast_fn=self.broadcast)
        # With narration_enabled=True (config default), events are buffered
        # even without an API key — TTS errors are handled at generation time
        await narrator.feed({"name": "dig", "payload": {}})
        self.assertEqual(len(narrator._event_buffer), 1)

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


class TestAsyncStreaming(unittest.IsolatedAsyncioTestCase):
    """Test that _generate_text_streaming uses async iteration correctly."""

    def setUp(self):
        self.broadcast = AsyncMock()
        self.narrator = Narrator(broadcast_fn=self.broadcast)
        self.narrator._enabled = True

    def tearDown(self):
        self.narrator.stop()

    async def test_stream_async_called(self):
        """Verify stream_async (not sync stream) is invoked."""

        async def _fake_stream():
            event = MagicMock()
            event.data.choices = [MagicMock()]
            event.data.choices[0].delta.content = "Hello"
            yield event

        mock_client = MagicMock()
        mock_client.chat.stream_async = AsyncMock(return_value=_fake_stream())
        self.narrator._mistral = mock_client

        result = await self.narrator._generate_text_streaming("test prompt")

        mock_client.chat.stream_async.assert_awaited_once()
        self.assertEqual(result, "Hello")

    async def test_full_text_accumulated(self):
        """All chunks should be concatenated into the final return value."""

        async def _multi_chunk_stream():
            for text in ["The ", "rover ", "drills."]:
                event = MagicMock()
                event.data.choices = [MagicMock()]
                event.data.choices[0].delta.content = text
                yield event

        mock_client = MagicMock()
        mock_client.chat.stream_async = AsyncMock(return_value=_multi_chunk_stream())
        self.narrator._mistral = mock_client

        result = await self.narrator._generate_text_streaming("test")
        self.assertEqual(result, "The rover drills.")

    async def test_empty_stream_returns_none(self):
        """An empty stream (no events) should return None."""

        async def _empty():
            return
            yield  # noqa: unreachable

        mock_client = MagicMock()
        mock_client.chat.stream_async = AsyncMock(return_value=_empty())
        self.narrator._mistral = mock_client

        result = await self.narrator._generate_text_streaming("test")
        self.assertIsNone(result)

    async def test_none_content_chunks_skipped(self):
        """Chunks where delta.content is None should be skipped."""

        async def _stream_with_none():
            none_event = MagicMock()
            none_event.data.choices = [MagicMock()]
            none_event.data.choices[0].delta.content = None
            yield none_event

            real_event = MagicMock()
            real_event.data.choices = [MagicMock()]
            real_event.data.choices[0].delta.content = "Real content"
            yield real_event

        mock_client = MagicMock()
        mock_client.chat.stream_async = AsyncMock(return_value=_stream_with_none())
        self.narrator._mistral = mock_client

        result = await self.narrator._generate_text_streaming("test")
        self.assertEqual(result, "Real content")

    async def test_streaming_skips_empty_choices(self):
        """Events with empty choices array should be skipped without error."""

        async def _stream_with_empty():
            empty_event = MagicMock()
            empty_event.data.choices = []
            yield empty_event

            normal_event = MagicMock()
            normal_event.data.choices = [MagicMock()]
            normal_event.data.choices[0].delta.content = "Hello Mars!"
            yield normal_event

        mock_client = MagicMock()
        mock_client.chat.stream_async = AsyncMock(return_value=_stream_with_empty())
        self.narrator._mistral = mock_client

        result = await self.narrator._generate_text_streaming("test prompt")
        self.assertEqual(result, "Hello Mars!")


class TestStreamingChunkBehavior(unittest.IsolatedAsyncioTestCase):
    """Verify chunk broadcast semantics during async streaming."""

    def setUp(self):
        self.broadcast = AsyncMock()
        self.narrator = Narrator(broadcast_fn=self.broadcast)
        self.narrator._enabled = True

    def tearDown(self):
        self.narrator.stop()

    async def test_chunks_broadcast_in_order(self):
        """Each chunk should be broadcast as a narration_chunk event in order."""
        chunks = ["First ", "second ", "third."]

        async def _ordered_stream():
            for text in chunks:
                event = MagicMock()
                event.data.choices = [MagicMock()]
                event.data.choices[0].delta.content = text
                yield event

        mock_client = MagicMock()
        mock_client.chat.stream_async = AsyncMock(return_value=_ordered_stream())
        self.narrator._mistral = mock_client

        await self.narrator._generate_text_streaming("test")

        self.assertEqual(self.broadcast.await_count, len(chunks))
        for i, call in enumerate(self.broadcast.await_args_list):
            payload = call[0][0]
            self.assertEqual(payload["name"], "narration_chunk")
            self.assertEqual(payload["payload"]["text"], _strip_audio_tags(chunks[i]))

    async def test_broadcast_event_schema(self):
        """Broadcast events should have the correct structure."""

        async def _single_chunk():
            event = MagicMock()
            event.data.choices = [MagicMock()]
            event.data.choices[0].delta.content = "Test chunk"
            yield event

        mock_client = MagicMock()
        mock_client.chat.stream_async = AsyncMock(return_value=_single_chunk())
        self.narrator._mistral = mock_client

        await self.narrator._generate_text_streaming("test")

        payload = self.broadcast.await_args_list[0][0][0]
        self.assertEqual(payload["source"], "narrator")
        self.assertEqual(payload["type"], "narration")
        self.assertEqual(payload["name"], "narration_chunk")
        self.assertIn("text", payload["payload"])

    async def test_audio_tags_stripped_in_chunks(self):
        """Audio tags should be stripped from broadcast chunks."""

        async def _tagged_stream():
            event = MagicMock()
            event.data.choices = [MagicMock()]
            event.data.choices[0].delta.content = "[laughs] That's funny"
            yield event

        mock_client = MagicMock()
        mock_client.chat.stream_async = AsyncMock(return_value=_tagged_stream())
        self.narrator._mistral = mock_client

        await self.narrator._generate_text_streaming("test")

        payload = self.broadcast.await_args_list[0][0][0]
        self.assertNotIn("[laughs]", payload["payload"]["text"])


class TestStreamingEventLoopBehavior(unittest.IsolatedAsyncioTestCase):
    """Verify the event loop remains responsive during narration streaming."""

    def setUp(self):
        self.broadcast = AsyncMock()
        self.narrator = Narrator(broadcast_fn=self.broadcast)
        self.narrator._enabled = True

    def tearDown(self):
        self.narrator.stop()

    async def test_event_loop_not_blocked(self):
        """Verify other coroutines can run while streaming is in progress."""
        loop_ran = False

        async def _slow_stream():
            nonlocal loop_ran
            for text in ["Chunk1", "Chunk2", "Chunk3"]:
                await asyncio.sleep(0.01)
                event = MagicMock()
                event.data.choices = [MagicMock()]
                event.data.choices[0].delta.content = text
                yield event

        async def _concurrent_task():
            nonlocal loop_ran
            await asyncio.sleep(0.005)
            loop_ran = True

        mock_client = MagicMock()
        mock_client.chat.stream_async = AsyncMock(return_value=_slow_stream())
        self.narrator._mistral = mock_client

        result, _ = await asyncio.gather(
            self.narrator._generate_text_streaming("test"),
            _concurrent_task(),
        )

        self.assertTrue(loop_ran, "Event loop was blocked")
        self.assertEqual(result, "Chunk1Chunk2Chunk3")


class TestStreamingErrorHandling(unittest.IsolatedAsyncioTestCase):
    """Verify streaming error paths don't crash the narrator."""

    def setUp(self):
        self.broadcast = AsyncMock()
        self.narrator = Narrator(broadcast_fn=self.broadcast)
        self.narrator._enabled = True

    def tearDown(self):
        self.narrator.stop()

    async def test_stream_async_exception_returns_none(self):
        """If stream_async raises, return None gracefully."""
        mock_client = MagicMock()
        mock_client.chat.stream_async = AsyncMock(side_effect=RuntimeError("API connection failed"))
        self.narrator._mistral = mock_client

        result = await self.narrator._generate_text_streaming("test prompt")

        self.assertIsNone(result)
        self.broadcast.assert_not_awaited()

    async def test_partial_stream_then_error_returns_none(self):
        """If stream fails mid-iteration, return None."""

        async def _failing_stream():
            event = MagicMock()
            event.data.choices = [MagicMock()]
            event.data.choices[0].delta.content = "Partial text"
            yield event
            raise ConnectionError("Stream interrupted")

        mock_client = MagicMock()
        mock_client.chat.stream_async = AsyncMock(return_value=_failing_stream())
        self.narrator._mistral = mock_client

        result = await self.narrator._generate_text_streaming("test prompt")
        self.assertIsNone(result)

    async def test_error_does_not_propagate(self):
        """Streaming errors must be caught, not propagated."""
        mock_client = MagicMock()
        mock_client.chat.stream_async = AsyncMock(side_effect=Exception("Unexpected error"))
        self.narrator._mistral = mock_client

        result = await self.narrator._generate_text_streaming("test prompt")
        self.assertIsNone(result)


class TestProcessBatchStreaming(unittest.IsolatedAsyncioTestCase):
    """Test the full batch pipeline uses async streaming."""

    def setUp(self):
        self.broadcast = AsyncMock()
        self.narrator = Narrator(broadcast_fn=self.broadcast)
        self.narrator._enabled = True

    def tearDown(self):
        self.narrator.stop()

    @patch("app.narrator.settings")
    async def test_process_batch_uses_streaming(self, mock_settings):
        """_process_batch should call _generate_text_streaming first."""
        mock_settings.narration_model = "test-model"
        mock_settings.mistral_api_key = "test-key"
        mock_settings.narration_min_interval_seconds = 60

        dialogue = "COMMANDER REX: Test line.\nDR. NOVA: Response."

        self.narrator._generate_text_streaming = AsyncMock(return_value=dialogue)
        self.narrator._event_buffer = [{"name": "dig", "source": "rover", "payload": {}}]

        with patch("app.world.world") as mock_world:
            mock_world.get_agents.return_value = {}
            mock_world.get_mission.return_value = {"status": "active"}
            await self.narrator._process_batch()

        self.narrator._generate_text_streaming.assert_awaited_once()

    @patch("app.narrator.settings")
    async def test_process_batch_falls_back_on_streaming_failure(self, mock_settings):
        """When streaming returns None, fall back to non-streaming."""
        mock_settings.narration_model = "test-model"
        mock_settings.mistral_api_key = "test-key"
        mock_settings.narration_min_interval_seconds = 60

        self.narrator._generate_text_streaming = AsyncMock(return_value=None)
        self.narrator._generate_text = MagicMock(return_value="COMMANDER REX: Fallback text.")
        self.narrator._event_buffer = [{"name": "dig", "source": "rover", "payload": {}}]

        with patch("app.world.world") as mock_world:
            mock_world.get_agents.return_value = {}
            mock_world.get_mission.return_value = {"status": "active"}
            await self.narrator._process_batch()

        self.narrator._generate_text_streaming.assert_awaited_once()
