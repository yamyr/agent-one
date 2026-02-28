# Feature Specification: WS Reconnect Preserves Event History

**Feature Branch**: `072-ws-reconnect-state`  
**Created**: 2026-03-01  
**Status**: Draft  
**Input**: GitHub Issue #72 — WebSocket reconnect resets simulation state

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preserve Events on Reconnect (Priority: P1)

As a user watching the simulation, when my WebSocket connection drops and reconnects, I want to keep my existing event log so I don't lose context of what happened during the session.

**Why this priority**: Losing all events on every reconnect (which happens every 2s on disconnect) makes the UI unusable during network hiccups.

**Independent Test**: Disconnect and reconnect WS; verify event log is preserved while worldState is refreshed from server.

**Acceptance Scenarios**:

1. **Given** events are accumulated in the log, **When** the WS reconnects, **Then** existing events remain in the list
2. **Given** a fresh page load (first connect), **When** WS connects, **Then** events start empty (clean slate)
3. **Given** a reconnect occurs, **When** WS opens, **Then** worldState is cleared (server will repopulate it)

### Edge Cases

- First connect must still clear events (fresh start)
- Multiple rapid reconnects should not accumulate stale state

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: On first WS connect, `events` MUST be cleared (empty array)
- **FR-002**: On subsequent reconnects, `events` MUST be preserved
- **FR-003**: `worldState` MUST always be cleared on any connect (server repopulates)
- **FR-004**: A `isFirstConnect` flag MUST track first vs subsequent connections

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: ESLint passes with zero errors
- **SC-002**: `npm run build` succeeds
- **SC-003**: Event log survives WS reconnect in browser testing
