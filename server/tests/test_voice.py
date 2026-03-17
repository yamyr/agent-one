"""Tests for app.voice — Voxtral transcription + command parsing."""

import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.voice import (
    COMMAND_PARSE_SYSTEM_PROMPT,
    CONTEXT_BIAS_TERMS,
    SUPPORTED_AUDIO_TYPES,
    VoiceCommandProcessor,
)


class TestSupportedAudioTypes(unittest.TestCase):
    """Test audio format validation constants."""

    def test_mp3_supported(self):
        self.assertIn("audio/mpeg", SUPPORTED_AUDIO_TYPES)
        self.assertIn("audio/mp3", SUPPORTED_AUDIO_TYPES)

    def test_wav_supported(self):
        self.assertIn("audio/wav", SUPPORTED_AUDIO_TYPES)
        self.assertIn("audio/x-wav", SUPPORTED_AUDIO_TYPES)

    def test_flac_supported(self):
        self.assertIn("audio/flac", SUPPORTED_AUDIO_TYPES)

    def test_ogg_supported(self):
        self.assertIn("audio/ogg", SUPPORTED_AUDIO_TYPES)

    def test_webm_supported(self):
        self.assertIn("audio/webm", SUPPORTED_AUDIO_TYPES)


class TestContextBiasTerms(unittest.TestCase):
    """Test Mars domain terms for transcription context bias."""

    def test_contains_core_terms(self):
        for term in ["rover", "drone", "station", "mars", "basalt", "mission"]:
            self.assertIn(term, CONTEXT_BIAS_TERMS, f"Missing term: {term}")

    def test_contains_action_terms(self):
        for term in ["drill", "scan", "navigate", "abort", "recall"]:
            self.assertIn(term, CONTEXT_BIAS_TERMS, f"Missing term: {term}")


class TestVoiceCommandProcessorInit(unittest.TestCase):
    """Test VoiceCommandProcessor initialization."""

    def test_client_starts_none(self):
        processor = VoiceCommandProcessor()
        self.assertIsNone(processor._client)

    @patch("app.llm.settings")
    def test_get_client_raises_without_api_key(self, mock_settings):
        mock_settings.mistral_api_key = ""
        processor = VoiceCommandProcessor()
        with self.assertRaises(RuntimeError) as ctx:
            processor._get_client()
        self.assertIn("MISTRAL_API_KEY", str(ctx.exception))

    @patch("app.voice.get_mistral_client")
    def test_get_client_creates_client(self, mock_get_mistral_client):
        processor = VoiceCommandProcessor()
        client = processor._get_client()
        mock_get_mistral_client.assert_called_once_with()
        self.assertEqual(client, mock_get_mistral_client.return_value)

    @patch("app.voice.get_mistral_client")
    def test_get_client_caches(self, mock_get_mistral_client):
        processor = VoiceCommandProcessor()
        client1 = processor._get_client()
        client2 = processor._get_client()
        self.assertIs(client1, client2)
        mock_get_mistral_client.assert_called_once()


class TestTranscribe(unittest.IsolatedAsyncioTestCase):
    """Test audio transcription via Voxtral."""

    @patch("app.voice.settings")
    @patch("app.voice.get_mistral_client")
    async def test_transcribe_success(self, mock_get_mistral_client, mock_settings):
        mock_settings.voice_transcription_model = "voxtral-mini-latest"

        # Mock transcription response
        mock_response = MagicMock()
        mock_response.text = "Recall rover one immediately"
        mock_response.language = "en"
        mock_response.model = "voxtral-mini-2602"

        mock_client = MagicMock()
        mock_client.audio.transcriptions.complete_async = AsyncMock(return_value=mock_response)
        mock_get_mistral_client.return_value = mock_client

        processor = VoiceCommandProcessor()
        result = await processor.transcribe(b"fake-audio-data", "test.wav")

        self.assertEqual(result["text"], "Recall rover one immediately")
        self.assertEqual(result["language"], "en")
        self.assertEqual(result["model"], "voxtral-mini-2602")

        # Verify correct API call
        mock_client.audio.transcriptions.complete_async.assert_called_once()
        call_kwargs = mock_client.audio.transcriptions.complete_async.call_args[1]
        self.assertEqual(call_kwargs["model"], "voxtral-mini-latest")
        self.assertEqual(call_kwargs["language"], "en")
        self.assertEqual(call_kwargs["context_bias"], CONTEXT_BIAS_TERMS)

    @patch("app.voice.settings")
    @patch("app.voice.get_mistral_client")
    async def test_transcribe_custom_language(self, mock_get_mistral_client, mock_settings):
        mock_settings.voice_transcription_model = "voxtral-mini-latest"

        mock_response = MagicMock()
        mock_response.text = "Rappeler le rover"
        mock_response.language = "fr"
        mock_response.model = "voxtral-mini-2602"

        mock_client = MagicMock()
        mock_client.audio.transcriptions.complete_async = AsyncMock(return_value=mock_response)
        mock_get_mistral_client.return_value = mock_client

        processor = VoiceCommandProcessor()
        result = await processor.transcribe(b"fake-audio", "test.wav", language="fr")

        self.assertEqual(result["language"], "fr")
        call_kwargs = mock_client.audio.transcriptions.complete_async.call_args[1]
        self.assertEqual(call_kwargs["language"], "fr")


