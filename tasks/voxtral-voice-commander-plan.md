# Voxtral Voice Commander — Implementation Plan

**Branch**: `feature/voxtral-voice-commander`
**Worktree**: `/Users/Vernes/agent-one-voxtral`
**Status**: Complete

## Overview

Add a **Voice Commander** system that lets a human "Commander" speak voice commands from a cockpit-style UI. Audio is captured in-browser, sent to the server, transcribed via Mistral's Voxtral API, and routed to agents. The dual narrators (Commander Rex & Dr. Nova) react to voice commands via ElevenLabs TTS, creating an engaging conversational loop.

**Flow**: Commander speaks → `MediaRecorder` captures audio → POST to server → Voxtral transcribes → broadcast transcription to UI → route command to agents → narrators react with commentary → ElevenLabs TTS audio response → UI plays narrator audio

## Research Summary

### Voxtral API (Mistral)
- **Model**: `mistral-community/whisper-large-v3` via `pixtral-large-latest` multimodal OR `voxtral-mini-latest` (dedicated transcription model)
- **SDK**: `mistralai==1.12.4` (already installed)
- **Method**: `client.audio.transcriptions.complete_async(model="voxtral-mini-latest", file={"content": bytes, "file_name": "audio.wav"})`
- **Streaming**: `stream=True` returns SSE events (`transcription.text.delta`, `transcription.done`)
- **Features**: Speaker diarization, context biasing, word-level timestamps
- **Audio formats**: wav, mp3, webm (browser MediaRecorder outputs webm/opus)

### ElevenLabs TTS (existing)
- **Current**: `text_to_dialogue.convert()` with `eleven_v3` — ~1-3s latency
- **Upgrade path**: `text_to_dialogue.stream()` with `eleven_flash_v2_5` — ~75ms first chunk
- **Key**: Existing narrator pipeline handles the response direction — no architectural changes needed

### Existing Architecture
- `host.broadcast()` → `broadcaster.send()` (WebSocket) + `narrator.feed()` (event buffer)
- `host.send_command(target_id, cmd_dict)` → agent inbox `asyncio.Queue`
- Agent reads `pending_commands` on next tick via `host.drain_inbox()`
- Narrator filters events via `INTERESTING_EVENTS` weight map, batches, generates LLM dialogue, optional TTS

---

## Tasks

### 1. Config — Add Voxtral settings
- [x] Add to `server/app/config.py`:
  - `voxtral_model: str = "voxtral-mini-latest"` — transcription model
  - `voice_command_enabled: bool = True` — feature flag
- [x] Add to `server/env.sample` (if exists)

### 2. Voice Module — `server/app/voice.py`
- [x] Create `VoiceCommander` class:
  - `__init__(self, broadcast_fn, host)` — stores references
  - `async transcribe(audio_bytes: bytes, filename: str) -> dict` — calls Voxtral API
  - `async handle_voice_command(audio_bytes: bytes, filename: str) -> dict` — full pipeline:
    1. Transcribe audio via `client.audio.transcriptions.complete_async()`
    2. Broadcast `voice_transcription` event (source="commander", text=transcribed)
    3. Route command to relevant agents via `host.send_command()`
    4. Feed `voice_command` event to narrator for reaction
    5. Return `{ok: True, text: transcribed_text}`
- [x] Error handling: API failures, empty audio, no transcription result
- [x] Lazy Mistral client initialization (match narrator pattern)

### 3. Endpoint — `POST /voice/command`
- [x] Add to `server/app/main.py`:
  ```python
  @app.post("/voice/command")
  async def voice_command(audio: UploadFile):
      if not settings.voice_command_enabled:
          return {"ok": False, "error": "Voice commands disabled"}
      audio_bytes = await audio.read()
      return await voice_commander.handle_voice_command(audio_bytes, audio.filename)
  ```
- [x] Add `python-multipart` dependency (required for `UploadFile`)
- [x] Wire `voice_commander` instance in `main.py` (similar to `narrator`)

### 4. Host Integration — `server/app/host.py`
- [x] Add `handle_voice_command(text: str, target: str = None)` method:
  - If target specified: `send_command(target, {name: "voice_command", payload: {text}})`
  - If no target: send to ALL agent inboxes (broadcast command)
  - Broadcast `voice_command` event via `host.broadcast()` (feeds narrator + UI)
- [x] Create protocol message: `source="commander"`, `type="command"`, `name="voice_command"`

### 5. Narrator Integration — `server/app/narrator.py`
- [x] Add `"voice_command": 3` to `INTERESTING_EVENTS` (highest drama weight)
- [x] Update `_build_narration_prompt()` to handle voice command events:
  - Add special section: "THE COMMANDER HAS SPOKEN: '{text}'"
  - Instruct narrators to react to the commander's directive
  - Make it dramatic and fun — the commander is giving orders!
- [x] Update `NARRATOR_SYSTEM_PROMPT` to know about the Commander character:
  - The Commander is the human operator speaking from mission control
  - Rex and Nova should react with excitement/urgency to commander orders
  - They can comment on the command, speculate about it, joke about it

