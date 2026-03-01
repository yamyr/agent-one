"""Voice Commander — Voxtral transcription + command routing.

Captures audio from the UI cockpit, transcribes via Mistral's Voxtral API,
broadcasts the transcription, and routes the command to agents.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mistralai import Mistral

from .config import settings
from .protocol import make_message

if TYPE_CHECKING:
    from .host import Host

logger = logging.getLogger(__name__)


class VoiceCommander:
    """Transcribe commander audio via Voxtral and route as agent commands."""

    def __init__(self, host: Host):
        self._host = host
        self._client: Mistral | None = None

    # ── Lazy client ──

    def _get_client(self) -> Mistral:
        if self._client is None:
            if not settings.mistral_api_key:
                raise RuntimeError("MISTRAL_API_KEY required for voice commands")
            self._client = Mistral(api_key=settings.mistral_api_key)
        return self._client

    # ── Core pipeline ──

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """Transcribe audio bytes via Voxtral. Returns transcribed text."""
        client = self._get_client()
        response = await client.audio.transcriptions.complete_async(
            model=settings.voxtral_model,
            file={"content": audio_bytes, "file_name": filename},
        )
        return response.text.strip() if response.text else ""

    async def handle_voice_command(self, audio_bytes: bytes, filename: str = "audio.webm") -> dict:
        """Full pipeline: transcribe → broadcast → route to agents → feed narrator."""
        if not settings.voice_command_enabled:
            return {"ok": False, "error": "Voice commands disabled"}

        if not audio_bytes:
            return {"ok": False, "error": "Empty audio"}

        try:
            text = await self.transcribe(audio_bytes, filename)
        except Exception:
            logger.exception("Voxtral transcription failed")
            return {"ok": False, "error": "Transcription failed"}

        if not text:
            return {"ok": False, "error": "No speech detected"}

        logger.info("Commander voice command: %s", text)

        # 1. Broadcast transcription event to UI
        transcription_msg = make_message(
            source="commander",
            type="event",
            name="voice_transcription",
            payload={"text": text},
        )
        await self._host.broadcast(transcription_msg.to_dict())

        # 2. Route command to all agents via host
        await self._host.handle_voice_command(text)

        return {"ok": True, "text": text}
