# Data Model: Fix Narration Text Display & Voice Toggle

**Branch**: `001-fix-narration-ui` | **Date**: 2026-02-28

## Entities

### Narration Event (WebSocket message)

Full narration broadcast after a batch of events is processed.

| Field              | Type            | Description                                    |
| ------------------ | --------------- | ---------------------------------------------- |
| `source`           | string          | Always `"narrator"`                            |
| `type`             | string          | Always `"narration"`                           |
| `name`             | string          | `"narration"` for full events                  |
| `payload.text`     | string          | Narration text (audio tags stripped)            |
| `payload.audio`    | string \| null  | Base64-encoded MP3 audio (null if voice off)   |
| `payload.format`   | string \| null  | `"mp3"` when audio present, omitted otherwise  |

### Narration Chunk (WebSocket message)

Streaming text fragment during LLM generation.

| Field              | Type   | Description                           |
| ------------------ | ------ | ------------------------------------- |
| `source`           | string | Always `"narrator"`                   |
| `type`             | string | Always `"narration"`                  |
| `name`             | string | `"narration_chunk"` for chunks        |
| `payload.text`     | string | Text fragment (audio tags stripped)    |

### Voice Toggle State

Server-side boolean controlling ElevenLabs TTS synthesis.

| Field     | Type | Description                                      |
| --------- | ---- | ------------------------------------------------ |
| `enabled` | bool | `true` = voice synthesis active, `false` = text only |

## Key Insight

Both event types share `type: "narration"`. The `name` field is the discriminator:
- `name: "narration"` → full narration with optional audio
- `name: "narration_chunk"` → streaming text fragment
