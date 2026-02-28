# WebSocket Event Contracts: Narrator Events

## Event Routing Rules

The WebSocket `onmessage` handler must route narrator events using BOTH `source` and `name`:

```
if source === "narrator" AND name === "narration"      → full narration handler
if source === "narrator" AND name === "narration_chunk" → streaming chunk handler
```

**Do NOT** use `event.type` for discrimination — both event types share `type: "narration"`.

## REST Endpoints

### POST /api/narration/toggle

Toggles voice synthesis on/off. Returns current state.

**Response**: `{ "enabled": boolean }`

### GET /api/narration/status

Returns current voice synthesis state.

**Response**: `{ "enabled": boolean }`

**Usage**: Call on WebSocket connect to sync UI toggle state with server.