### 6. Agent Context — `server/app/agent.py`
- [x] In `RoverMistralReasoner._build_context()` (and drone equivalent):
  - Handle `voice_command` in pending_commands section
  - Format as: `"⚡ COMMANDER ORDER: {text}"` (high priority visual)
- [x] Agents should treat voice commands as high-priority directives

### 7. UI — `VoiceCommander.vue`
- [x] Create `ui/src/components/VoiceCommander.vue`:
  - **Mic button**: Hold-to-talk (mousedown/mouseup) or toggle mode
  - **Recording**: Use `navigator.mediaDevices.getUserMedia({ audio: true })` + `MediaRecorder`
  - **Visual feedback**: Pulsing red dot while recording, waveform/volume indicator
  - **Send**: On release/stop, POST audio blob to `/api/voice/command` as multipart
  - **Transcription display**: Show transcribed text when `voice_transcription` event received
  - **Status**: Show "Listening...", "Transcribing...", "Command sent" states
  - **Error handling**: Mic permission denied, API errors
- [x] Style: Match existing dark theme (Mars mission control aesthetic)
- [x] Responsive: Works on tablet (768px) and mobile (480px)

### 8. UI Wiring — `App.vue` + `useWebSocket.js`
- [x] In `useWebSocket.js`:
  - Add `voiceTranscription` ref
  - Route `source="commander"` events to new ref
- [x] In `App.vue`:
  - Import and place `VoiceCommander` component (between NarrationPlayer and MissionBar)
  - Pass `voiceTranscription` prop
  - Add to template

### 9. Tests — `server/tests/test_voice.py`
- [x] Test `VoiceCommander.transcribe()` with mocked Mistral client
- [x] Test `handle_voice_command()` full pipeline (transcription → routing → broadcast)
- [x] Test endpoint `POST /voice/command` with test audio file
- [x] Test voice_command_enabled=False disables endpoint
- [x] Test narrator receives voice_command events
- [x] Test agent context includes commander orders

### 10. Finalize
- [x] Update `Changelog.md` with voice commander entry
- [x] Run full test suite (`rut tests/`) — 319 passed
- [x] Run `lsp_diagnostics` on all modified/new files
- [x] Commit with `Co-Authored-By: agent-one team <agent-one@yanok.ai>`
- [x] Push and create PR following `.github/PULL_REQUEST_TEMPLATE.md` — PR #194

---

## File Manifest

### New Files
| File | Purpose |
|------|---------|
| `server/app/voice.py` | VoiceCommander class — Voxtral transcription + command routing |
| `server/tests/test_voice.py` | Tests for voice command system |
| `ui/src/components/VoiceCommander.vue` | Microphone UI, recording, transcription display |

### Modified Files
| File | Changes |
|------|---------|
| `server/app/config.py` | Add `voxtral_model`, `voice_command_enabled` |
| `server/app/main.py` | Add `/voice/command` endpoint, wire VoiceCommander |
| `server/app/host.py` | Add `handle_voice_command()` method |
| `server/app/narrator.py` | Add `voice_command` to events, update prompts |
| `server/app/agent.py` | Handle `voice_command` in agent context builder |
| `server/pyproject.toml` | Add `python-multipart` dependency |
| `ui/src/composables/useWebSocket.js` | Route commander events |
| `ui/src/App.vue` | Add VoiceCommander component |
| `Changelog.md` | Add voice commander entry |

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                        BROWSER (UI)                          │
│                                                              │
│  ┌──────────────────┐      ┌────────────────────────┐       │
│  │ VoiceCommander   │      │ NarrationPlayer        │       │
│  │ [🎤 Hold to Talk]│      │ [Rex & Nova audio]     │       │
│  │                  │      │                        │       │
│  │ MediaRecorder    │      │ Typewriter text        │       │
│  │ → webm/opus blob │      │ Base64 → Audio.play()  │       │
│  └────────┬─────────┘      └────────▲───────────────┘       │
│           │ POST /voice/command      │ WS: narration event   │
│           │ (multipart audio)        │                       │
└───────────┼──────────────────────────┼───────────────────────┘
            ▼                          │
┌───────────────────────────────────────────────────────────────┐
│                       SERVER (FastAPI)                        │
│                                                               │
│  POST /voice/command                                          │
│    ▼                                                          │
│  VoiceCommander.handle_voice_command(audio_bytes)             │
│    │                                                          │
│    ├─ 1. Voxtral API → transcribe → text                     │
│    │                                                          │
│    ├─ 2. host.broadcast(voice_transcription)                  │
│    │      ├─ broadcaster.send() → WS → UI (show text)        │
│    │      └─ narrator.feed() → event buffer                  │
│    │                                                          │
│    ├─ 3. host.send_command(agent_id, voice_command)           │
│    │      └─ agent inbox Queue → next tick → LLM context     │
│    │                                                          │
│    └─ 4. narrator.feed(voice_command) → drama weight 3       │
│           └─ Mistral LLM generates Rex/Nova dialogue         │
│              └─ ElevenLabs TTS → narration event → WS → UI   │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```
