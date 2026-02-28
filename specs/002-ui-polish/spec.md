# Feature Specification: UI Polish & Beautification

**Feature Branch**: `feature/ui-polish`
**Created**: 2026-02-28
**Status**: Draft
**Input**: User description: "improve and upgrade the UI for better development experience and game design beautification"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - CSS Design Tokens (Priority: P1)

As a developer, I want all colors, spacing, and radii defined as CSS custom properties in one place, so the UI is consistent and future-theming is trivial.

**Why this priority**: Foundation for all other visual improvements. Zero risk, immediate consistency.

**Independent Test**: All components render identically to current state, but colors come from `var(--*)` instead of hardcoded hex values.

**Acceptance Scenarios**:

1. **Given** the app loads, **When** I inspect any component, **Then** border colors, backgrounds, and text colors reference CSS custom properties
2. **Given** I change `--bg-primary` in `:root`, **When** the page re-renders, **Then** all backgrounds update globally

---

### User Story 2 - Font Upgrade (Priority: P1)

As a user, I want the UI to use JetBrains Mono instead of Courier New, so text is crisper and more readable at small sizes.

**Why this priority**: 15 minutes, instant visual improvement, zero functional risk.

**Independent Test**: All text renders in JetBrains Mono. No layout shifts.

**Acceptance Scenarios**:

1. **Given** the app loads, **When** I inspect `body`, **Then** `font-family` is `'JetBrains Mono', monospace`
2. **Given** the font package is installed, **When** I build for production, **Then** font files are bundled (no CDN requests)

---

### User Story 3 - Battery & Progress Visualizations (Priority: P2)

As a user watching the simulation, I want to see battery levels as colored bars (not just text) and mission progress as a visual bar, so I can quickly gauge agent health and mission status at a glance.

**Why this priority**: High visual impact, makes telemetry much more readable.

**Independent Test**: Agent panes show colored battery bars. Mission bar shows a filled progress indicator.

**Acceptance Scenarios**:

1. **Given** a rover has 75% battery, **When** I look at its pane, **Then** I see a green bar filled to ~75%
2. **Given** a rover has 20% battery, **When** I look at its pane, **Then** the bar is red
3. **Given** mission progress is 2/5, **When** I look at the mission bar, **Then** a filled segment covers ~40%

---

### User Story 4 - Concentration Heatmap on Map Tiles (Priority: P2)

As a user, I want revealed map tiles to show a subtle heatmap overlay based on ground concentration data, so I can visually identify promising areas for exploration.

**Why this priority**: Makes the map dramatically more informative with data already available from the backend.

**Independent Test**: Revealed tiles near core deposits appear slightly warmer (amber tint), while low-concentration tiles stay dark.

**Acceptance Scenarios**:

1. **Given** a tile has concentration > 0.5, **When** it is revealed, **Then** it has a warm amber tint
2. **Given** a tile has concentration ~0, **When** it is revealed, **Then** it looks like current revealed tiles (dark)
3. **Given** no concentration data exists, **When** tiles render, **Then** they use the default revealed color (graceful fallback)

---

### User Story 5 - Responsive Layout (Priority: P2)

As a user on a tablet or phone, I want the layout to stack vertically and remain usable, so I can watch the mission on any device.

**Why this priority**: CLAUDE.md explicitly requires responsive design — currently only NarrationPlayer has a media query.

**Independent Test**: At 768px width, the top-row stacks vertically. At 480px, all panels are full-width and readable.

**Acceptance Scenarios**:

1. **Given** viewport is < 768px, **When** I view the app, **Then** map and agent panes stack vertically
2. **Given** viewport is < 480px, **When** I view the app, **Then** header controls wrap, font sizes reduce, everything is usable

---

### User Story 6 - EventLog Formatting (Priority: P3)

As a user, I want EventLog entries to be human-readable one-liners with icons/badges instead of raw JSON dumps, so I can quickly scan mission activity.

**Why this priority**: Usability improvement — raw JSON is developer-facing, not user-facing.

**Independent Test**: Move events show "rover-mistral: (2,3) → (3,3)", dig events show "rover-mistral: dig at (3,3)", etc. No raw JSON for common event types.

**Acceptance Scenarios**:

1. **Given** a move event arrives, **When** it renders in EventLog, **Then** it shows a compact formatted line, not JSON
2. **Given** an unknown event type arrives, **When** it renders, **Then** it falls back to JSON (backward compatible)

---

### User Story 7 - Smooth Camera Interpolation (Priority: P3)

As a user, I want camera panning (auto-follow and manual) to smoothly interpolate instead of jumping discretely, so the viewport feels cinematic.

**Why this priority**: Polish. The map already works, this just makes it feel better.

**Independent Test**: When auto-follow moves the camera, the viewport slides smoothly over 300ms instead of jumping instantly.

**Acceptance Scenarios**:

1. **Given** auto-follow is active, **When** the rover moves, **Then** the camera slides to center on it over ~300ms
2. **Given** I click on the minimap, **When** the camera navigates, **Then** it slides to the target position

---

### User Story 8 - UnoCSS Integration (Priority: P3)

As a developer, I want UnoCSS available as an optional utility layer alongside existing scoped CSS, so new components can be built faster with atomic classes.

**Why this priority**: DX improvement but largest setup cost. Additive — doesn't touch existing styles.

**Independent Test**: Adding `class="text-sm text-gray-400"` to any element applies the expected styles. Existing scoped CSS continues to work.

**Acceptance Scenarios**:

1. **Given** UnoCSS is installed, **When** I use `class="flex gap-2"` in a template, **Then** it renders correctly
2. **Given** existing scoped CSS exists, **When** UnoCSS is active, **Then** no visual regressions occur
3. **Given** CI runs, **When** `npm run build` executes, **Then** the build succeeds with UnoCSS in the pipeline

---

### Edge Cases

- What happens if `@fontsource/jetbrains-mono` fails to load? Fallback to system monospace via font stack.
- What happens if concentration data is missing from world state? Heatmap gracefully degrades to default tile color.
- What happens if UnoCSS conflicts with existing scoped styles? UnoCSS utilities have lower specificity than scoped styles — no conflicts.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All hardcoded colors MUST be replaced with CSS custom properties in a central `:root` block
- **FR-002**: Font MUST be self-hosted via npm package (no CDN dependency)
- **FR-003**: Battery visualization MUST use color coding: green (>50%), amber (25-50%), red (<25%)
- **FR-004**: Heatmap MUST gracefully fall back when concentration data is absent
- **FR-005**: Layout MUST be usable at 768px and 480px breakpoints
- **FR-006**: EventLog formatting MUST fall back to JSON for unknown event types
- **FR-007**: Camera interpolation MUST not exceed 300ms to avoid feeling sluggish
- **FR-008**: UnoCSS MUST NOT break existing scoped CSS or cause visual regressions
- **FR-009**: All changes MUST pass existing CI pipeline (eslint, vite build)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero visual regressions — existing UI looks the same or better after each PR
- **SC-002**: `npm run build` succeeds with zero errors after each change
- **SC-003**: `npx eslint .` passes with zero warnings after each change
- **SC-004**: All 8 improvements merged to main via individual PRs with green CI
