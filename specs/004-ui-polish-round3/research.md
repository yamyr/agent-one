# Research: UI Polish Round 3

**Feature**: `004-ui-polish-round3`
**Date**: 2026-02-28

## R1: MiniMap Legend Placement

**Decision**: Inline legend positioned at bottom of MiniMap SVG, rendered as HTML overlay below the SVG canvas.

**Rationale**: SVG-internal text is hard to style and doesn't support CSS flexbox for responsive layout. An HTML overlay below the minimap provides clean styling, text wrapping, and responsive collapse.

**Alternatives considered**:
- SVG `<text>` elements inside minimap — poor styling control, no responsive collapse
- Separate legend component — adds unnecessary component; legend is MiniMap-specific
- Tooltip on hover — doesn't provide persistent reference

## R2: Toast Deduplication Strategy

**Decision**: Content-hash based dedup within a 5-second sliding window. When a duplicate fires, increment a `count` property on the existing toast and reset its dismiss timer.

**Rationale**: Simple, no external state. Content string + type is sufficient for identity. Resetting the timer ensures the toast stays visible while events keep firing.

**Alternatives considered**:
- Event source dedup (group by agent) — too aggressive, different messages from same agent should show
- Debounce all toasts — too aggressive, would delay important unique toasts
- Queue system with max visible — still need dedup on top; queue alone doesn't solve repeat noise

## R3: Toast Rate-Limiting

**Decision**: Hard cap of 5 visible toasts. New toasts beyond the cap replace the oldest non-pinned toast.

**Rationale**: 5 toasts is ~160px of vertical space — visible without overwhelming. Replacing oldest keeps the stream fresh.

**Alternatives considered**:
- Drop excess silently — user misses events
- Queue with FIFO — causes delayed toasts that appear long after the event
- Collapse all into single "N events" summary — loses event detail

## R4: Keyboard Help Overlay Design

**Decision**: Modal overlay triggered by `?` key, listing shortcuts in a 2-column table (key | description). Styled consistently with existing AgentDetailModal.

**Rationale**: Reuses existing modal transition system and styling. `?` is the de-facto standard for keyboard help (GitHub, Gmail, Slack all use it).

**Alternatives considered**:
- Command palette (Cmd+K) — over-engineering for current ~10 shortcuts
- Footer bar with hints — takes permanent screen space
- Tooltip on first visit — easy to miss

## R5: Skeleton/Loading State Pattern

**Decision**: CSS-only skeleton with pulsing gradient animation. A reusable `SkeletonBlock.vue` component that accepts width/height props. Applied to WorldMap, EventLog, and StatsBar areas.

**Rationale**: CSS-only is lightweight (no JS timers), works with `prefers-reduced-motion`, and matches existing dark theme. A reusable component prevents duplication.

**Alternatives considered**:
- Spinner/loading indicator — less modern, doesn't indicate layout shape
- Progressive rendering — complex, requires partial data handling
- External skeleton library — violates no-external-library constraint

## R6: localStorage Persistence

**Decision**: New `usePreferences.js` composable wrapping `localStorage` with JSON serialization, try/catch for safety, and a `PREFS_VERSION` key for future migrations.

**Rationale**: Composable pattern matches existing codebase (useWebSocket, useKeyboard, useToasts). Version key allows breaking-change migrations without corrupting saved state.

**Keys to persist**:
- `mars_zoom` — zoom level (number)
- `mars_follow` — follow agent ID (string | null)
- `mars_narration` — narration enabled (boolean)

**Alternatives considered**:
- sessionStorage — doesn't survive tab close
- IndexedDB — overkill for 3 simple values
- Cookie — wrong tool for client-only state

## R7: Camera Distance-Adaptive Smoothing

**Decision**: Scale LERP speed by clamped distance: `lerpSpeed = clamp(0.08 + distance * 0.01, 0.08, 0.5)`. Short distances (~3 tiles) get 0.11 (precise), long distances (~50 tiles) get 0.5 (fast).

**Rationale**: Linear scaling with clamp provides predictable behavior. The formula ensures short pans stay smooth (0.08 base) while long jumps converge quickly (0.5 cap).

**Alternatives considered**:
- Ease-out curve (cubic) — more complex, harder to tune
- Instant snap for long distances — jarring, loses spatial context
- Fixed higher LERP — makes short pans too snappy
