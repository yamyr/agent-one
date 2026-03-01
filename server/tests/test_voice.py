"""Tests for VoiceCommander — transcription, routing, endpoint, feature flag."""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.host import Host
from app.narrator import Narrator
from app.voice import VoiceCommander


def _make_host():
    """Create a Host with a mocked narrator for testing."""
    narrator = MagicMock(spec=Narrator)
    narrator.feed = AsyncMock()
    narrator.reset = MagicMock()
    narrator.start = MagicMock()
    narrator.stop = MagicMock()
    return Host(narrator=narrator)


class TestVoiceCommanderTranscribe(unittest.TestCase):
    """Test VoiceCommander.transcribe() with mocked Mistral client."""

    def test_transcribe_returns_text(self):
        host = _make_host()
        vc = VoiceCommander(host=host)

        mock_response = MagicMock()
        mock_response.text = " Collect basalt from zone alpha "

        mock_client = MagicMock()
        mock_client.audio.transcriptions.complete_async = AsyncMock(return_value=mock_response)
        vc._client = mock_client

        result = asyncio.run(vc.transcribe(b"fake-audio-bytes", "test.webm"))
        self.assertEqual(result, "Collect basalt from zone alpha")

        mock_client.audio.transcriptions.complete_async.assert_called_once()
        call_kwargs = mock_client.audio.transcriptions.complete_async.call_args
        self.assertEqual(call_kwargs.kwargs["file"]["file_name"], "test.webm")

    def test_transcribe_empty_text_returns_empty(self):
        host = _make_host()
        vc = VoiceCommander(host=host)

        mock_response = MagicMock()
        mock_response.text = ""

        mock_client = MagicMock()
        mock_client.audio.transcriptions.complete_async = AsyncMock(return_value=mock_response)
        vc._client = mock_client

        result = asyncio.run(vc.transcribe(b"silence", "quiet.webm"))
        self.assertEqual(result, "")

    def test_transcribe_none_text_returns_empty(self):
        host = _make_host()
        vc = VoiceCommander(host=host)

        mock_response = MagicMock()
        mock_response.text = None

        mock_client = MagicMock()
        mock_client.audio.transcriptions.complete_async = AsyncMock(return_value=mock_response)
        vc._client = mock_client

        result = asyncio.run(vc.transcribe(b"noise", "noise.webm"))
        self.assertEqual(result, "")


class TestVoiceCommanderPipeline(unittest.TestCase):
    """Test handle_voice_command() full pipeline."""

    def _make_vc_with_mock_transcribe(self, transcription="Move rover north"):
        host = _make_host()
        host.register(MagicMock(agent_id="rover-mistral", interval=0.1))
        vc = VoiceCommander(host=host)
        vc.transcribe = AsyncMock(return_value=transcription)
        return vc, host

    def test_handle_voice_command_success(self):
        vc, host = self._make_vc_with_mock_transcribe("Move rover north")

        with patch("app.host.broadcaster") as mock_bc:
            mock_bc.send = AsyncMock()
            result = asyncio.run(vc.handle_voice_command(b"audio-data", "cmd.webm"))

        self.assertTrue(result["ok"])
        self.assertEqual(result["text"], "Move rover north")
        vc.transcribe.assert_called_once_with(b"audio-data", "cmd.webm")

    def test_handle_voice_command_routes_to_agents(self):
        vc, host = self._make_vc_with_mock_transcribe("Recall all rovers")

        with patch("app.host.broadcaster") as mock_bc:
            mock_bc.send = AsyncMock()
            asyncio.run(vc.handle_voice_command(b"audio", "cmd.webm"))

        commands = host.drain_inbox("rover-mistral")
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["name"], "voice_command")
        self.assertEqual(commands[0]["payload"]["text"], "Recall all rovers")

    def test_handle_voice_command_broadcasts_transcription(self):
        vc, host = self._make_vc_with_mock_transcribe("Scan zone bravo")

        with patch("app.host.broadcaster") as mock_bc:
            mock_bc.send = AsyncMock()
            asyncio.run(vc.handle_voice_command(b"audio", "cmd.webm"))

            # Should broadcast at least 2 messages:
            # 1. voice_transcription (from VoiceCommander)
            # 2. voice_command (from host.handle_voice_command)
            self.assertGreaterEqual(mock_bc.send.call_count, 2)

            # Find the transcription broadcast
            calls = [c.args[0] for c in mock_bc.send.call_args_list]
            transcription_msgs = [c for c in calls if c.get("name") == "voice_transcription"]
            self.assertEqual(len(transcription_msgs), 1)
            self.assertEqual(transcription_msgs[0]["payload"]["text"], "Scan zone bravo")
            self.assertEqual(transcription_msgs[0]["source"], "commander")

    def test_handle_voice_command_feeds_narrator(self):
        vc, host = self._make_vc_with_mock_transcribe("Deploy solar panel")

        with patch("app.host.broadcaster") as mock_bc:
            mock_bc.send = AsyncMock()
            asyncio.run(vc.handle_voice_command(b"audio", "cmd.webm"))

        # Narrator should have been fed events
        self.assertTrue(host._narrator.feed.called)

    def test_handle_voice_command_empty_audio(self):
        host = _make_host()
        vc = VoiceCommander(host=host)

        result = asyncio.run(vc.handle_voice_command(b"", "empty.webm"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "Empty audio")

    def test_handle_voice_command_no_speech(self):
        vc, host = self._make_vc_with_mock_transcribe("")

        with patch("app.host.broadcaster") as mock_bc:
            mock_bc.send = AsyncMock()
            result = asyncio.run(vc.handle_voice_command(b"silence", "quiet.webm"))

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "No speech detected")

    def test_handle_voice_command_transcription_failure(self):
        host = _make_host()
        vc = VoiceCommander(host=host)
        vc.transcribe = AsyncMock(side_effect=RuntimeError("API down"))

        result = asyncio.run(vc.handle_voice_command(b"audio", "cmd.webm"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "Transcription failed")


class TestVoiceCommanderFeatureFlag(unittest.TestCase):
    """Test voice_command_enabled feature flag."""

    def test_disabled_returns_error(self):
        host = _make_host()
        vc = VoiceCommander(host=host)

        with patch("app.voice.settings") as mock_settings:
            mock_settings.voice_command_enabled = False
            result = asyncio.run(vc.handle_voice_command(b"audio", "cmd.webm"))

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "Voice commands disabled")


