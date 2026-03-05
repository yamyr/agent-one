# Data Model: Simulation Replay

## Backend (No Schema Changes Required)

All required tables already exist in SurrealDB:

| Table | Key Fields | Usage in Replay |
|-------|-----------|-----------------|
| `training_session` | id, started_at, ended_at, status, config, result, duration_seconds | Session picker list |
| `training_world_snapshot` | session_id, tick, world_state | Frame data for map rendering |
| `training_event` | session_id, tick, source, event_type, event_name, payload | Event timeline overlay |
| `training_turn` | session_id, tick, agent_id, action_name, thinking | Agent decision detail (optional) |

## Frontend State (ReplayPage)

```
sessions: Array<Session>          // From GET /api/training/sessions
selectedSession: Session | null   // Currently selected session
snapshots: Array<Snapshot>        // From GET /api/training/sessions/{id}/snapshots
events: Array<Event>              // From GET /api/training/sessions/{id}/events

// Playback state
currentIndex: number              // Index into snapshots array
playing: boolean                  // Auto-advance active
speed: number                     // 1, 2, 5, or 10
```

## API Response Shapes

### Session List Item
```json
{
  "id": "uuid",
  "started_at": "2026-03-06T10:00:00Z",
  "ended_at": "2026-03-06T10:30:00Z",
  "status": "success",
  "config": { "active_agents": [...], "world_seed": "..." },
  "duration_seconds": 1800.0
}
```

### World Snapshot
```json
{
  "id": "uuid",
  "session_id": "uuid",
  "tick": 10,
  "timestamp": "2026-03-06T10:01:00Z",
  "world_state": {
    "agents": { ... },
    "stones": [ ... ],
    "obstacles": [ ... ],
    "solar_panels": [ ... ],
    "structures": [ ... ],
    "storm": { "phase": "clear", "intensity": 0 },
    "mission": { "status": "running", "collected": 50, "target_quantity": 300 }
  }
}
```

### Training Event
```json
{
  "id": "uuid",
  "session_id": "uuid",
  "tick": 10,
  "source": "rover-mistral",
  "event_type": "action",
  "event_name": "thinking",
  "payload": { ... }
}
```
