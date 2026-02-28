# Feature Specification: UI Polish Round 3 — Phases 3–8

**Feature Branch**: `004-ui-polish-round3`
**Created**: 2026-02-28
**Status**: Draft
**Input**: User description: "Round 3 Phases 3-8: MiniMap legend, camera smoothing, toast dedupe, loading skeletons, localStorage preferences, keyboard help overlay"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — MiniMap Legend (Priority: P1)

A user watching the simulation glances at the MiniMap but cannot tell what the colored dots represent. A small legend overlay on the MiniMap shows agent type colors and vein grade colors so the user can identify entities at a glance.

**Why this priority**: MiniMap is always visible; without a legend the dots are meaningless to new users.

**Independent Test**: Open the UI, verify the MiniMap shows a legend box with labeled colored entries for each agent type (rover, drone, station) and each vein grade (low through pristine).

**Acceptance Scenarios**:

1. **Given** the MiniMap is visible, **When** the simulation has agents and veins, **Then** a compact legend shows agent type symbols + colors and vein grade swatches + labels.
2. **Given** the viewport is ≤480px (mobile), **When** viewing the MiniMap, **Then** the legend collapses or hides to save space.

---

### User Story 2 — Toast Dedupe & Rate-Limiting (Priority: P1)

A user running the simulation is overwhelmed by repeated identical toasts (e.g., "rover-mistral: found low vein" appearing 10 times in 5 seconds). The toast system deduplicates identical messages and rate-limits to prevent noise.

**Why this priority**: Repeated toasts obscure important events and degrade UX.

**Independent Test**: Trigger rapid identical events; verify only one toast appears with a count badge (e.g., "×3") instead of separate duplicates.

**Acceptance Scenarios**:

1. **Given** a toast "X" is visible, **When** the same message "X" fires again within 5 seconds, **Then** the existing toast shows an incremented count badge instead of creating a new toast.
2. **Given** toasts are firing rapidly (>5 per second), **When** new events arrive, **Then** at most 5 toasts are visible simultaneously; excess are queued or dropped.
3. **Given** two different messages fire, **When** displayed, **Then** each appears as a separate toast (no false dedup).

---

### User Story 3 — Keyboard Help Overlay (Priority: P2)

A user doesn't know what keyboard shortcuts exist. Pressing `?` or clicking a help button opens a modal/overlay listing all available shortcuts.

**Why this priority**: Keyboard shortcuts are invisible without documentation; this makes them discoverable.

**Independent Test**: Press `?` key; verify a modal appears listing all shortcuts (Space, Escape, WASD/Arrows, 0-9, ?) with descriptions.

**Acceptance Scenarios**:

1. **Given** no modal is open and no text input is focused, **When** user presses `?`, **Then** a keyboard help overlay appears listing all shortcuts.
2. **Given** the help overlay is open, **When** user presses `Escape` or clicks outside, **Then** the overlay closes.
3. **Given** the help overlay is open, **When** user presses any shortcut key listed, **Then** the overlay closes and the shortcut executes.

---

### User Story 4 — Startup/Loading Skeletons (Priority: P2)

A user loads the page and sees empty sections with "Waiting for..." text. Instead, skeleton/shimmer placeholders provide visual feedback that data is loading.

**Why this priority**: Perceived performance; users know the app is working during initial load.

**Independent Test**: Hard-refresh the page; verify skeleton states appear in WorldMap, MiniMap, EventLog, and StatsBar areas before data arrives.

**Acceptance Scenarios**:

1. **Given** the WebSocket has not yet connected, **When** the page renders, **Then** WorldMap shows a skeleton grid pattern, EventLog shows pulsing placeholder rows, StatsBar shows placeholder values.
2. **Given** the WebSocket connects and first world state arrives, **When** data is available, **Then** skeletons fade out and real content fades in.

---

### User Story 5 — Persist UI Preferences (Priority: P2)

