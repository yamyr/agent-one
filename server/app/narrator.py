"""Mars mission narrator — dual-narrator dialogue via Mistral LLM + ElevenLabs TTS.

Two narrators — Commander Rex (male) and Dr. Nova (female) — banter about
mission events.  Mistral generates a labelled dialogue, which is converted to
speech via the ElevenLabs Text-to-Dialogue API and broadcast over WebSocket.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import re
import time

from elevenlabs import DialogueInput, ElevenLabs
from mistralai import Mistral

from .config import settings

logger = logging.getLogger(__name__)


# ── Event filtering ──────────────────────────────────────────────────────────

# Events worth narrating (event name → dramatic weight 1-3)
INTERESTING_EVENTS = {
    # Agent discoveries
    "check": 2,  # stone found at position
    # Agent actions
    "move": 1,  # movement (only narrate occasionally)
    "dig": 2,  # digging and collecting a stone
    "analyze": 2,  # analyzing unknown stone
    # Station events
    "assign_mission": 3,  # mission assigned to rover
    "alert": 3,  # station broadcast alert
    "charge_agent": 2,  # rover being charged
    # Agent internal
    "thinking": 1,  # agent reasoning (narrate sparingly)
    # Mission-level
    "mission_success": 3,  # mission completed!
    "mission_failed": 3,  # mission failed
    "mission_aborted": 3,  # mission manually aborted
    # Storm events
    "storm_warning": 3,  # dust storm approaching
    "storm_started": 3,  # dust storm arrived
    "storm_ended": 2,  # dust storm passed
}

# Only narrate thinking events if they contain these keywords
THINKING_KEYWORDS = [
    "battery",
    "low",
    "danger",
    "storm",
    "stuck",
    "fail",
    "return",
    "station",
    "emergency",
    "vein",
    "found",
    "discover",
]


def _is_interesting(event: dict) -> int:
    """Return drama weight (0 = skip, 1-3 = narrate with priority)."""
    name = event.get("name", "")
    weight = INTERESTING_EVENTS.get(name, 0)

    if weight == 0:
        return 0

    # Filter out noisy thinking events
    if name == "thinking":
        text = event.get("payload", {}).get("text", "").lower()
        if not any(kw in text for kw in THINKING_KEYWORDS):
            return 0

    # Filter move events — only narrate every few
    if name == "move":
        return 0  # handled via batching in the event buffer

    return weight


# ── Narration text generation (Mistral) ─────────────────────────────────────

NARRATOR_SYSTEM_PROMPT = """\
You are writing a DIALOGUE between two Mars Mission narrators who are \
commentating on a live rover exploration mission together. They are a duo — \
like a podcast team covering a space mission in real time.

THE NARRATORS:
- COMMANDER REX: A seasoned mission veteran. Pragmatic, dry humor, loves a \
good pun. Speaks with authority but never takes himself too seriously. When \
things go wrong he stays calm but dramatic — "Well, folks, this is what we \
in the business call a 'situation'." Think Jeff Goldblum narrating a nature \
documentary on Mars.
- DR. NOVA: A brilliant planetary scientist. Curious, witty, genuinely \
excited about every rock and reading. She cracks jokes, geeks out over \
geology, and adds the scientific color. When discoveries happen she can \
barely contain her excitement. Think a fun science podcaster who also \
happens to have a PhD.

DIALOGUE FORMAT (STRICT):
Each line MUST start with the speaker name followed by a colon:
COMMANDER REX: [their line]
DR. NOVA: [their line]

RULES:
- Write 2-4 lines of dialogue total (alternating speakers)
- They REACT to each other — build on what the other says, crack jokes, \
disagree playfully, finish each other's thoughts
- Keep each line SHORT (1-2 sentences max)
- Be conversational and natural — like two friends watching a Mars mission
- When things go wrong (low battery, failed actions): Rex stays cool, Nova \
gets worried, they play off each other's energy
- When discoveries happen: Nova geeks out, Rex makes a quip
- NEVER use hashtags, emojis, or markdown formatting
- Vary who speaks first — sometimes Rex starts, sometimes Nova

Audio emotion tags (use sparingly, on key moments):
- [laughs] — after a joke
- [sighs] — exasperation or relief
- [whispers] — suspense
- [gasps] — sudden discoveries
- [clears throat] — transitions