class TestParseCommand(unittest.IsolatedAsyncioTestCase):
    """Test LLM-based command parsing from transcript."""

    def _make_processor_with_mock(self, llm_response_text):
        """Helper to create a processor with a mocked LLM client."""
        mock_choice = MagicMock()
        mock_choice.message.content = llm_response_text

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.complete_async = AsyncMock(return_value=mock_response)

        processor = VoiceCommandProcessor()
        processor._client = mock_client
        return processor, mock_client

    async def test_parse_recall_command(self):
        llm_output = json.dumps(
            {
                "command": "recall_rover",
                "params": {"rover_id": "rover-mistral"},
                "confidence": 0.95,
            }
        )
        processor, _ = self._make_processor_with_mock(llm_output)
        result = await processor.parse_command("Recall rover one immediately")

        self.assertEqual(result["command"], "recall_rover")
        self.assertEqual(result["params"]["rover_id"], "rover-mistral")
        self.assertAlmostEqual(result["confidence"], 0.95)

    async def test_parse_abort_command(self):
        llm_output = json.dumps(
            {
                "command": "abort_mission",
                "params": {"reason": "Critical failure"},
                "confidence": 0.9,
            }
        )
        processor, _ = self._make_processor_with_mock(llm_output)
        result = await processor.parse_command("Abort the mission, critical failure")

        self.assertEqual(result["command"], "abort_mission")
        self.assertEqual(result["params"]["reason"], "Critical failure")

    async def test_parse_general_message(self):
        llm_output = json.dumps(
            {
                "command": "general_message",
                "params": {"message": "How are things going?"},
                "confidence": 0.6,
            }
        )
        processor, _ = self._make_processor_with_mock(llm_output)
        result = await processor.parse_command("How are things going?")

        self.assertEqual(result["command"], "general_message")
        self.assertEqual(result["confidence"], 0.6)

    async def test_parse_empty_llm_response(self):
        """Empty LLM response falls back to general_message."""
        mock_choice = MagicMock()
        mock_choice.message.content = ""

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.complete_async = AsyncMock(return_value=mock_response)

        processor = VoiceCommandProcessor()
        processor._client = mock_client

        result = await processor.parse_command("test transcript")
        self.assertEqual(result["command"], "general_message")
        self.assertEqual(result["confidence"], 0.0)

    async def test_parse_invalid_json_falls_back(self):
        """Invalid JSON from LLM falls back to general_message."""
        processor, _ = self._make_processor_with_mock("not valid json at all")
        result = await processor.parse_command("test transcript")

        self.assertEqual(result["command"], "general_message")
        self.assertEqual(result["confidence"], 0.0)

    async def test_parse_missing_keys_uses_defaults(self):
        """Missing keys in LLM JSON get defaults."""
        llm_output = json.dumps({"command": "pause_simulation"})
        processor, _ = self._make_processor_with_mock(llm_output)
        result = await processor.parse_command("pause it")

        self.assertEqual(result["command"], "pause_simulation")
        self.assertIn("message", result["params"])
        self.assertEqual(result["confidence"], 0.5)

    @patch("app.voice.settings")
    async def test_parse_uses_correct_model(self, mock_settings):
        mock_settings.mistral_api_key = "test-key"
        mock_settings.voice_command_model = "mistral-small-latest"

        llm_output = json.dumps(
            {
                "command": "general_message",
                "params": {"message": "hello"},
                "confidence": 0.5,
            }
        )
        processor, mock_client = self._make_processor_with_mock(llm_output)
        await processor.parse_command("hello")

        call_kwargs = mock_client.chat.complete_async.call_args[1]
        self.assertEqual(call_kwargs["model"], "mistral-small-latest")
        self.assertEqual(call_kwargs["temperature"], 0.1)
        self.assertEqual(call_kwargs["response_format"], {"type": "json_object"})


