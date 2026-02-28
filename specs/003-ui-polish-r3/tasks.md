# Tasks: UI Polish Round 3

**Status**: Active
**Progress**: 2/8 Phases Complete

## Phase 1: Accessibility Baseline (R3P1) ✅
- [x] T001 Add ARIA labels, roles, and focus-visible outlines
- [x] T002 Add prefers-reduced-motion media query
- [x] T003 Implement rover carried-ore visuals (bonus)

## Phase 2: EventLog Virtualization (R3P2) ✅
- [x] T004 Implement windowing/limit logic in `EventLog.vue`
- [x] T005 Limit backing array in `useWebSocket` (200 items)

## Phase 3: MiniMap Legends (R3P3) 🎯
**Goal**: Explain map symbology.
- [ ] T007 Create `MapLegend.vue` component
- [ ] T008 Integrate into `MiniMap.vue` as a toggleable overlay

## Phase 4: Camera Inertia (R3P4)
**Goal**: Cinematic smooth panning.
- [ ] T009 Refine `cameraLoop` in `WorldMap.vue` with adaptive lerp

## Phase 5: Toast Dedupe (R3P5)
**Goal**: Reduce visual noise.
- [ ] T010 Update `useToasts.js` to reject duplicate messages within N seconds

## Phase 6: Loading Skeletons (R3P6)
**Goal**: Better startup UX.
- [ ] T011 Create skeleton styles/components
- [ ] T012 Show skeletons when `!worldState`

## Phase 7: Persisted Prefs (R3P7)
**Goal**: Save user config.
- [ ] T013 Create `usePreferences` composable
- [ ] T014 Wire up zoom, narration, and follow-mode to prefs

## Phase 8: Help Overlay (R3P8)
**Goal**: Discoverability.
- [ ] T015 Create `HelpModal.vue` with shortcuts
- [ ] T016 Bind `?` key to toggle help
