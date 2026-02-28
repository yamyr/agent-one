"""Mars mission narrator — generates witty, dramatic TTS narration from simulation events.

Hooks into the broadcaster to intercept interesting events, generates narration text
via Mistral LLM, converts to speech via ElevenLabs, and broadcasts audio to clients.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import re
import time

from elevenlabs import ElevenLabs
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
    "dig": 2,  # digging a stone
    "pickup": 2,  # picking up a stone
    "analyze": 2,  # analyzing unknown stone
    "analyze_ground": 1,  # ground concentration reading
    # Station events
    "assign_mission": 3,  # mission assigned to rover
    "alert": 3,  # station broadcast alert
    "charge_rover": 2,  # rover being charged
    # Agent internal
    "thinking": 1,  # agent reasoning (narrate sparingly)
    # Mission-level
    "mission_success": 3,  # mission completed!
    "mission_failed": 3,  # mission failed
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
    "core",
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
You are the Mars Mission Narrator — a witty, warm, and occasionally dramatic \
commentator for a live Mars rover exploration mission. Think David Attenborough \
meets a space enthusiast podcaster.

Your style:
- Natural, conversational tone — like narrating a nature documentary, but on Mars
- Sprinkle in humor and personality: puns, light jokes, genuine excitement
- When things go wrong (low battery, failed actions), get dramatic and suspenseful
- When discoveries happen, convey wonder and curiosity
- Reference agents by name (Rover, Station) — they're characters in an adventure
- Keep narrations SHORT: 1-3 sentences max. This is live commentary, not an essay
- Vary your style: sometimes a quick quip, sometimes a dramatic pause, sometimes \
genuine awe
- NEVER use hashtags, emojis, or markdown formatting

Audio emotion tags:
You MUST use ElevenLabs audio tags to add vocal emotion and expression. Wrap \
words or phrases in these tags to control how they sound:
- [laughs] — use after a joke or funny observation
- [sighs] — use for exasperation, relief, or dramatic weight
- [whispers] — use for suspense, secrets, or quiet tension
- [gasps] — use for sudden discoveries or shocking news
- [clears throat] — use for transitions or when composing yourself

Place tags INLINE in your narration text. Examples:
- "[whispers] Something's moving out there... [gasps] Wait — is that a core sample?!"
- "Battery at twelve percent. [sighs] Our little rover's running on fumes."
- "[laughs] Basalt again! The Red Planet really knows how to tease."
- "[clears throat] Mission control has spoken — new objective incoming."
- "[gasps] We did it! [laughs] Ladies and gentlemen, core sample secured!"

Use these tags naturally — not on every sentence, but to punch up key emotional \
moments. The voice synthesizer will render them as actual vocal expressions.
"""


def _build_narration_prompt(events: list[dict], world_summary: str) -> str:
    """Build a prompt for Mistral to generate narration text from batched events."""
    lines = ["Here are the latest events from the Mars mission:\n"]

    for event in events:
        source = event.get("source", "unknown")
        name = event.get("name", "unknown")
        payload = event.get("payload", {})

        if name == "check":
            stone = payload.get("stone", {})
            if stone:
                lines.append(
                    f"- {source} found a {stone.get('type', 'unknown')} stone "
                    f"(extracted={stone.get('extracted', False)})"
                )
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
        elif name == "charge_rover":
            bef = payload.get("battery_before", 0)
            aft = payload.get("battery_after", 0)
            lines.append(f"- Station charged a rover: battery {bef:.0%} → {aft:.0%}")
        elif name in ("dig", "pickup", "analyze"):
            stone = payload.get("stone", {})
            pos = payload.get("position", [])
            lines.append(
                f"- {source} performed '{name}' at ({pos[0] if pos else '?'},"
                f"{pos[1] if len(pos) > 1 else '?'})"
                + (f" — stone type: {stone.get('type', '?')}" if stone else "")
            )
        elif name == "analyze_ground":
            conc = payload.get("concentration", 0)
            lines.append(
                f"- {source} analyzed ground concentration: {conc:.3f}"
                + (" (hot spot!)" if conc > 0.5 else " (low reading)")
            )
        elif name == "mission_success":
            lines.append("- MISSION SUCCESS! All target stones delivered to station!")
        elif name == "mission_failed":
            reason = payload.get("reason", "unknown")
            lines.append(f"- MISSION FAILED: {reason}")
        else:
            lines.append(f"- {source}: {name} — {payload}")

    lines.append(f"\nCurrent world context:\n{world_summary}")
    lines.append(
        "\nGenerate a short, natural narration (1-3 sentences) for these events. "
        "Be conversational and engaging. If multiple events happened, weave them "
        "into a cohesive narrative. Use audio emotion tags like [whispers], [gasps], "
        "[laughs], [sighs] to add vocal expression at key moments."
    )

    return "\n".join(lines)


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


