# Feature Specification: Remove Stale /mission/status Endpoint

**Feature Branch**: `069-stale-mission-status`  
**Created**: 2026-03-01  
**Status**: Draft  
**Input**: GitHub Issue #69 — stale /mission/status endpoint returns hardcoded data

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Remove Stale Endpoint (Priority: P1)

As a developer, I want the stale `/mission/status` endpoint in `views.py` removed so that the only mission status endpoint is the real one in `main.py`, preventing confusion and incorrect API responses.

**Why this priority**: The stale endpoint returns hardcoded `{"status": "idle", "mission": None}` which conflicts with the real mission status available through the world state.

**Independent Test**: After removal, all remaining tests pass. The test for the stale endpoint is also removed.

**Acceptance Scenarios**:

1. **Given** the stale endpoint exists in `views.py`, **When** I remove it, **Then** the router no longer registers `/mission/status` from `views.py`
2. **Given** a test exists for the stale endpoint, **When** I remove the test, **Then** all remaining tests pass cleanly

### Edge Cases

- Verify no other code depends on the removed endpoint
- Ensure the WebSocket endpoint in `views.py` remains unaffected

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST NOT have a stale `/mission/status` endpoint in `views.py`
- **FR-002**: The test `test_mission_status_returns_idle` MUST be removed from `test_health.py`
- **FR-003**: All remaining tests MUST pass
- **FR-004**: Linting (ruff format + ruff check) MUST pass

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `views.py` contains only the WebSocket endpoint, no REST endpoints
- **SC-002**: `test_health.py` contains only the health check test
- **SC-003**: `uv run ruff check app/ tests/` passes with zero errors
- **SC-004**: `uv run rut tests/` passes with all tests green