A user sets zoom to 150%, follows drone-mistral, and pauses narration. After refreshing the page, all preferences are lost. With localStorage persistence, preferences survive page reloads.

**Why this priority**: Avoids repetitive setup; respects user's choices.

**Independent Test**: Set zoom, follow agent, pause narration. Refresh page. Verify all settings are restored.

**Acceptance Scenarios**:

1. **Given** the user changes zoom level, **When** they refresh the page, **Then** zoom is restored to the saved value.
2. **Given** the user follows a specific agent, **When** they refresh, **Then** followAgent is restored (if agent exists in new session).
3. **Given** the user toggles narration off, **When** they refresh, **Then** narration remains off.
4. **Given** localStorage is unavailable or corrupted, **When** loading preferences, **Then** defaults are used without errors.

---

### User Story 6 — Camera Smoothing Refinement (Priority: P3)

When clicking the minimap to navigate 50+ tiles away, the camera takes the same interpolation time as a 3-tile pan. Distance-adaptive smoothing makes long pans faster and short pans precise.

**Why this priority**: Nice-to-have polish; current LERP works but feels sluggish for large jumps.

**Independent Test**: Click minimap far from current viewport; verify camera arrives faster than a close click. Follow agent during movement; verify smooth tracking.

**Acceptance Scenarios**:

1. **Given** the camera is at (0,0) and user navigates to (50,50) via minimap, **When** the camera interpolates, **Then** it arrives in under 1 second (vs current ~3s at LERP 0.15).
2. **Given** the camera is following an agent that moves 1 tile, **When** interpolating, **Then** movement is smooth and precise (no overshooting).

---

### Edge Cases

- What happens when localStorage is full? → Silently fail, use defaults.
- What happens when keyboard shortcuts fire during help overlay animation? → Queue the action.
- What happens when 50+ toasts fire in 1 second? → Hard cap at 5 visible, drop excess.
- What happens when zoom is at min/max and user scrolls further? → No-op, no error.
- What happens when saved followAgent ID doesn't exist in new session? → Fall back to free camera.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: MiniMap MUST display a legend showing agent type colors (rover, drone, station) and vein grade colors (low, medium, high, rich, pristine)
- **FR-002**: MiniMap legend MUST be responsive — collapsed or hidden on viewports ≤480px
- **FR-003**: Toast system MUST deduplicate identical messages within a 5-second window, showing count badge
- **FR-004**: Toast system MUST limit visible toasts to 5 simultaneously
- **FR-005**: Pressing `?` MUST open a keyboard help overlay listing all shortcuts
- **FR-006**: Help overlay MUST be dismissible via Escape or clicking outside
- **FR-007**: Loading skeletons MUST appear for WorldMap, EventLog, and StatsBar before WebSocket connects
- **FR-008**: Skeletons MUST transition to real content when data arrives
- **FR-009**: System MUST persist zoom level, follow agent, and narration enabled state to localStorage
- **FR-010**: System MUST gracefully handle missing/corrupted localStorage (use defaults)
- **FR-011**: Camera smoothing MUST use distance-adaptive LERP (faster for long pans, precise for short)

### Key Entities

- **UIPreferences**: zoom level, follow agent ID, narration enabled — persisted to localStorage
- **ToastState**: message, type, count (dedup counter), created timestamp, id
- **KeyboardShortcut**: key(s), description, action — used for help overlay rendering

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: MiniMap legend correctly shows all agent types and vein grades with matching colors
- **SC-002**: Repeated identical toasts within 5s produce a single toast with count badge
- **SC-003**: No more than 5 toasts visible at once under any event throughput
- **SC-004**: `?` key opens help overlay listing all shortcuts; Escape closes it
- **SC-005**: Skeleton states visible for ≥200ms during initial page load before data arrives
- **SC-006**: Zoom, follow agent, and narration preferences survive page refresh via localStorage
- **SC-007**: Camera arrives at distant targets (>20 tiles) in under 1.5 seconds
- **SC-008**: UI build (`npm run build`) passes with zero errors
