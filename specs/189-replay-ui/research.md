# Research Notes: Simulation Replay UI

## Existing Backend Endpoints

All required API endpoints already exist in `server/app/views.py`:
- `GET /api/training/sessions` -- list sessions with pagination
- `GET /api/training/sessions/{session_id}` -- single session + stats
- `GET /api/training/sessions/{session_id}/turns` -- agent turns by tick
- `GET /api/training/sessions/{session_id}/events` -- events by tick
- `GET /api/training/sessions/{session_id}/snapshots` -- world snapshots by tick
- `GET /api/training/sessions/{session_id}/export` -- JSONL export

These delegate to `TrainingLogger` methods in `server/app/training_logger.py`.

## Training Data Schema (SurrealDB)

Defined in `server/app/training_logger.py` (`_SCHEMA_QUERIES`):

### training_session
- `started_at`: datetime
- `ended_at`: option<datetime>
- `status`: string (running | success | failed | aborted)
- `config`: object (SessionConfig)
- `result`: option<object> (SessionResult)
- `tags`: array
- `duration_seconds`: option<float>

### training_world_snapshot
- `session_id`: string
- `tick`: int
- `timestamp`: datetime
- `world_state`: object (full world state dict)

### training_event
- `session_id`: string
- `tick`: int
- `timestamp`: datetime
- `source`: string
- `event_type`: string
- `event_name`: string
- `payload`: object

## WorldMap Component Analysis

`ui/src/components/WorldMap.vue` accepts:
- `worldState` (Object) -- the world state to render
- `agentIds` (Array) -- list of agent IDs
- `followAgent` (String) -- agent to auto-follow
- `events` (Array) -- event list for comm lines

The WorldMap renders from `worldState` prop, not directly from WebSocket.
This means we can pass snapshot `world_state` directly as `worldState`.

Key: `worldState` must contain:
- `agents` dict with position, battery, type, inventory, visited, etc.
- `stones` array with position, grade, quantity
- `solar_panels` array
- `structures` array
- `obstacles` array
- `storm` object (phase, intensity)
- `mission` object (status, collected, target_quantity)

## Router Configuration

`ui/src/router/index.js` uses `createRouter` + `createWebHistory()`.
Routes: `/` (LandingPage), `/app` (SimulationPage).
Adding `/replay` route is straightforward.

## Navigation

Landing page NavBar (`ui/src/components/landing/NavBar.vue`) has a "Launch Mission" CTA.
We can add a "Replay" link alongside it.

## Snapshot Interval

Snapshots are logged at configurable intervals (default: every 10 ticks via `training_snapshot_interval` in config).
Replay will need to interpolate or step by snapshot, not by individual tick.