class TestVoiceCommanderLazyClient(unittest.TestCase):
    """Test lazy Mistral client initialization."""

    def test_get_client_raises_without_api_key(self):
        host = _make_host()
        vc = VoiceCommander(host=host)

        with patch("app.voice.settings") as mock_settings:
            mock_settings.mistral_api_key = ""
            with self.assertRaises(RuntimeError) as ctx:
                vc._get_client()
            self.assertIn("MISTRAL_API_KEY", str(ctx.exception))

    def test_get_client_creates_client_once(self):
        host = _make_host()
        vc = VoiceCommander(host=host)

        with patch("app.voice.settings") as mock_settings:
            mock_settings.mistral_api_key = "test-key"
            with patch("app.voice.Mistral") as mock_cls:
                mock_cls.return_value = MagicMock()
                client1 = vc._get_client()
                client2 = vc._get_client()
                self.assertIs(client1, client2)
                mock_cls.assert_called_once_with(api_key="test-key")


class TestHostVoiceCommand(unittest.TestCase):
    """Test Host.handle_voice_command() routes to all agents."""

    def test_voice_command_sent_to_all_agents(self):
        host = _make_host()
        host.register(MagicMock(agent_id="rover-mistral", interval=0.1))
        host.register(MagicMock(agent_id="rover-2", interval=0.1))
        host.register(MagicMock(agent_id="drone-mistral", interval=0.1))

        with patch("app.host.broadcaster") as mock_bc:
            mock_bc.send = AsyncMock()
            asyncio.run(host.handle_voice_command("Head to zone delta"))

        for agent_id in ["rover-mistral", "rover-2", "drone-mistral"]:
            commands = host.drain_inbox(agent_id)
            self.assertEqual(len(commands), 1, f"Expected 1 command for {agent_id}")
            self.assertEqual(commands[0]["name"], "voice_command")
            self.assertEqual(commands[0]["payload"]["text"], "Head to zone delta")

    def test_voice_command_broadcasts_event(self):
        host = _make_host()
        host.register(MagicMock(agent_id="rover-mistral", interval=0.1))

        with patch("app.host.broadcaster") as mock_bc:
            mock_bc.send = AsyncMock()
            asyncio.run(host.handle_voice_command("Status report"))

            # Should broadcast voice_command event
            calls = [c.args[0] for c in mock_bc.send.call_args_list]
            cmd_msgs = [c for c in calls if c.get("name") == "voice_command"]
            self.assertEqual(len(cmd_msgs), 1)
            self.assertEqual(cmd_msgs[0]["source"], "commander")
            self.assertEqual(cmd_msgs[0]["payload"]["text"], "Status report")


class TestNarratorVoiceEvents(unittest.TestCase):
    """Test narrator knows about voice command events."""

    def test_voice_events_in_interesting_events(self):
        from app.narrator import INTERESTING_EVENTS

        self.assertIn("voice_command", INTERESTING_EVENTS)
        self.assertIn("voice_transcription", INTERESTING_EVENTS)
        self.assertEqual(INTERESTING_EVENTS["voice_command"], 3)
        self.assertEqual(INTERESTING_EVENTS["voice_transcription"], 3)
