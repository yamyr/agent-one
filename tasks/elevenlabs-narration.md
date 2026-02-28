# ElevenLabs Narration Feature

## Overview
Add real-time AI-generated narration to the Mars simulation using Mistral for text generation and ElevenLabs for text-to-speech. The narrator acts as a witty, dramatic mission commentator — announcing agent goals, celebrating discoveries, dramatizing trouble, and cracking jokes.

## Architecture

```
Event Flow:
  agent_loop() → broadcaster.send(event) → Narrator intercepts
                                           ↓
                                    Mistral generates narration text
                                           ↓
                                    ElevenLabs converts to MP3
                                           ↓
                                    broadcaster.send({type: "narration", payload: {audio: base64, text: "..."}})
                                           ↓
                                    Frontend NarrationPlayer plays audio
```

## Design Decisions

1. **Narration is async** — doesn't block the event loop. Events queue up, narrator processes them with rate limiting.
2. **Not every event gets narrated** — only "interesting" ones: goal changes, stone discoveries, low battery, mission status, storms, errors.
3. **Batching** — multiple rapid events are batched into a single narration to avoid overwhelming the listener.
4. **Rate limiting** — minimum 10s between narrations to let audio finish playing.
5. **Audio format** — MP3 at 22050Hz/32kbps (smallest supported format, fast to generate and stream).
6. **Delivery** — Base64 encoded MP3 over existing WebSocket as a `narration` event type.

## Tasks

- [x] Create feature branch
- [x] Write plan
- [x] Add `elevenlabs` dependency to `pyproject.toml`
- [x] Add `ELEVENLABS_API_KEY` to `config.py`
- [x] Create `narrator.py` — narration engine
  - [x] Event filter (which events are "interesting")
  - [x] Narration text generator (Mistral LLM prompt)
  - [x] ElevenLabs TTS integration
  - [x] Event batching + rate limiting
  - [x] Async background task
- [x] Hook narrator into `main.py` event flow
- [x] Add `/narration/toggle` endpoint
- [x] Create `NarrationPlayer.vue` frontend component
- [x] Wire narration into `useWebSocket.js` and `App.vue`
- [x] Update `env.sample`
- [x] Write tests (30 tests, all passing)
- [x] Update `Changelog.md`
- [x] Verify: lint, build, test