class TestProcess(unittest.IsolatedAsyncioTestCase):
    """Test the full process pipeline (transcribe + parse)."""

    async def test_process_full_pipeline(self):
        """Test end-to-end: transcribe → parse → return."""
        processor = VoiceCommandProcessor()

        # Mock transcribe
        processor.transcribe = AsyncMock(
            return_value={
                "text": "Recall rover one",
                "language": "en",
                "model": "voxtral-mini-2602",
            }
        )

        # Mock parse_command
        processor.parse_command = AsyncMock(
            return_value={
                "command": "recall_rover",
                "params": {"rover_id": "rover-mistral"},
                "confidence": 0.95,
            }
        )

        result = await processor.process(b"audio-data", "test.mp3")

        self.assertEqual(result["transcript"], "Recall rover one")
        self.assertEqual(result["command"], "recall_rover")
        self.assertEqual(result["params"]["rover_id"], "rover-mistral")
        self.assertEqual(result["confidence"], 0.95)
        self.assertEqual(result["transcription_model"], "voxtral-mini-2602")

    async def test_process_empty_transcript(self):
        """Empty transcript returns general_message with 0 confidence."""
        processor = VoiceCommandProcessor()
        processor.transcribe = AsyncMock(
            return_value={
                "text": "",
                "language": "en",
                "model": "voxtral-mini-2602",
            }
        )

        result = await processor.process(b"audio-data")

        self.assertEqual(result["transcript"], "")
        self.assertEqual(result["command"], "general_message")
        self.assertEqual(result["confidence"], 0.0)
        # parse_command should NOT be called for empty transcript

    async def test_process_whitespace_transcript(self):
        """Whitespace-only transcript returns general_message."""
        processor = VoiceCommandProcessor()
        processor.transcribe = AsyncMock(
            return_value={
                "text": "   ",
                "language": "en",
                "model": "voxtral-mini-2602",
            }
        )

        result = await processor.process(b"audio-data")
        self.assertEqual(result["command"], "general_message")
        self.assertEqual(result["confidence"], 0.0)


class TestCommandParsePrompt(unittest.TestCase):
    """Test the command parsing system prompt content."""

    def test_prompt_contains_all_commands(self):
        commands = [
            "recall_rover",
            "abort_mission",
            "pause_simulation",
            "resume_simulation",
            "reset_simulation",
            "toggle_narration",
            "general_message",
        ]
        for cmd in commands:
            self.assertIn(cmd, COMMAND_PARSE_SYSTEM_PROMPT, f"Missing command: {cmd}")

    def test_prompt_contains_rover_ids(self):
        self.assertIn("rover-mistral", COMMAND_PARSE_SYSTEM_PROMPT)
        self.assertIn("rover-2", COMMAND_PARSE_SYSTEM_PROMPT)

    def test_prompt_requests_json(self):
        self.assertIn("JSON", COMMAND_PARSE_SYSTEM_PROMPT)


class TestVoiceCommandEndpoint(unittest.TestCase):
    """Test the /api/voice-command FastAPI endpoint."""

    def setUp(self):
        from fastapi.testclient import TestClient

        from app.main import app

        self.client = TestClient(app)

    def test_empty_audio_returns_error(self):
        """Empty file upload returns error."""
        from io import BytesIO

        resp = self.client.post(
            "/api/voice-command",
            files={"audio": ("test.wav", BytesIO(b""), "audio/wav")},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertIn("Empty", data["error"])

    def test_unsupported_format_returns_error(self):
        """Unsupported content type returns error."""
        from io import BytesIO

        resp = self.client.post(
            "/api/voice-command",
            files={"audio": ("test.txt", BytesIO(b"not audio"), "text/plain")},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertIn("Unsupported", data["error"])

    @patch("app.main.voice_processor")
    def test_successful_voice_command(self, mock_processor):
        """Successful voice command returns transcript and parsed command."""
        from io import BytesIO

        mock_processor.process = AsyncMock(
            return_value={
                "transcript": "Recall rover one",
                "command": "recall_rover",
                "params": {"rover_id": "rover-mistral"},
                "confidence": 0.95,
                "transcription_model": "voxtral-mini-2602",
            }
        )

        resp = self.client.post(
            "/api/voice-command",
            files={"audio": ("test.wav", BytesIO(b"fake-audio"), "audio/wav")},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["transcript"], "Recall rover one")
        self.assertEqual(data["command"], "recall_rover")

    @patch("app.main.voice_processor")
    def test_runtime_error_returns_error(self, mock_processor):
        """RuntimeError (e.g., missing API key) returns error."""
        from io import BytesIO

        mock_processor.process = AsyncMock(side_effect=RuntimeError("MISTRAL_API_KEY not set"))

        resp = self.client.post(
            "/api/voice-command",
            files={"audio": ("test.wav", BytesIO(b"fake-audio"), "audio/wav")},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertIn("MISTRAL_API_KEY", data["error"])

    @patch("app.main.voice_processor")
    def test_unexpected_error_returns_generic_error(self, mock_processor):
        """Unexpected exception returns generic error."""
        from io import BytesIO

        mock_processor.process = AsyncMock(side_effect=ValueError("unexpected"))

        resp = self.client.post(
            "/api/voice-command",
            files={"audio": ("test.wav", BytesIO(b"fake-audio"), "audio/wav")},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertIn("failed", data["error"])

    def test_no_content_type_accepted(self):
        """File upload without content type should be accepted (no validation)."""
        from io import BytesIO

        # When content_type is empty string, we skip validation
        resp = self.client.post(
            "/api/voice-command",
            files={"audio": ("test.wav", BytesIO(b"fake-audio"), "")},
        )
        # Should proceed past content type check (may fail on processing without API key)
        self.assertEqual(resp.status_code, 200)
