# WebSocket Message Schema Contract: Human-in-the-Loop Confirmation

**Feature**: Human-in-the-Loop (UiRequest::Confirm) | **Date**: 2026-03-05

## New Events Added to WebSocket `/ws` Endpoint

All events follow the existing base message schema:
```json
{
  "source": "string",
  "type": "string",
  "name": "string",
  "payload": "object",
  "id": "string (UUID v4)",
  "ts": "number (Unix timestamp)",
  "tick": "integer",
  "correlation_id": "string|null"
}
```

---

### EventMessage: confirm_request

Emitted when a rover requests human confirmation before a high-risk action. The UI should display a modal with the question and Confirm/Deny buttons.

```json
{
  "source": "rover-mistral",
  "type": "event",
  "name": "confirm_request",
  "payload": {
    "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "agent_id": "rover-mistral",
    "question": "Cross hazard zone during active storm? Battery at 35%.",
    "timeout": 30,
    "context": {
      "position": [4, 7],
      "battery": 0.35,
      "storm_phase": "active",
      "storm_intensity": 0.6
    }
  },
  "tick": 42
}
```

| payload key | type | description |
|-------------|------|-------------|
| request_id | string (UUID) | Unique ID linking request to response |
| agent_id | string | Rover requesting confirmation |
| question | string | Human-readable question |
| timeout | integer | Seconds until auto-deny (default 30) |
| context | object | Situational data for the human |
| context.position | [int, int] | Agent's current grid position |
| context.battery | number (0-1) | Current battery level |
| context.storm_phase | string or null | "clear", "warning", or "active" |
| context.storm_intensity | number or null | Storm intensity (0-1) |

**Frequency**: At most one pending per agent at any time.

---

### CommandMessage: confirm_response

Emitted when a human responds to a confirmation request via the `/api/confirm` endpoint.

```json
{
  "source": "human",
  "type": "command",
  "name": "confirm_response",
  "payload": {
    "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "confirmed": true
  },
  "tick": 43
}
```

| payload key | type | description |
|-------------|------|-------------|
| request_id | string (UUID) | Links to the original confirm_request |
| confirmed | boolean | True = human approved, False = human denied |

---

### EventMessage: confirm_timeout

Emitted when a confirmation request times out without human response. Treated as denied.

```json
{
  "source": "world",
  "type": "event",
  "name": "confirm_timeout",
  "payload": {
    "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "agent_id": "rover-mistral"
  },
  "tick": 45
}
```

| payload key | type | description |
|-------------|------|-------------|
| request_id | string (UUID) | The timed-out request |
| agent_id | string | Agent whose request timed out |

---

## REST Endpoint Contract: POST /api/confirm

### Request

```http
POST /api/confirm
Content-Type: application/json

{
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "confirmed": true
}
```

| field | type | required | description |
|-------|------|----------|-------------|
| request_id | string | yes | UUID of the pending confirmation |
| confirmed | boolean | yes | Human's decision |

### Response (200 OK)

```json
{
  "ok": true,
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "confirmed": true
}
```

### Response (404 Not Found)

```json
{
  "ok": false,
  "error": "No pending confirmation with this request_id"
}
```

### Response (400 Bad Request)

```json
{
  "ok": false,
  "error": "Missing required field: confirmed"
}
```

---

## Backward Compatibility

- Existing events are unchanged
- New events use the same base schema
- UI consumers that don't handle `confirm_request` will simply ignore them
- The `/api/confirm` endpoint is additive (no existing endpoints modified)
- Rovers without the `request_confirm` tool (drone, hauler, station) are unaffected
