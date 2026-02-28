# Quickstart: UI Polish Round 3

**Feature**: `004-ui-polish-round3`
**Date**: 2026-02-28

## Prerequisites

- Node.js ≥ 24.0.0
- npm (bundled with Node)
- Running backend server on port 4009 (for full simulation testing)

## Setup

```bash
cd ui
npm install
npm run dev    # Vite dev server on :4089
```

## Implementation Order

Each phase is independently implementable and testable:

### Phase 3: MiniMap Legend
**Files**: `ui/src/components/MiniMap.vue`
**Test**: Open UI → verify legend shows agent types + vein grades below minimap

### Phase 5: Toast Dedupe & Rate-Limit
**Files**: `ui/src/composables/useToasts.js`, `ui/src/components/ToastOverlay.vue`
**Test**: Trigger rapid identical events → verify count badge appears, max 5 toasts visible

### Phase 8: Keyboard Help Overlay
**Files**: `ui/src/components/KeyboardHelp.vue` (new), `ui/src/composables/useKeyboard.js`, `ui/src/App.vue`
**Test**: Press `?` → verify help modal lists all shortcuts

### Phase 6: Loading Skeletons
**Files**: `ui/src/components/SkeletonBlock.vue` (new), `ui/src/App.vue`, `ui/src/components/WorldMap.vue`, `ui/src/components/EventLog.vue`, `ui/src/components/StatsBar.vue`
**Test**: Hard refresh → verify skeleton states appear before WebSocket connects

### Phase 7: Persist UI Preferences
**Files**: `ui/src/composables/usePreferences.js` (new), `ui/src/App.vue`
**Test**: Change zoom/follow/narration → refresh → verify settings restored

### Phase 4: Camera Smoothing
**Files**: `ui/src/components/WorldMap.vue`
**Test**: Click minimap far away → verify fast arrival; follow agent → verify smooth tracking

## Build Verification

```bash
cd ui
npm run build    # Must pass with zero errors
```

## Key Constants Reference

```javascript
// constants.js
TILE_SIZE = 20
VIEWPORT_W = 20
VIEWPORT_H = 20
ZOOM_MIN = 0.7   // in WorldMap.vue
ZOOM_MAX = 2.2   // in WorldMap.vue

// Agent colors
AGENT_COLORS = {
  'station': '#44cc88',
  'rover-mistral': '#e06030',
  'drone-mistral': '#cc44cc',
}

// Vein grade colors
VEIN_COLORS = {
  'pristine': '#e6c619',
  'rich': '#c4a012',
  'high': '#d4760a',
  'medium': '#8a8a8a',
  'low': '#5a5a5a',
  'unknown': '#4a4a6a',
}
```
