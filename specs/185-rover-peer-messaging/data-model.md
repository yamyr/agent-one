# Data Model: Rover Peer-to-Peer Messaging

**Feature**: Rover Peer-to-Peer Messaging
**Date**: 2026-03-06

---

## Existing Entity (unchanged): AGENT_MESSAGES

The global `AGENT_MESSAGES` list in world.py already supports any-to-any messaging. No schema changes needed.

| Field | Type | Description |
|-------|------|-------------|
| `from` | `str` | Sender agent ID (e.g., "rover-mistral") |
| `to` | `str` | Recipient agent ID (e.g., "rover-2") |
| `message` | `str` | Message text |
| `tick` | `int` | World tick when sent |
| `read` | `bool` | Whether recipient has read this message |

---

## New Entity: NOTIFY_PEER_TOOL

Tool definition added to ROVER_TOOLS in agent.py.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `target_id` | `str` | Yes | Agent ID of the rover to message |
| `message` | `str` | Yes | Message text to send |

**Validation Rules**:
- `target_id` must exist in `WORLD["agents"]`
- `target_id` must not equal sender's agent_id
- `target_id` agent must be a rover type (not "station", not "drone")
- `message` must be non-empty
- Sender must have sufficient battery (>= BATTERY_COST_NOTIFY)

---

## New Event: peer_message

WebSocket event broadcast when a rover sends a peer message.

| Field | Type | Description |
|-------|------|-------------|
| `source` | `str` | Sender rover ID |
| `type` | `str` | Always "event" |
| `name` | `str` | Always "peer_message" |
| `payload.target` | `str` | Target rover ID |
| `payload.message` | `str` | Message text |
| `payload.position` | `[int, int]` | Sender's position |

---

## Updated Entity: COMM_COLORS (WorldMap.vue)

| Key | Color | Description |
|-----|-------|-------------|
| `relay` | `#44ccaa` | Existing: agent-to-agent intel relay |
| `command` | `#cc8844` | Existing: station commands |
| `alert` | `#cc4444` | Existing: broadcast alerts |
| `notify` | `#4488cc` | Existing: agent notifies station |
| `peer` | `#cc44cc` | **New**: rover-to-rover peer message |

---

## Updated Entity: Rover Prompt Sections

New section added to `_build_context()` in agent.py, after the RADIO section.

| Section | Content |
|---------|---------|
| PEER COMMUNICATION | Lists other active rover IDs, explains `notify_peer` usage, suggests coordination scenarios |

---

## Relationships

```
Rover A
  |
  +--> notify_peer(target_id="rover-2", message="Rich vein at (12,8)")
  |      |
  |      +--> _execute_notify_peer() [world.py]
  |      |      +--> battery cost deducted
  |      |      +--> send_agent_message(from="rover-A", to="rover-2", message=...)
  |      |      +--> return {ok: true, ...}
  |      |
  |      +--> tick handler [agent.py]
  |             +--> broadcast WebSocket event {name: "peer_message", payload: {target, message}}
  |
  |
Rover B (target)
  |
  +--> next tick: _build_context()
         +--> get_unread_messages("rover-2")
         +--> "== INCOMING MESSAGES ==" section shows message from Rover A
```
