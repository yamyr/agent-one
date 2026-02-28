# Implementation Plan: UI Polish Round 3 — Phases 3–8

**Branch**: `004-ui-polish-round3` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-ui-polish-round3/spec.md`

## Summary

Six UI polish improvements for the Mars mission simulation: MiniMap legend overlay, toast deduplication with rate-limiting, keyboard help overlay, startup loading skeletons, localStorage preference persistence, and camera smoothing refinement. All changes are frontend-only (Vue 3 + Vite), touching existing components and composables with no backend modifications.

## Technical Context

**Language/Version**: JavaScript (ES2022+), Vue 3 (Composition API with `<script setup>`)
**Primary Dependencies**: Vue 3 (3.x), Vite (5.x)
**Storage**: localStorage (browser-side preference persistence)
**Testing**: Vite build verification (`npm run build`), manual QA
**Target Platform**: Web browsers (Chrome, Firefox, Safari — desktop + tablet + mobile)
**Project Type**: Single-page web application (frontend)
**Performance Goals**: 60fps scrolling/animation, <100ms interaction response
**Constraints**: No external UI libraries; all implementations native Vue + CSS
**Scale/Scope**: ~15 Vue components, ~5 composables, 1 constants file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution file is a template (not project-specific). No project-specific gates defined. Applying CLAUDE.md principles:

| Principle | Status | Notes |
|-----------|--------|-------|
| Simplicity First | PASS | Each phase is a focused, minimal change |
| No Laziness | PASS | Root cause fixes, not workarounds |
| Minimal Impact | PASS | Each phase touches 1-3 files maximum |
| Responsive Design | PASS | All new UI elements must be responsive |
| Co-Authoring | PASS | All commits use `agent-one team` attribution |
| Feature Branch | PASS | Working on `004-ui-polish-round3` |

## Project Structure

### Documentation (this feature)

```text
specs/004-ui-polish-round3/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/           # N/A (no external APIs)
```

### Source Code (repository root)

```text
ui/src/
├── components/
│   ├── WorldMap.vue         # Phase 6: camera smoothing
│   ├── MiniMap.vue          # Phase 3: legend overlay
│   ├── EventLog.vue         # (already virtualized in Phase 2)
│   ├── ToastOverlay.vue     # Phase 5: dedupe badge rendering
│   ├── AppHeader.vue        # Phase 6: skeleton state
│   ├── StatsBar.vue         # Phase 6: skeleton state
│   ├── KeyboardHelp.vue     # Phase 8: NEW — help overlay component
│   └── SkeletonBlock.vue    # Phase 6: NEW — reusable skeleton placeholder
├── composables/
│   ├── useToasts.js         # Phase 5: dedupe + rate-limit logic
│   ├── useKeyboard.js       # Phase 8: `?` key binding
│   └── usePreferences.js    # Phase 7: NEW — localStorage persistence
├── constants.js             # Color/size constants (reference only)
└── App.vue                  # Phase 6+7: skeleton wrapper + preference wiring
```

**Structure Decision**: All changes live within the existing `ui/src/` structure. Three new files: `KeyboardHelp.vue` (help overlay), `SkeletonBlock.vue` (reusable skeleton), `usePreferences.js` (localStorage composable).

## Phase Implementation Order

| Phase | Component | Priority | Files Touched | Complexity |
|-------|-----------|----------|---------------|------------|
| 3 | MiniMap Legend | P1 | MiniMap.vue | Low |
| 5 | Toast Dedupe | P1 | useToasts.js, ToastOverlay.vue | Medium |
| 8 | Keyboard Help | P2 | KeyboardHelp.vue (new), useKeyboard.js, App.vue | Medium |
| 6 | Loading Skeletons | P2 | SkeletonBlock.vue (new), App.vue, WorldMap.vue, EventLog.vue, StatsBar.vue | Medium |
| 7 | localStorage Prefs | P2 | usePreferences.js (new), App.vue | Medium |
| 4 | Camera Smoothing | P3 | WorldMap.vue | Low |

## Complexity Tracking

No constitution violations to justify — all changes are minimal, focused, and within existing architecture.
