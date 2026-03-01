# Voice Command Endpoint — Implementation Plan

## Overview
Add a `/api/voice-command` POST endpoint that accepts audio from the human operator,
transcribes it via Mistral's Voxtral model, parses the transcript into a structured
command, routes it through the Host, and broadcasts the event to all WebSocket clients.

## Tasks

- [x] 1. Create feature branch `feat/voice-command`
- [x] 2. Add `python-multipart` dependency to `pyproject.toml`
- [x] 3. Add voice config settings to `config.py` (model name, context bias terms)
- [x] 4. Create `server/app/voice.py` — Voxtral transcription + command parsing
  - [x] 4a. `VoiceCommandProcessor` class with lazy Mistral client init
  - [x] 4b. `transcribe()` — call `client.audio.transcriptions.complete_async()`
  - [x] 4c. `parse_command()` — LLM-based intent extraction from transcript
  - [x] 4d. `process()` — orchestrate transcribe → parse → return result
- [x] 5. Add `/api/voice-command` POST endpoint to `main.py`
  - [x] 5a. Accept `UploadFile` audio
  - [x] 5b. Call `VoiceCommandProcessor.process()`
  - [x] 5c. Route parsed command through Host
  - [x] 5d. Broadcast voice_command event via WebSocket
- [x] 6. Create `server/tests/test_voice.py` with full test coverage
  - [x] 6a. Test `transcribe()` with mocked Mistral client
  - [x] 6b. Test `parse_command()` with mocked LLM
  - [x] 6c. Test `process()` end-to-end with mocks
  - [x] 6d. Test error handling (no API key, transcription failure, parse failure)
  - [x] 6e. Test endpoint via FastAPI TestClient
- [x] 7. Update `Changelog.md`
- [x] 8. Run tests, verify, and submit PR

## Architecture Decisions

1. **Batch transcription** (not realtime) — suitable for push-to-talk UX
2. **Model**: `voxtral-mini-latest` for transcription endpoint
3. **Command parsing**: Use Mistral LLM to extract structured intent from transcript
4. **No new API key**: Reuses `MISTRAL_API_KEY`
5. **`context_bias`**: Mars domain terms improve transcription accuracy
6. **Supported audio formats**: MP3, WAV, FLAC, OGG, WEBM
