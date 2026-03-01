# Tasks: UI Polish Round 3 — Phases 3–8

**Input**: Design documents from `/specs/004-ui-polish-round3/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Not explicitly requested — no test tasks included.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1–US6)
- Exact file paths included in all descriptions

## Path Conventions

All paths relative to repository root. UI source: `ui/src/`.

---

## Phase 1: Setup

**Purpose**: Verify environment and branch readiness

- [x] T001 Verify on branch `004-ui-polish-round3` and `npm install` in `ui/`
- [x] T002 Run `npm run build` in `ui/` to confirm clean baseline

**Checkpoint**: Build passes, ready for implementation

---

## Phase 2: Foundational

**Purpose**: No blocking prerequisites — all user stories modify existing files independently. Skip to user story phases.

**Checkpoint**: N/A — proceed directly to user stories

---

## Phase 3: User Story 1 — MiniMap Legend (Priority: P1) MVP

**Goal**: Add a compact legend to MiniMap showing agent type colors/shapes and vein grade color swatches.

**Independent Test**: Open UI → MiniMap shows labeled legend with correct colors for rover (circle, #e06030), drone (triangle, #cc44cc), station (square, #44cc88) and vein grades (low through pristine).

### Implementation

- [x] T003 [US1] Add HTML legend section below SVG in `ui/src/components/MiniMap.vue` — implemented via MapLegend.vue component (PR #53)
- [x] T004 [US1] Style the legend in `ui/src/components/MiniMap.vue` — implemented with toggle button and transitions (PR #53)
- [x] T005 [US1] Verify build passes: run `npm run build` in `ui/`

**Checkpoint**: MiniMap legend visible with correct colors and responsive collapse on mobile

---

## Phase 4: User Story 2 — Toast Dedupe & Rate-Limiting (Priority: P1)

**Goal**: Deduplicate identical toast messages within 5s window and cap visible toasts at 5.

**Independent Test**: Trigger rapid identical events → single toast with "×N" count badge. Fire 6+ unique toasts → only 5 visible, oldest replaced.

### Implementation

- [x] T006 [P] [US2] Update `addToast()` in `ui/src/composables/useToasts.js` — deduplication implemented (PR #55)
- [x] T007 [P] [US2] Add rate-limiting to `addToast()` in `ui/src/composables/useToasts.js` — MAX_VISIBLE=5, evicts oldest when full
- [x] T008 [US2] Update `ui/src/components/ToastOverlay.vue` — count badge `×N` with styling
- [x] T009 [US2] Verify build passes: run `npm run build` in `ui/`

**Checkpoint**: Identical toasts deduplicate with count badge; max 5 visible at once

---

## Phase 5: User Story 3 — Keyboard Help Overlay (Priority: P2)

**Goal**: `?` key opens a modal listing all keyboard shortcuts grouped by category.

**Independent Test**: Press `?` → help modal appears with General, Camera, Agents groups. Press Escape → closes.

### Implementation

- [x] T010 [P] [US3] Create `ui/src/components/HelpModal.vue` — implemented as HelpModal.vue (stashed on feature branch)
- [x] T011 [P] [US3] Add `?` key handler in `ui/src/composables/useKeyboard.js` — implemented (PR #57 pending)
- [x] T012 [US3] Wire up in `ui/src/App.vue` — HelpModal integrated with toggle
- [x] T013 [US3] Verify build passes: run `npm run build` in `ui/`

**Checkpoint**: `?` opens help overlay; Escape closes it; shortcuts listed with correct keys

---

## Phase 6: User Story 4 — Startup/Loading Skeletons (Priority: P2)

**Goal**: Show CSS-only skeleton placeholders before WebSocket data arrives.

**Independent Test**: Hard refresh → skeleton grid in WorldMap area, pulsing rows in EventLog, placeholder values in StatsBar. Skeletons replaced when data arrives.

### Implementation

- [x] T014 [P] [US4] Skeleton states implemented inline (no separate SkeletonBlock.vue) — PR #56
- [x] T015 [P] [US4] Add skeleton state to `ui/src/components/WorldMap.vue` — grid pulse animation implemented (PR #56)
- [x] T016 [P] [US4] Add skeleton state to `ui/src/components/EventLog.vue` — 6 pulsing skeleton rows with staggered animation
- [x] T017 [P] [US4] Add skeleton state to `ui/src/components/StatsBar.vue` — skeleton items implemented (PR #56)
- [x] T018 [US4] Verify build passes: run `npm run build` in `ui/`

**Checkpoint**: Skeleton states appear on cold load; replaced smoothly when data arrives

---

## Phase 7: User Story 5 — Persist UI Preferences (Priority: P2)

**Goal**: Save zoom, follow agent, and narration state to localStorage; restore on page load.

**Independent Test**: Set zoom=150%, follow drone, toggle narration off. Refresh page. All settings restored.

### Implementation

- [x] T019 [US5] Create `ui/src/composables/usePreferences.js` — implemented with localStorage persistence
- [x] T020 [US5] Wire preferences into `ui/src/App.vue` — integrated
- [x] T021 [US5] Expose `zoom` ref from `ui/src/components/WorldMap.vue` via `defineExpose`
- [x] T022 [US5] Verify build passes: run `npm run build` in `ui/`

**Checkpoint**: Preferences survive page refresh; corrupted/missing localStorage uses defaults

---

## Phase 8: User Story 6 — Camera Smoothing Refinement (Priority: P3)

**Goal**: Distance-adaptive LERP speed — fast for long pans, precise for short movements.

**Independent Test**: Click minimap 50+ tiles away → camera arrives in <1.5s. Follow agent moving 1 tile → smooth, precise tracking.

### Implementation

- [x] T023 [US6] Update `cameraLoop()` in `ui/src/components/WorldMap.vue` — adaptive LERP implemented (PR #54)
- [x] T024 [US6] Verify build passes: run `npm run build` in `ui/`

**Checkpoint**: Long pans fast (~<1.5s for 50 tiles), short tracking smooth and precise

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and documentation

- [x] T025 Run full `npm run build` in `ui/` — zero errors confirmed
- [x] T026 Update `Changelog.md` with entries for toast rate-limiting, count badges, EventLog skeleton
- [x] T027 Update `tasks/todo.md` with completed checklist for this round
- [x] T028 Create PR from `004-ui-polish-round3` to `main`

**Checkpoint**: All stories functional, build clean, PR submitted

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: N/A — no blocking prereqs
- **User Stories (Phase 3–8)**: All independent — can run in any order or in parallel
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (MiniMap Legend)**: Independent — touches only `MiniMap.vue`
- **US2 (Toast Dedupe)**: Independent — touches only `useToasts.js` + `ToastOverlay.vue`
- **US3 (Keyboard Help)**: Independent — new `KeyboardHelp.vue` + minor `useKeyboard.js` + `App.vue`
- **US4 (Loading Skeletons)**: Independent — new `SkeletonBlock.vue` + replaces empty states in 3 components
- **US5 (localStorage Prefs)**: Depends on US6 camera smoothing only if zoom persistence requires exposed zoom ref — but `defineExpose` is minimal, so can be done standalone. Touches `App.vue` (shared with US3/US4 but different sections).
- **US6 (Camera Smoothing)**: Independent — touches only `WorldMap.vue` cameraLoop function

### Within Each User Story

- Implementation tasks flow sequentially within a story (composable → component → wiring → build check)
- Tasks marked [P] within a story can run in parallel

### Parallel Opportunities

**Maximum parallelism — 4 agents simultaneously:**

| Agent | User Story | Files |
|-------|-----------|-------|
| Agent A | US1 (MiniMap Legend) | `MiniMap.vue` |
| Agent B | US2 (Toast Dedupe) | `useToasts.js`, `ToastOverlay.vue` |
| Agent C | US4 (Loading Skeletons) | `SkeletonBlock.vue`, `WorldMap.vue`, `EventLog.vue`, `StatsBar.vue` |
| Agent D | US6 (Camera Smoothing) | `WorldMap.vue` cameraLoop only |

**⚠️ File conflicts**: US4 and US6 both touch `WorldMap.vue` — run sequentially or coordinate sections. US3 and US5 both touch `App.vue` — run sequentially.

**Recommended parallel grouping:**
- **Wave 1** (parallel): US1 + US2 + US6 (no file conflicts)
- **Wave 2** (parallel): US3 + US4 (no file conflicts between them)
- **Wave 3** (sequential): US5 (touches App.vue after US3 is done)

---

## Parallel Example: Wave 1

```bash
# Launch 3 agents in parallel (no file conflicts):
Agent A: "T003–T005: Add MiniMap legend in ui/src/components/MiniMap.vue"
Agent B: "T006–T009: Toast dedupe in ui/src/composables/useToasts.js + ui/src/components/ToastOverlay.vue"
Agent C: "T023–T024: Camera smoothing in ui/src/components/WorldMap.vue cameraLoop"
```

---

## Implementation Strategy

### MVP First (US1 + US2 = P1 stories)

1. Complete T001–T002 (setup verification)
2. Complete T003–T005 (US1: MiniMap Legend)
3. Complete T006–T009 (US2: Toast Dedupe)
4. **STOP and VALIDATE**: Build passes, legend visible, dedupe works
5. Can commit/PR as standalone increment

### Incremental Delivery

1. Wave 1: US1 + US2 + US6 → commit + validate
2. Wave 2: US3 + US4 → commit + validate
3. Wave 3: US5 → commit + validate
4. Polish: T025–T028 → PR to main

### Full Swarm Strategy

With 3 agents:
1. All agents complete setup together
2. Wave 1: Agent A (US1), Agent B (US2), Agent C (US6)
3. Wave 2: Agent A (US3), Agent B (US4), Agent C idle
4. Wave 3: Agent A (US5)
5. Lead handles Polish (T025–T028)

---

## Notes

- All tasks are frontend-only (Vue 3 + Vite) — no backend changes
- No external libraries — native Vue + CSS implementations only
- Every build check (T005, T009, T013, T018, T022, T024) must pass before moving to next story
- Co-author all commits: `Co-Authored-By: agent-one team <agent-one@yanok.ai>`
- Responsive design required: all new UI elements must work on desktop, tablet (≤768px), and mobile (≤480px)
