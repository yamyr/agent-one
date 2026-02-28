# Data Model: Non-Blocking Narration Streaming

**Branch**: `076-narrator-streaming-fix` | **Date**: 2026-03-01

## Entities

### Narration Stream Item

Single upstream event consumed during narration streaming.

| Field | Type | Description |
|-------|------|-------------|
| `event_type` | string | Upstream stream event category |
| `text_delta` | string \| null | Incremental narration text, if present |
| `timestamp` | float | Processing time for ordering/diagnostics |

### Narration Chunk Output

Websocket emission produced from stream items.

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Existing chunk event name |
| `payload.text` | string | Text fragment for client assembly |
| `sequence` | integer | Monotonic order in current narration stream |

### Responsiveness Signal

Observable indicator that core loop remains active during narration.

| Field | Type | Description |
|-------|------|-------------|
| `tick_progress` | integer | Simulation ticks observed during active stream window |
| `events_sent` | integer | Non-narration websocket events emitted during stream window |

## State Expectations

- Stream processing may be concurrent with simulation tasks but must preserve output order per stream.
- Stream failure must terminate narration path gracefully without halting global simulation flow.
