# Implementation Plan: Feature 189 - Simulation Replay UI

## Phase 1: Backend Verification & Tests

### Task 1.1: Verify existing API endpoints
- [x] Confirm `/api/training/sessions` endpoint works
- [x] Confirm `/api/training/sessions/{id}` endpoint works
- [x] Confirm `/api/training/sessions/{id}/snapshots` endpoint works
- [x] Confirm `/api/training/sessions/{id}/events` endpoint works

### Task 1.2: Add replay-specific API tests
- [x] Write `test_replay_api.py` testing session list, snapshot retrieval, event retrieval
- [x] Ensure tests pass with in-memory SurrealDB (15 tests, all passing)

## Phase 2: Frontend - ReplayPage

### Task 2.1: Add route
- [x] Add `/replay` route to `ui/src/router/index.js`
- [x] Create `ui/src/pages/ReplayPage.vue` scaffold

### Task 2.2: Session picker
- [x] Fetch sessions from API on mount
- [x] Display session list with metadata (date, status, agent count, tick count)
- [x] Handle empty state (no sessions)
- [x] Handle loading state

### Task 2.3: Snapshot loading
- [x] On session select, fetch snapshots and events
- [x] Store in reactive state
- [x] Pass first snapshot's world_state to WorldMap

### Task 2.4: Playback controls
- [x] Play/pause toggle
- [x] Speed selector (1x, 2x, 5x, 10x)
- [x] Tick counter (current / total)
- [x] Progress bar with click-to-seek
- [x] Timer-based auto-advance using setTimeout

### Task 2.5: Event panel
- [x] Filter events for current tick range
- [x] Display event list alongside map
- [x] Show agent IDs extracted from snapshot

## Phase 3: Navigation & Polish

### Task 3.1: Navigation
- [x] Add "Replay" link to landing page NavBar
- [x] Add back-navigation from replay page

### Task 3.2: Responsive design
- [x] Ensure replay page works on tablet (768px)
- [x] Ensure replay page works on mobile (480px)

## Phase 4: Testing & Formatting

### Task 4.1: Backend tests
- [x] Run full test suite: 806 passed, 3 skipped
- [x] Format: ruff format + ruff check --fix applied

### Task 4.2: Frontend build
- [x] Verify UI compiles: vite build successful (ReplayPage chunk produced)

## Phase 5: Documentation & Commit

### Task 5.1: Update Changelog
- [x] Add replay-ui entries to Changelog.md

### Task 5.2: Commit
- [ ] Stage all files
- [ ] Commit with proper message and co-author trailer
