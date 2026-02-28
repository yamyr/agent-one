# Tasks: UI Polish & Beautification

**Input**: Design documents from `/specs/002-ui-polish/`
**Prerequisites**: spec.md (required)

**Tests**: Validated via CI (eslint + vite build) after each PR. No new unit tests required.

**Organization**: Each user story = one PR, merged independently. Sequential execution (P1 → P2 → P3).

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: US1 — CSS Design Tokens (P1) 🎯 PR #1

**Goal**: Extract all hardcoded colors/radii into `:root` CSS custom properties

- [ ] T001 [US1] Define `:root` design tokens block in `ui/src/App.vue` `<style>` section with all shared colors, radii, and font-family
- [ ] T002 [US1] Replace hardcoded colors in `ui/src/App.vue` global styles with `var(--*)` references
- [ ] T003 [P] [US1] Replace hardcoded colors in `ui/src/components/AppHeader.vue` with `var(--*)` references
- [ ] T004 [P] [US1] Replace hardcoded colors in `ui/src/components/MissionBar.vue` with `var(--*)` references
- [ ] T005 [P] [US1] Replace hardcoded colors in `ui/src/components/WorldMap.vue` with `var(--*)` references
- [ ] T006 [P] [US1] Replace hardcoded colors in `ui/src/components/EventLog.vue` with `var(--*)` references
- [ ] T007 [P] [US1] Replace hardcoded colors in `ui/src/components/AgentPane.vue` with `var(--*)` references
- [ ] T008 [P] [US1] Replace hardcoded colors in `ui/src/components/AgentDetailModal.vue` with `var(--*)` references
- [ ] T009 [P] [US1] Replace hardcoded colors in `ui/src/components/NarrationPlayer.vue` with `var(--*)` references
- [ ] T010 [P] [US1] Replace hardcoded colors in `ui/src/components/MiniMap.vue` with `var(--*)` references
- [ ] T011 [US1] Run `npx eslint .` and `npm run build` in `ui/` — zero errors
- [ ] T012 [US1] Commit, push, create PR, verify CI green, merge to main

**Checkpoint**: All components use CSS variables. Visual output identical to before.

---

## Phase 2: US2 — Font Upgrade (P1) 🎯 PR #2

**Goal**: Replace Courier New with self-hosted JetBrains Mono

- [ ] T013 [US2] Install `@fontsource/jetbrains-mono` in `ui/` via npm
- [ ] T014 [US2] Import font CSS in `ui/src/main.js`: `import '@fontsource/jetbrains-mono/400.css'` and `import '@fontsource/jetbrains-mono/700.css'`
- [ ] T015 [US2] Update `--font-mono` CSS variable (from Phase 1) to `'JetBrains Mono', monospace`
- [ ] T016 [US2] Remove all `font-family: 'Courier New', monospace` from component scoped styles (now inherited via variable)
- [ ] T017 [US2] Run `npx eslint .` and `npm run build` in `ui/` — zero errors
- [ ] T018 [US2] Commit, push, create PR, verify CI green, merge to main

**Checkpoint**: All text renders in JetBrains Mono. Font files bundled in production build.

---

## Phase 3: US3 — Battery & Progress Bars (P2) 🎯 PR #3

**Goal**: Add inline SVG/CSS battery bars to agent panes and a progress bar to MissionBar

- [ ] T019 [US3] Create `ui/src/components/BatteryBar.vue` — inline bar component with color coding (green >50%, amber 25-50%, red <25%), accepts `level` prop (0.0-1.0)
- [ ] T020 [US3] Integrate BatteryBar into `ui/src/components/AgentPane.vue` — replace text-only battery display
- [ ] T021 [US3] Add visual progress bar to `ui/src/components/MissionBar.vue` — filled segment based on collected/target ratio
- [ ] T022 [US3] Run `npx eslint .` and `npm run build` in `ui/` — zero errors
- [ ] T023 [US3] Commit, push, create PR, verify CI green, merge to main

**Checkpoint**: Battery bars visible in agent panes. Mission progress has a visual fill indicator.

---

## Phase 4: US4 — Concentration Heatmap (P2) 🎯 PR #4

**Goal**: Render revealed tiles with a subtle color gradient based on concentration data

- [ ] T024 [US4] Add `tileConcentration(x, y)` computed helper in `ui/src/components/WorldMap.vue` that reads `worldState.concentration_map` (or chunk data)
- [ ] T025 [US4] Update revealed tile `:fill` to interpolate between `var(--bg-revealed)` and a warm amber (`#2a1a08`) based on concentration value
- [ ] T026 [US4] Ensure graceful fallback — if no concentration data, use default revealed color
- [ ] T027 [US4] Run `npx eslint .` and `npm run build` in `ui/` — zero errors
- [ ] T028 [US4] Commit, push, create PR, verify CI green, merge to main

**Checkpoint**: Map tiles show subtle heat gradient. Zero visual regression on tiles without data.

