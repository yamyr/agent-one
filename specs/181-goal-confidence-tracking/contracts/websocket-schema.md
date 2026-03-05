# WebSocket Contract: Goal Confidence in State Snapshot

**Branch**: `181-goal-confidence-tracking`

## Overview

Goal confidence data is delivered to the UI via the existing `state` snapshot broadcast. No new WebSocket event types are introduced.

## Existing Contract (unchanged)

**Event**: `{ source: "world", type: "event", name: "state", payload: <snapshot> }`
**Trigger**: Broadcast after each agent tick and on WebSocket connection

## Schema Addition

The `payload.agents[<agent_id>]` object gains one new field:

### Agent State in Snapshot

```jsonc
{
  "agents": {
    "rover-mistral": {
      "position": [3, 2],
      "battery": 0.85,
      "mission": { "objective": "...", "plan": [] },
      "inventory": [],
      "memory": [],
      "tasks": [],
      "visited": [[0,0], [1,0], ...],
      "type": "rover",
      // NEW FIELD:
      "goal_confidence": 0.65  // float, 0.0-1.0
    }
  }
}
```

### Field Specification

| Field | Type | Range | Default | Description |
|-------|------|-------|---------|-------------|
| `goal_confidence` | `number` | `[0.0, 1.0]` | `0.5` | Agent's current confidence in completing its active mission |

### Backwards Compatibility

- Field is always present (initialized at agent creation)
- UI clients that don't read `goal_confidence` are unaffected
- No existing fields are modified or removed

### UI Color Mapping

| Confidence Range | Color | CSS Variable |
|-----------------|-------|--------------|
| 0.70 - 1.00 | Green | `--accent-green` |
| 0.40 - 0.69 | Amber | `--accent-amber` |
| 0.00 - 0.39 | Red | `--accent-red` |
