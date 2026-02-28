# Dual Narrators Feature Plan

## Overview
Upgrade the single-narrator system to a **dual-narrator dialogue** between a male and female commentator who interact, crack jokes, and create an engaging back-and-forth narrative about Mars mission events.

## Architecture

### Current State
- Single narrator (George, voice_id `JBFqnCBsd6RMkjVDRZzb`)
- Mistral LLM (`magistral-medium-latest`) generates 1-3 sentence monologue
- ElevenLabs `text_to_speech.convert()` generates single-voice audio
- WebSocket payload: `{text, audio, format}`

### Target State
- Two narrators: **Commander Rex** (male, George) + **Dr. Nova** (female, Rachel)
- Mistral LLM (`mistral-medium-latest`) generates a dialogue with speaker labels
- ElevenLabs **Text-to-Dialogue API** (`text_to_dialogue.convert()`) generates multi-voice audio in one call
- WebSocket payload: `{dialogue: [{speaker, text}], audio, format}`

### Key Design Decisions
1. **Text-to-Dialogue API** — ElevenLabs has a native `/v1/text-to-dialogue/convert` endpoint that takes `DialogueInput(text=..., voice_id=...)` pairs and returns a single audio stream with both voices. No need to splice audio manually.
2. **LLM generates structured dialogue** — Prompt Mistral to output `COMMANDER REX: ...` / `DR. NOVA: ...` lines, then parse into dialogue inputs.
3. **Model upgrade** — Switch from `magistral-medium-latest` to `mistral-medium-latest` per user request.
4. **Backward-compatible payload** — Include both `text` (flat string for legacy) and `dialogue` (structured array) in the narration payload.

## Tasks

- [x] Create this plan
- [x] **Config** — Added `narration_voice_id_male`, `narration_voice_id_female`, `narration_model` to `config.py`
- [x] **Narrator system prompt** — Rewritten with Commander Rex and Dr. Nova characters, dialogue format rules, audio emotion tags
- [x] **Dialogue generation** — `_parse_dialogue()` with regex `_SPEAKER_RE`, speaker normalization via `_SPEAKER_NAMES`
- [x] **TTS** — `_generate_dialogue_audio()` using `text_to_dialogue.convert()` with `DialogueInput` pairs; `_generate_audio_single()` as fallback
- [x] **Streaming** — Streaming chunks broadcast as flat text (typewriter); full dialogue structure sent in final `narration` event
- [x] **WebSocket payload** — `{text, dialogue: [{speaker, text}], audio, format}` with backward-compatible flat `text`
- [x] **NarrationPlayer.vue** — Speaker labels (REX amber, NOVA teal), dialogue block layout, "MISSION COMMS" label, responsive mobile styles
- [x] **Tests** — 14 new tests: `TestParseDialogue` (8) + `TestStripAudioTags` (6); all 44 narrator tests pass
- [x] **Changelog** — Documented dual-narrator feature in `Changelog.md`
- [ ] **PR** — Commit, push, create PR to main
