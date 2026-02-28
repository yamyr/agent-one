# Feature Specification: Replace Logging f-strings with Lazy % Formatting

**Feature Branch**: `073-logging-fstrings`  
**Created**: 2026-03-01  
**Status**: Draft  
**Input**: GitHub Issue #73 — logging f-strings in broadcast.py

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Use Lazy Logging Format (Priority: P1)

As a developer, I want logging calls to use lazy `%`-style formatting instead of f-strings, so that string interpolation is deferred until the message is actually emitted (per Python logging best practices and ruff G004).

**Why this priority**: f-strings in logging calls eagerly evaluate even when the log level is disabled, wasting CPU. This is a best-practice fix.

**Independent Test**: Run ruff check — no G004 violations should appear.

**Acceptance Scenarios**:

1. **Given** `broadcast.py` uses f-strings in `logger.info()`, **When** I replace them with `%`-style, **Then** ruff check passes with no G004 warnings
2. **Given** the fix is applied, **When** all tests run, **Then** all 287+ tests pass

### Edge Cases

- Ensure the `%d` format specifier correctly formats `len(self._connections)`

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `broadcast.py` line 22 MUST use `logger.info("Client connected (%d total)", len(self._connections))`
- **FR-002**: `broadcast.py` line 26 MUST use `logger.info("Client disconnected (%d total)", len(self._connections))`

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `uv run ruff check app/` passes with zero errors
- **SC-002**: `uv run rut tests/` passes with all tests green