Example dialogue:
COMMANDER REX: [clears throat] Well, our little rover just hit twelve \
percent battery. That's what I'd call... optimistically low.
DR. NOVA: [sighs] Optimistically low? Rex, that's critically low! It \
needs to get back to station before it becomes the galaxy's most expensive \
paperweight.
COMMANDER REX: [laughs] Expensive paperweight. I'm stealing that one.
DR. NOVA: You're welcome. Now can we please focus on getting it home?
"""


def _build_narration_prompt(events: list[dict], world_summary: str) -> str:
    """Build a prompt for Mistral to generate dialogue from batched events."""
    lines = ["Here are the latest events from the Mars mission:\n"]

    for event in events:
        source = event.get("source", "unknown")
        name = event.get("name", "unknown")
        payload = event.get("payload", {})

        if name == "check":
            stone = payload.get("stone", {})
            if stone:
                lines.append(f"- {source} found a {stone.get('type', 'unknown')} stone")
        elif name == "thinking":
            text = payload.get("text", "")
            lines.append(f'- {source} is thinking: "{text[:150]}"')
        elif name == "assign_mission":
            lines.append(
                f"- Station assigned mission to {payload.get('agent_id', '?')}: "
                f'"{payload.get("objective", "?")}"'
            )
        elif name == "alert":
            lines.append(f'- Station alert: "{payload.get("message", "?")}"')
        elif name == "charge_agent":
            bef = payload.get("battery_before", 0)
            aft = payload.get("battery_after", 0)
            agent_id = payload.get("agent_id", "agent")
            lines.append(f"- Station charged {agent_id}: battery {bef:.0%} → {aft:.0%}")
        elif name in ("dig", "analyze"):
            stone = payload.get("stone", {})
            pos = payload.get("position", [])
            lines.append(
                f"- {source} performed '{name}' at ({pos[0] if pos else '?'},"
                f"{pos[1] if len(pos) > 1 else '?'})"
                + (f" — stone type: {stone.get('type', '?')}" if stone else "")
            )
        elif name == "mission_success":
            lines.append("- MISSION SUCCESS! All target stones delivered to station!")
        elif name == "mission_failed":
            reason = payload.get("reason", "unknown")
            lines.append(f"- MISSION FAILED: {reason}")
        elif name == "storm_warning":
            lines.append(
                f"- DUST STORM WARNING: {payload.get('message', 'Storm approaching!')}"
            )
        elif name == "storm_started":
            lines.append(
                f"- DUST STORM HIT: {payload.get('message', 'Storm arrived!')} "
                f"Intensity: {payload.get('intensity', '?')}"
            )
        elif name == "storm_ended":
            lines.append(
                f"- Storm cleared: {payload.get('message', 'Storm has passed.')}"
            )
        else:
            lines.append(f"- {source}: {name} — {payload}")

    lines.append(f"\nCurrent world context:\n{world_summary}")
    lines.append(
        "\nWrite a short dialogue (2-4 lines) between COMMANDER REX and "
        "DR. NOVA reacting to these events. Be conversational, funny, and "
        "engaging. Use audio emotion tags on key moments."
    )

    return "\n".join(lines)


# ── Dialogue parsing ────────────────────────────────────────────────────────

# Match lines like "COMMANDER REX: text" or "DR. NOVA: text"
_SPEAKER_RE = re.compile(
    r"^(COMMANDER REX|DR\.?\s*NOVA)\s*:\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)

# Speaker name normalisation map
_SPEAKER_NAMES = {
    "commander rex": "COMMANDER REX",
    "dr. nova": "DR. NOVA",
    "dr nova": "DR. NOVA",
}


def _parse_dialogue(text: str) -> list[tuple[str, str]]:
    """Parse LLM output into [(speaker, line), ...] tuples.

    Returns an empty list if no valid dialogue lines are found.
    """
    matches = _SPEAKER_RE.findall(text)
    if not matches:
        return []

    result: list[tuple[str, str]] = []
    for raw_speaker, line in matches:
        speaker = _SPEAKER_NAMES.get(raw_speaker.lower().strip(), raw_speaker.upper())
        result.append((speaker, line.strip()))
    return result


# ── Text helpers ────────────────────────────────────────────────────────────

_AUDIO_TAG_RE = re.compile(
    r"\[(laughs|sighs|whispers|gasps|clears throat)\]",
    re.IGNORECASE,
)


def _strip_audio_tags(text: str) -> str:
    """Remove ElevenLabs emotion tags for text-only display."""
    cleaned = _AUDIO_TAG_RE.sub("", text)
    # Collapse any resulting double-spaces
    cleaned = re.sub(r"  +", " ", cleaned)
    return cleaned.strip()


# ── ElevenLabs TTS ──────────────────────────────────────────────────────────

# Map speaker names to config voice IDs
_VOICE_MAP = {
    "COMMANDER REX": lambda: settings.narration_voice_id_male,
    "DR. NOVA": lambda: settings.narration_voice_id_female,
}


def _generate_dialogue_audio(dialogue: list[tuple[str, str]], client: ElevenLabs) -> bytes | None:
    """Convert dialogue to MP3 via ElevenLabs Text-to-Dialogue API."""
    if not dialogue:
        return None

    inputs = []
    for speaker, line in dialogue:
        voice_getter = _VOICE_MAP.get(speaker)
        voice_id = voice_getter() if voice_getter else settings.narration_voice_id_male
        inputs.append(DialogueInput(text=line, voice_id=voice_id))

    try:
        audio_iter = client.text_to_dialogue.convert(
            inputs=inputs,
            model_id="eleven_v3",
            output_format="mp3_22050_32",
        )
        chunks = []
        for chunk in audio_iter:
            if isinstance(chunk, bytes):
                chunks.append(chunk)
        if chunks:
            return b"".join(chunks)
        return None
    except Exception:
        logger.exception("ElevenLabs Text-to-Dialogue failed")
        return None


def _generate_audio_single(text: str, client: ElevenLabs) -> bytes | None:
    """Fallback: single-voice TTS when dialogue parsing fails."""
    try:
        audio_iter = client.text_to_speech.convert(
            voice_id=settings.narration_voice_id_male,
            text=text,
            model_id="eleven_v3",
            output_format="mp3_22050_32",
        )
        chunks = []
        for chunk in audio_iter:
            if isinstance(chunk, bytes):
                chunks.append(chunk)
        if chunks:
            return b"".join(chunks)
        return None
    except Exception:
        logger.exception("ElevenLabs single-voice TTS failed")
        return None


# ── Narrator class ──────────────────────────────────────────────────────────


class Narrator:
    """Async narrator that batches events, generates dialogue, and broadcasts audio."""

    def __init__(self, broadcast_fn):
        self._broadcast = broadcast_fn
        self._event_buffer: list[dict] = []
        self._last_narration_time: float = 0
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self._enabled = settings.narration_enabled
        self._mistral: Mistral | None = None
        self._elevenlabs: ElevenLabs | None = None
        self._running = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
        logger.info("Narration %s", "enabled" if value else "disabled")

    def _get_mistral(self) -> Mistral:
        if self._mistral is None:
            if not settings.mistral_api_key:
                raise RuntimeError("MISTRAL_API_KEY not set")
            self._mistral = Mistral(api_key=settings.mistral_api_key)
        return self._mistral

    def _get_elevenlabs(self) -> ElevenLabs | None:
        if self._elevenlabs is None:
            if not settings.elevenlabs_api_key:
                logger.warning("ELEVENLABS_API_KEY not set — narration audio disabled")
                return None
            self._elevenlabs = ElevenLabs(api_key=settings.elevenlabs_api_key)
        return self._elevenlabs

    async def feed(self, event: dict):
        """Feed an event to the narrator. Non-blocking.

        When narration is disabled, events are silently dropped.
        """
        if not self._enabled:
            return

        weight = _is_interesting(event)
        if weight == 0:
            return

        async with self._lock:
            self._event_buffer.append(event)

        # Check if enough time has passed for a new narration
        now = time.monotonic()
        time_since = now - self._last_narration_time
        if time_since >= settings.narration_min_interval_seconds:
            # Fire narration immediately
            self._schedule_narration()
        # Otherwise the processing loop will pick it up

    def start(self):
        """Start the background narration processing loop."""
        if self._task is not None:
            return
        self._running = True
        self._task = asyncio.create_task(self._processing_loop())
        logger.info("Narrator started (dual-narrator mode)")

    def stop(self):
        """Stop the narrator."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Narrator stopped")

    def reset(self):
        """Clear event buffer and reset timing."""
        self._event_buffer.clear()
        self._last_narration_time = 0

    async def _processing_loop(self):
        """Background loop that checks for pending narration work."""
        while self._running:
            try:
                await asyncio.sleep(settings.narration_min_interval_seconds)
                if self._event_buffer:
                    await self._process_batch()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Narrator processing loop error")

    def _schedule_narration(self):
        """Schedule an immediate narration if not already running."""
        if self._task is None:
            return
        asyncio.create_task(self._try_narrate())

    async def _try_narrate(self):
        """Attempt to narrate if enough time has passed and there are events."""
        now = time.monotonic()
        if now - self._last_narration_time < settings.narration_min_interval_seconds:
            return
        if not self._event_buffer:
            return
        await self._process_batch()

    async def _process_batch(self):
        """Take all buffered events, generate dialogue, broadcast audio."""
        async with self._lock:
            if not self._event_buffer:
                return
            events = list(self._event_buffer)
            self._event_buffer.clear()

        self._last_narration_time = time.monotonic()

        try:
            # Build world summary for context
            from .world import world as _world

            agents = _world.get_agents()
            mission = _world.get_mission()
            summary_parts = [
                f"Mission status: {mission.get('status', 'unknown')}",
                f"Target: {mission.get('target_quantity', '?')} units of basalt "
                f"({mission.get('collected_quantity', 0)} collected)",
            ]
            for aid, agent in agents.items():
                if agent.get("type") == "rover":
                    x, y = agent.get("position", [0, 0])
                    bat = agent.get("battery", 0)
                    inv = len(agent.get("inventory", []))
                    summary_parts.append(
                        f"{aid}: pos=({x},{y}) battery={bat:.0%} inventory={inv} veins"
                    )
            world_summary = "\n".join(summary_parts)

            # Generate narration dialogue via Mistral (streaming to UI)
            prompt = _build_narration_prompt(events, world_summary)

            # Try streaming first; fall back to non-streaming on failure
            narration_text = await self._generate_text_streaming(prompt)
            if narration_text is None:
                narration_text = await asyncio.to_thread(self._generate_text, prompt)

            if not narration_text:
                logger.warning("Narrator: empty text from LLM")
                return

            logger.info("Narration: %s", narration_text)

            # Parse dialogue lines
            dialogue = _parse_dialogue(narration_text)

            # Build structured payload
            if dialogue:
                dialogue_payload = [
                    {
                        "speaker": speaker,
                        "text": _strip_audio_tags(line),
                    }
                    for speaker, line in dialogue
                ]
                flat_text = " ".join(f"{d['speaker']}: {d['text']}" for d in dialogue_payload)
            else:
                # Fallback: no parseable dialogue, treat as single narrator
                dialogue_payload = [
                    {
                        "speaker": "COMMANDER REX",
                        "text": _strip_audio_tags(narration_text),
                    }
                ]
                flat_text = _strip_audio_tags(narration_text)

            # Voice synthesis — only when narration is enabled
            if self._enabled:
                elevenlabs = self._get_elevenlabs()
                audio_bytes = None
                if elevenlabs:
                    if dialogue:
                        audio_bytes = await asyncio.to_thread(
                            _generate_dialogue_audio, dialogue, elevenlabs
                        )
                    else:
                        audio_bytes = await asyncio.to_thread(
                            _generate_audio_single, narration_text, elevenlabs
                        )

                if audio_bytes:
                    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
                    await self._broadcast(
                        {
                            "source": "narrator",
                            "type": "narration",
                            "name": "narration",
                            "payload": {
                                "text": flat_text,
                                "dialogue": dialogue_payload,
                                "audio": audio_b64,
                                "format": "mp3",
                            },
                        }
                    )
                    return

            # Text-only narration (no audio) — always sent
            await self._broadcast(
                {
                    "source": "narrator",
                    "type": "narration",
                    "name": "narration",
                    "payload": {
                        "text": flat_text,
                        "dialogue": dialogue_payload,
                        "audio": None,
                    },
                }
            )

        except Exception:
            logger.exception("Narrator batch processing failed")

    def _generate_text(self, prompt: str) -> str | None:
        """Call Mistral to generate narration dialogue (runs in thread).

        Kept as a non-streaming fallback.
        """
        try:
            client = self._get_mistral()
            response = client.chat.complete(
                model=settings.narration_model,
                messages=[
                    {"role": "system", "content": NARRATOR_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=350,
                temperature=0.9,
            )
            text = response.choices[0].message.content
            return text.strip() if text else None
        except Exception:
            logger.exception("Narrator LLM call failed")
            return None

    async def _generate_text_streaming(self, prompt: str) -> str | None:
        """Stream narration from Mistral, broadcasting chunks as they arrive.

        Each chunk is sent to the UI as a ``narration_chunk`` event so the text
        appears progressively.  Returns the full accumulated text when done.
        """
        try:
            client = self._get_mistral()

            stream = client.chat.stream(
                model=settings.narration_model,
                messages=[
                    {"role": "system", "content": NARRATOR_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=350,
                temperature=0.9,
            )

            full_text = ""
            for event in stream:
                chunk = event.data.choices[0].delta.content
                if chunk:
                    full_text += chunk
                    # Broadcast each chunk for progressive display (stripped
                    # of audio tags since these are for TTS only)
                    await self._broadcast(
                        {
                            "source": "narrator",
                            "type": "narration",
                            "name": "narration_chunk",
                            "payload": {
                                "text": _strip_audio_tags(chunk),
                            },
                        }
                    )

            return full_text.strip() if full_text else None
        except Exception:
            logger.exception("Narrator streaming LLM call failed")
            return None
