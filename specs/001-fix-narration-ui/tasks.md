# Tasks: Fix Narration Text Display & Voice Toggle

**Input**: Design documents from `/specs/001-fix-narration-ui/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Not explicitly requested. Existing server tests will be verified as part of validation.

**Organization**: Tasks grouped by user story. US1 and US2 are both P1 but independent. US3 depends on US2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No setup needed — this is a bug fix on an existing codebase. Branch already created.

_(No tasks — project structure and dependencies already exist)_

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fix the shared WebSocket event routing that blocks both text display (US1) and voice toggle (US2)

**CRITICAL**: These fixes unblock all user stories

- [x] T001 [P] Fix full narration event matching: change `event.type === 'narration'` to `event.name === 'narration'` in `ui/src/composables/useWebSocket.js` line 41
- [x] T002 [P] Fix chunk event matching: change `event.type === 'narration_chunk'` to `event.name === 'narration_chunk'` in `ui/src/composables/useWebSocket.js` line 43

**Checkpoint**: WebSocket now correctly routes narrator events — both full narrations and streaming chunks reach the UI components

---

## Phase 3: User Story 1 - See Narration Text During Simulation (Priority: P1)

**Goal**: Narration text appears in the narrator bar with typewriter streaming as mission events happen

**Independent Test**: Start simulation, wait for rover actions. Text should stream into narrator bar within 5 seconds.

### Implementation for User Story 1

- [x] T003 [US1] Verify narration text displays after T001+T002 fixes by checking NarrationPlayer.vue watcher logic handles both `narrationChunk` and `narration` props correctly in `ui/src/components/NarrationPlayer.vue`

**Checkpoint**: Narration text streams into narrator bar during simulation. "Awaiting mission events..." shows when idle.

---

## Phase 4: User Story 2 - Toggle Voice Narration On/Off (Priority: P1)

**Goal**: Voice toggle button correctly calls server and reflects actual state

**Independent Test**: Click "Voice OFF" button → changes to "Voice ON" → server enables voice synthesis. Click again to disable.

### Implementation for User Story 2

- [x] T004 [US2] Change `narrationEnabled` initialization from `ref(true)` to `ref(false)` in `ui/src/App.vue` line 14

**Checkpoint**: Toggle button starts as "Voice OFF" (matching server default), clicking it correctly toggles server state and button label.

---

## Phase 5: User Story 3 - Voice Toggle State Syncs on Page Load (Priority: P2)

**Goal**: On page load or WebSocket reconnect, UI fetches actual voice state from server

**Independent Test**: Enable voice via toggle, refresh page, toggle should still show "Voice ON"

### Implementation for User Story 3

- [x] T005 [US3] Add `/api/narration/status` fetch in `onWsConnect()` callback to sync `narrationEnabled` with server state in `ui/src/App.vue`

**Checkpoint**: Voice toggle always reflects server state on page load and reconnect.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validation and changelog

- [x] T006 Run existing server narrator tests: `cd server && rut tests/test_narrator.py` — all 30 must pass
- [x] T007 [P] Run UI lint: `cd ui && npx eslint src/` — zero warnings
- [x] T008 [P] Run UI build: `cd ui && npm run build` — clean build
- [x] T009 Update `Changelog.md` with bug fix details
- [ ] T010 Commit, push, create PR, verify CI green, merge to main

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: No dependencies — start immediately
- **US1 (Phase 3)**: Depends on T001+T002 (foundational WebSocket fixes)
- **US2 (Phase 4)**: Independent of US1 — only depends on foundational phase
- **US3 (Phase 5)**: Independent of US1 — can run in parallel with US2
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Depends on T001, T002 (WebSocket routing fixes)
- **US2 (P1)**: Independent — only touches App.vue line 14
- **US3 (P2)**: Independent — only touches App.vue onWsConnect

### Within Each User Story

- US1: Verification only (fix is in foundational phase)
- US2: Single line change
- US3: Single function addition

### Parallel Opportunities

- T001 and T002 are in the same file but different lines — can be done together in one edit
- T004 and T005 are in the same file (App.vue) — do sequentially
- T006, T007, T008 validation tasks can all run in parallel

---

## Parallel Example: Foundational Phase

```bash
# Both WebSocket fixes in one edit pass (same file):
Task T001: "Fix narration event matching in useWebSocket.js line 41"
Task T002: "Fix chunk event matching in useWebSocket.js line 43"
```

## Parallel Example: Validation

```bash
# All validation tasks in parallel:
Task T006: "Run server narrator tests"
Task T007: "Run UI lint"
Task T008: "Run UI build"
```

---

## Implementation Strategy

### MVP First (US1 + Foundational)

1. Complete Phase 2: Fix WebSocket routing (T001, T002)
2. Complete Phase 3: Verify text appears (T003)
3. **STOP and VALIDATE**: Narration text now visible in UI

### Full Fix

1. T001+T002: Fix WebSocket routing
2. T003: Verify text display
3. T004: Fix toggle default
4. T005: Add status sync on connect
5. T006+T007+T008: Validate all checks pass
6. T009: Update changelog
7. T010: Ship via PR

---

## Notes

- Total: 10 tasks (2 foundational, 1 US1, 1 US2, 1 US3, 5 polish)
- All code changes are in 2 UI files only — server code is correct
- No new dependencies or files needed
- Existing 30 narrator tests must continue to pass