---

## Phase 5: US5 — Responsive Layout (P2) 🎯 PR #5

**Goal**: Add media queries so the app is usable on tablets and phones

- [ ] T029 [US5] Add `@media (max-width: 768px)` rules in `ui/src/App.vue`: stack `.top-row` vertically, full-width columns
- [ ] T030 [US5] Add `@media (max-width: 480px)` rules in `ui/src/App.vue`: reduce padding, smaller fonts, wrap header controls
- [ ] T031 [P] [US5] Add responsive rules in `ui/src/components/AppHeader.vue`: wrap controls, reduce h1 font size
- [ ] T032 [P] [US5] Add responsive rules in `ui/src/components/AgentPane.vue`: adjust height, font sizes
- [ ] T033 [P] [US5] Add responsive rules in `ui/src/components/MiniMap.vue`: limit max height
- [ ] T034 [US5] Run `npx eslint .` and `npm run build` in `ui/` — zero errors
- [ ] T035 [US5] Commit, push, create PR, verify CI green, merge to main

**Checkpoint**: Layout stacks at 768px. All panels readable at 480px.

---

## Phase 6: US6 — EventLog Formatting (P3) 🎯 PR #6

**Goal**: Format common event types as human-readable one-liners instead of raw JSON

- [ ] T036 [US6] Create `formatEventPayload(event)` function in `ui/src/components/EventLog.vue` that returns formatted strings for: move, dig, pickup, analyze, analyze_ground, thinking, charge_rover, alert, assign_mission, mission_success, mission_failed
- [ ] T037 [US6] Update EventLog template to use `formatEventPayload()` instead of `JSON.stringify()` — fallback to JSON for unrecognized event names
- [ ] T038 [US6] Add visual badges/labels for event types (e.g., colored dot or icon prefix)
- [ ] T039 [US6] Run `npx eslint .` and `npm run build` in `ui/` — zero errors
- [ ] T040 [US6] Commit, push, create PR, verify CI green, merge to main

**Checkpoint**: Common events readable at a glance. Unknown events still show JSON.

---

## Phase 7: US7 — Smooth Camera (P3) 🎯 PR #7

**Goal**: Interpolate camera position instead of discrete jumping

- [ ] T041 [US7] Add `targetCamX`/`targetCamY` refs in `ui/src/components/WorldMap.vue` — auto-follow and minimap navigation set the target, not `camX`/`camY` directly
- [ ] T042 [US7] Add `requestAnimationFrame` interpolation loop that moves `camX`/`camY` toward target at a rate that completes within ~300ms
- [ ] T043 [US7] Ensure drag-to-pan still sets `camX`/`camY` directly (no interpolation during drag)
- [ ] T044 [US7] Run `npx eslint .` and `npm run build` in `ui/` — zero errors
- [ ] T045 [US7] Commit, push, create PR, verify CI green, merge to main

**Checkpoint**: Camera slides smoothly on auto-follow and minimap click. Drag remains instant.

---

## Phase 8: US8 — UnoCSS Integration (P3) 🎯 PR #8

**Goal**: Add UnoCSS as an optional utility CSS layer

- [ ] T046 [US8] Install `unocss` in `ui/` via npm
- [ ] T047 [US8] Create `ui/uno.config.js` with `presetUno()` preset
- [ ] T048 [US8] Add UnoCSS Vite plugin to `ui/vite.config.js`
- [ ] T049 [US8] Add `import 'virtual:uno.css'` to `ui/src/main.js`
- [ ] T050 [US8] Verify no visual regressions — existing scoped CSS still works
- [ ] T051 [US8] Run `npx eslint .` and `npm run build` in `ui/` — zero errors
- [ ] T052 [US8] Commit, push, create PR, verify CI green, merge to main

**Checkpoint**: UnoCSS available. No regressions. New utility classes work in templates.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (CSS Tokens)**: No dependencies — start immediately
- **Phase 2 (Font)**: Depends on Phase 1 (uses `--font-mono` variable)
- **Phase 3 (Battery Bars)**: Depends on Phase 1 (uses design token variables)
- **Phase 4 (Heatmap)**: Depends on Phase 1 (uses design token variables)
- **Phase 5 (Responsive)**: Depends on Phase 1 (variables simplify media queries)
- **Phase 6 (EventLog)**: Independent — can run after Phase 1
- **Phase 7 (Camera)**: Independent — no CSS variable dependencies
- **Phase 8 (UnoCSS)**: Independent — additive layer

### Execution Order

Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8

Each phase: implement → lint → build → commit → push → PR → CI green → merge → pull main into worktree → next phase.

---

## Notes

- Total: 52 tasks across 8 phases
- Each phase = 1 PR, merged independently
- All work in worktree at `../agent-one-ui-polish`
- After each merge, reset worktree to latest main before starting next phase
- CI validates: eslint (zero warnings) + vite build (zero errors)
