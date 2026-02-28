# Research: Fix Narration Text Display & Voice Toggle

**Branch**: `001-fix-narration-ui` | **Date**: 2026-02-28

## Research Summary

No unknowns or NEEDS CLARIFICATION items. All 4 bugs were identified through direct code inspection.

## Decision 1: WebSocket Event Matching Strategy

**Decision**: Match narrator events on `event.name` field instead of `event.type`

**Rationale**: The server narrator broadcasts all events with `type: "narration"` and uses the `name` field to distinguish between `"narration"` (full text + optional audio) and `"narration_chunk"` (streaming text fragment). The UI WebSocket handler was incorrectly checking `event.type` for the chunk distinction, which always fails since both event types share `type: "narration"`.

**Alternatives considered**:
- Change server to use different `type` values — rejected because `type: "narration"` is the correct semantic grouping, and `name` is the discriminator per the project's event protocol
- Add a separate field — rejected as unnecessary complexity

## Decision 2: Voice Toggle State Initialization

**Decision**: Initialize `narrationEnabled` to `false` and fetch actual state from `/api/narration/status` on WebSocket connect

**Rationale**: Server defaults to `narration_enabled = False` (config.py). The UI was hardcoding `true`, creating an immediate state mismatch. Fetching on connect ensures the UI always reflects reality.

**Alternatives considered**:
- Include narration state in the WebSocket world state payload — rejected as it would require server changes and narration state is not part of world state
- Use localStorage to persist toggle — rejected as it would still diverge from server state after restarts
