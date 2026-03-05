# Data Model: Human-in-the-Loop (UiRequest::Confirm)

**Feature**: Human-in-the-Loop Confirmation for High-Risk Rover Actions
**Date**: 2026-03-05

---

## Entity: PendingConfirmation (new, transient)

Stored in `Host._pending_confirms` as a dict keyed by `request_id`. NOT persisted in WORLD state.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| request_id (key) | `str` | UUID for the confirmation request | Auto-generated UUID4 |
| agent_id | `str` | Rover requesting confirmation | Must exist in WORLD["agents"] |
| question | `str` | Human-readable question | Non-empty string |
| timeout | `int` | Seconds before auto-deny | 5-120, default 30 |
| event | `asyncio.Event` | Signaled when response arrives | Internal, not serialized |
| response | `bool \| None` | Human's decision (None = pending) | Set by /api/confirm |
| tick | `int` | Tick when request was created | Current WORLD tick |

**Example state**:
```python
host._pending_confirms = {
    "a1b2c3d4-...": {
        "agent_id": "rover-mistral",
        "question": "Cross hazard zone during active storm? Battery at 35%.",
        "timeout": 30,
        "event": <asyncio.Event>,
        "response": None,  # Pending
        "tick": 42,
    }
}
```

**State Transitions**:
- Created: Rover calls `request_confirm` tool in its tick
- Responded: `/api/confirm` sets `response` and signals `event`
- Timed out: `asyncio.wait_for` raises TimeoutError, treated as denied
- Cleaned up: Entry removed after response or timeout

---

## Constant: CONFIRM_DEFAULT_TIMEOUT (new)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| CONFIRM_DEFAULT_TIMEOUT | `int` | `30` | Default seconds before auto-deny |

Defined in `server/app/host.py`.

---

## Event: confirm_request (new)

Emitted when a rover requests human confirmation before a high-risk action.

| Field | Type | Value |
|-------|------|-------|
| source | `str` | Agent ID (e.g., `"rover-mistral"`) |
| type | `str` | `"event"` |
| name | `str` | `"confirm_request"` |
| payload.request_id | `str` | UUID linking request to response |
| payload.agent_id | `str` | Requesting agent |
| payload.question | `str` | Human-readable question |
| payload.timeout | `int` | Seconds until auto-deny |
| payload.context | `dict` | Situational data (position, battery, storm, etc.) |
| tick | `int` | Current simulation tick |

---

## Event: confirm_response (new)

Emitted when a human responds to a confirmation request.

| Field | Type | Value |
|-------|------|-------|
| source | `str` | `"human"` |
| type | `str` | `"command"` |
| name | `str` | `"confirm_response"` |
| payload.request_id | `str` | UUID linking to the original request |
| payload.confirmed | `bool` | True = approved, False = denied |
| tick | `int` | Current simulation tick |

---

## Event: confirm_timeout (new)

Emitted when a confirmation request times out without human response.

| Field | Type | Value |
|-------|------|-------|
| source | `str` | `"world"` |
| type | `str` | `"event"` |
| name | `str` | `"confirm_timeout"` |
| payload.request_id | `str` | UUID of the timed-out request |
| payload.agent_id | `str` | Agent that requested confirmation |
| tick | `int` | Current simulation tick |

---

## Tool Schema: REQUEST_CONFIRM_TOOL (new)

```python
REQUEST_CONFIRM_TOOL = {
    "type": "function",
    "function": {
        "name": "request_confirm",
        "description": (
            "Request human confirmation before a high-risk action. "
            "Your loop pauses until the human confirms or denies (or timeout). "
            "Use before entering storm zones, crossing hazard tiles, "
            "or moving with very low battery. Do NOT use for routine moves."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Clear question for the human operator (e.g., 'Cross hazard zone during active storm? Battery at 35%.').",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Seconds to wait for response (default 30, max 120).",
                },
            },
            "required": ["question"],
        },
    },
}
```

---

## REST Endpoint: POST /api/confirm (new)

**Request Body**:
```json
{
    "request_id": "a1b2c3d4-...",
    "confirmed": true
}
```

**Response (success)**:
```json
{
    "ok": true,
    "request_id": "a1b2c3d4-...",
    "confirmed": true
}
```

**Response (not found)**:
```json
{
    "ok": false,
    "error": "No pending confirmation with this request_id"
}
```

---

## Updated Entity: Host (additions only)

| New Field | Type | Default | Description |
|-----------|------|---------|-------------|
| `_pending_confirms` | `dict[str, dict]` | `{}` | Pending confirmation requests keyed by request_id |

**New Methods**:
- `create_confirm(agent_id, question, timeout) -> str`: Creates pending confirm, returns request_id
- `resolve_confirm(request_id, confirmed: bool) -> bool`: Sets response and signals event
- `get_pending_confirm(request_id) -> dict | None`: Retrieves pending confirm
- `get_agent_pending_confirm(agent_id) -> dict | None`: Gets confirm for a specific agent
- `cleanup_confirm(request_id)`: Removes expired/resolved confirm

---

## Relationships

```
Rover Tick
  |
  +--> request_confirm tool called
  |      |
  |      +--> host.create_confirm(agent_id, question, timeout)
  |      |      |
  |      |      +--> Creates asyncio.Event
  |      |      +--> Broadcasts confirm_request event
  |      |
  |      +--> await asyncio.wait_for(event.wait(), timeout)
  |             |
  |             +--> Human clicks Confirm/Deny in UI
  |             |      |
  |             |      +--> POST /api/confirm {request_id, confirmed}
  |             |      |      |
  |             |      |      +--> host.resolve_confirm(request_id, confirmed)
  |             |      |      +--> Broadcasts confirm_response event
  |             |      |      +--> event.set() → unblocks rover
  |             |      |
  |             |      +--> UI dismisses modal
  |             |
  |             +--> Timeout?
  |                    |
  |                    +--> Treated as denied
  |                    +--> Broadcasts confirm_timeout event
  |                    +--> UI auto-dismisses modal
  |
  +--> Rover receives response (confirmed=True/False)
  +--> Rover proceeds or aborts the risky action
```