def _generate_audio(text: str, client: ElevenLabs) -> bytes | None:
    """Convert narration text to MP3 audio bytes via ElevenLabs."""
    try:
        audio_iter = client.text_to_speech.convert(
            voice_id=settings.narration_voice_id,
            text=text,
            model_id="eleven_v3",
            output_format="mp3_22050_32",
        )
        # convert returns an iterator of bytes chunks
        chunks = []
        for chunk in audio_iter:
            if isinstance(chunk, bytes):
                chunks.append(chunk)
        if chunks:
            return b"".join(chunks)
        return None
    except Exception:
        logger.exception("ElevenLabs TTS failed")
        return None


# ── Narrator class ──────────────────────────────────────────────────────────


class Narrator:
    """Async narrator that batches events, generates narration, and broadcasts audio."""

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

        Text narration is always generated regardless of the enabled flag.
        The ``_enabled`` flag only controls whether ElevenLabs voice audio
        is produced.
        """
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
        logger.info("Narrator started")

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
        """Take all buffered events, generate narration, broadcast audio."""
        async with self._lock:
            if not self._event_buffer:
                return
            events = list(self._event_buffer)
            self._event_buffer.clear()

        self._last_narration_time = time.monotonic()

        try:
            # Build world summary for context
            from .world import WORLD

            agents = WORLD.get("agents", {})
            mission = WORLD.get("mission", {})
            summary_parts = [
                f"Mission status: {mission.get('status', 'unknown')}",
                f"Target: {mission.get('target_count', '?')} {mission.get('target_type', '?')} stones "
                f"({mission.get('collected_count', 0)} collected)",
            ]
            for aid, agent in agents.items():
                if agent.get("type") == "rover":
                    x, y = agent.get("position", [0, 0])
                    bat = agent.get("battery", 0)
                    inv = len(agent.get("inventory", []))
                    summary_parts.append(
                        f"{aid}: pos=({x},{y}) battery={bat:.0%} inventory={inv} stones"
                    )
            world_summary = "\n".join(summary_parts)

            # Generate narration text via Mistral (streaming to UI)
            prompt = _build_narration_prompt(events, world_summary)

            # Try streaming first; fall back to non-streaming on failure
            narration_text = await self._generate_text_streaming(prompt)
            if narration_text is None:
                narration_text = await asyncio.to_thread(self._generate_text, prompt)

            if not narration_text:
                logger.warning("Narrator: empty text from LLM")
                return

            logger.info("Narration: %s", narration_text)

            # Voice synthesis — only when narration is enabled
            if self._enabled:
                elevenlabs = self._get_elevenlabs()
                audio_bytes = None
                if elevenlabs:
                    audio_bytes = await asyncio.to_thread(
                        _generate_audio, narration_text, elevenlabs
                    )

                if audio_bytes:
                    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
                    await self._broadcast(
                        {
                            "source": "narrator",
                            "type": "narration",
                            "name": "narration",
                            "payload": {
                                "text": _strip_audio_tags(narration_text),
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
                        "text": _strip_audio_tags(narration_text),
                        "audio": None,
                    },
                }
            )

        except Exception:
            logger.exception("Narrator batch processing failed")

    def _generate_text(self, prompt: str) -> str | None:
        """Call Mistral to generate narration text (runs in thread).

        Kept as a non-streaming fallback.
        """
        try:
            client = self._get_mistral()
            response = client.chat.complete(
                model="magistral-medium-latest",
                messages=[
                    {"role": "system", "content": NARRATOR_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=200,
                temperature=0.9,
            )
            text = response.choices[0].message.content
            return text.strip() if text else None
        except Exception:
            logger.exception("Narrator LLM call failed")
            return None

    async def _generate_text_streaming(self, prompt: str) -> str | None:
        """Stream narration text from Mistral, broadcasting chunks as they arrive.

        Each chunk is sent to the UI as a ``narration_chunk`` event so the text
        appears progressively.  Returns the full accumulated text when done.
        """
        try:
            client = self._get_mistral()

            stream = client.chat.stream(
                model="magistral-medium-latest",
                messages=[
                    {"role": "system", "content": NARRATOR_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=200,
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
