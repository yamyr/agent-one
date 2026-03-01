"""Voice command system — Voxtral transcription + command routing + LLM parsing.

Provides two complementary voice processing classes:

- ``VoiceCommander``: Cockpit-style pipeline — transcribe audio, broadcast to UI,
  route raw text to all agent inboxes, and feed the narrator for dramatic reactions.
- ``VoiceCommandProcessor``: Structured pipeline — transcribe audio, use LLM to
  extract a structured command intent (recall_rover, abort_mission, etc.), and
  return parsed results for Host routing.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from mistralai import Mistral
from mistralai.models import File

from .config import settings
from .protocol import make_message

if TYPE_CHECKING:
    from .host import Host

logger = logging.getLogger(__name__)

# ── Audio formats accepted by the Voxtral transcription API ──────────────────

SUPPORTED_AUDIO_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/flac",
    "audio/ogg",
    "audio/webm",
}

# ── Mars domain terms to improve transcription accuracy ──────────────────────

CONTEXT_BIAS_TERMS = [
    "rover",
    "drone",
    "station",
    "drill",
    "scan",
    "navigate",
    "abort",
    "mars",
    "sol",
    "regolith",
    "basalt",
    "vein",
    "recall",
    "mission",
    "battery",
    "charge",
    "explore",
    "crater",
    "sample",
    "deploy",
    "solar",
    "panel",
]

# ── Command parsing prompt ───────────────────────────────────────────────────

COMMAND_PARSE_SYSTEM_PROMPT = """\
You are a Mars mission command parser. You receive transcribed voice commands \
from a human mission operator and extract the structured intent.

AVAILABLE COMMANDS:
- recall_rover: Recall a rover back to station. Params: rover_id (string).
- abort_mission: Abort the current mission. Params: reason (string).
- pause_simulation: Pause the simulation. No params.
- resume_simulation: Resume the simulation. No params.
- reset_simulation: Reset the simulation. No params.
- toggle_narration: Toggle narration on/off. No params.
- general_message: A general message/instruction to the mission. Params: message (string).

RULES:
- Extract the most likely command from the transcript
- If the operator mentions a specific rover (e.g., "rover one", "rover 2", \
"the rover"), map it to the appropriate rover_id
- Common rover IDs: "rover-mistral", "rover-2"
- If no clear command is detected, use "general_message"
- Always include the original transcript in your response
- Respond with ONLY valid JSON, no markdown formatting

OUTPUT FORMAT (JSON only):
{"command": "<command_name>", "params": {<parameters>}, "confidence": <0.0-1.0>}

Examples:
Transcript: "Recall rover one immediately"
{"command": "recall_rover", "params": {"rover_id": "rover-mistral"}, "confidence": 0.95}

Transcript: "Abort the mission, we have a critical failure"
{"command": "abort_mission", "params": {"reason": "Critical failure reported by operator"}, "confidence": 0.9}

Transcript: "How are the rovers doing?"
{"command": "general_message", "params": {"message": "How are the rovers doing?"}, "confidence": 0.6}
"""


# ── VoiceCommander (cockpit pipeline) ────────────────────────────────────────


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


# ── VoiceCommandProcessor (structured pipeline) ─────────────────────────────


class VoiceCommandProcessor:
    """Transcribes audio and parses voice commands for the Mars mission."""

    def __init__(self):
        self._client: Mistral | None = None

    def _get_client(self) -> Mistral:
        """Lazy-init Mistral client."""
        if self._client is None:
            if not settings.mistral_api_key:
                raise RuntimeError("MISTRAL_API_KEY not set — cannot process voice commands")
            self._client = Mistral(api_key=settings.mistral_api_key)
        return self._client

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language: str = "en",
    ) -> dict[str, Any]:
        """Transcribe audio bytes via Voxtral.

        Returns a dict with 'text', 'language', and 'model' keys.
        """
        client = self._get_client()

        response = await client.audio.transcriptions.complete_async(
            model=settings.voice_transcription_model,
            file=File(content=audio_bytes, file_name=filename),
            language=language,
            context_bias=CONTEXT_BIAS_TERMS,
        )

        return {
            "text": response.text,
            "language": response.language,
            "model": response.model,
        }

    async def parse_command(self, transcript: str) -> dict[str, Any]:
        """Use LLM to extract a structured command from the transcript.

        Returns a dict with 'command', 'params', and 'confidence' keys.
        """
        client = self._get_client()

        response = await client.chat.complete_async(
            model=settings.voice_command_model,
            messages=[
                {"role": "system", "content": COMMAND_PARSE_SYSTEM_PROMPT},
                {"role": "user", "content": f'Transcript: "{transcript}"'},
            ],
            max_tokens=200,
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        text = response.choices[0].message.content
        if not text:
            return {
                "command": "general_message",
                "params": {"message": transcript},
                "confidence": 0.0,
            }

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Voice command LLM returned invalid JSON: %s", text)
            return {
                "command": "general_message",
                "params": {"message": transcript},
                "confidence": 0.0,
            }

        # Ensure required keys exist
        return {
            "command": parsed.get("command", "general_message"),
            "params": parsed.get("params", {"message": transcript}),
            "confidence": parsed.get("confidence", 0.5),
        }

    async def process(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language: str = "en",
    ) -> dict[str, Any]:
        """Full pipeline: transcribe audio → parse command → return result.

        Returns a dict with 'transcript', 'command', 'params', 'confidence',
        and 'transcription_model' keys.
        """
        # Step 1: Transcribe
        transcription = await self.transcribe(audio_bytes, filename, language)
        transcript_text = transcription["text"]

        if not transcript_text or not transcript_text.strip():
            return {
                "transcript": "",
                "command": "general_message",
                "params": {"message": ""},
                "confidence": 0.0,
                "transcription_model": transcription.get("model", ""),
            }

        # Step 2: Parse command
        parsed = await self.parse_command(transcript_text)

        return {
            "transcript": transcript_text,
            "command": parsed["command"],
            "params": parsed["params"],
            "confidence": parsed["confidence"],
            "transcription_model": transcription.get("model", ""),
        }
