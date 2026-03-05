# Feature 189: Simulation Replay UI from SurrealDB Training Sessions

## Overview

Add a replay page to the UI that loads training sessions from SurrealDB and plays them back visually on the map. Users can browse past sessions, select one, and watch the simulation unfold tick-by-tick using stored world snapshots.

## User Stories

### US1 (P1): Backend API for Replay Data

**As a** frontend developer
**I want** API endpoints returning snapshots and events for a training session
**So that** the replay page can render past simulation states

**Acceptance Criteria:**
- `GET /api/training/sessions` returns list of sessions (already exists)
- `GET /api/training/sessions/{id}` returns session details (already exists)
- `GET /api/training/sessions/{id}/snapshots` returns world snapshots ordered by tick (already exists)
- `GET /api/training/sessions/{id}/events` returns events ordered by tick (already exists)
- All endpoints verified with tests

### US2 (P1): ReplayPage with Session Picker and World Map

**As a** user
**I want** a `/replay` page where I can select a training session and see the world map
**So that** I can review past simulation runs visually

**Acceptance Criteria:**
- New route `/replay` loads `ReplayPage.vue`
- Session picker shows available sessions with metadata (date, status, ticks)
- Selecting a session loads its snapshots and renders the first tick on the WorldMap
- WorldMap component renders from snapshot data (not WebSocket)
- Navigation link added to landing page NavBar

### US3 (P2): Playback Controls

**As a** user
**I want** play/pause, speed, and scrubber controls
**So that** I can control the replay timeline

**Acceptance Criteria:**
- Play/pause button starts/stops auto-advance through snapshots
- Speed selector: 1x, 2x, 5x, 10x
- Progress bar shows current tick position
- Tick counter displays current/total ticks
- Clicking the progress bar jumps to that tick
- Events panel shows events for the current tick range

## Non-Goals

- Editing or deleting training sessions from the UI
- Live recording + replay simultaneously
- Audio narration during replay
