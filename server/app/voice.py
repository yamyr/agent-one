"""Voice command processor — Voxtral transcription + LLM command parsing.

Accepts audio from the human operator, transcribes it via Mistral's Voxtral
model, then uses an LLM call to extract a structured command intent for
routing through the Host.
"""

from __future__ import annotations

import logging
from typing import Any

from mistralai.models import File

from .config import settings
from .llm import get_mistral_client
from .llm_utils import safe_get_choice

logger = logging.getLogger(__name__)

# Audio formats accepted by the Voxtral transcription API
SUPPORTED_AUDIO_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/flac",
    "audio/ogg",
    "audio/webm",
}

# Mars domain terms to improve transcription accuracy
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

# ── Command parsing prompt ──────────────────────────────────────────────────

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


# ── Voice command processor ─────────────────────────────────────────────────


class VoiceCommandProcessor:
    """Transcribes audio and parses voice commands for the Mars mission."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        """Lazy-init Mistral client."""
        if self._client is None:
            self._client = get_mistral_client()
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

        import json

        choice = safe_get_choice(response, "voice")
        text = choice.message.content
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
