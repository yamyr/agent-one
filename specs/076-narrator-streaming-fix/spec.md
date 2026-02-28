# Feature Specification: Non-Blocking Narration Streaming

**Feature Branch**: `076-narrator-streaming-fix`  
**Created**: 2026-03-01  
**Status**: Draft  
**Input**: User description: "Issue #92: perf: narrator streaming blocks the event loop with synchronous Mistral iteration; ensure non-blocking narration streaming and preserve behavior."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Keep Simulation Responsive During Narration (Priority: P1)

As a mission operator, I need simulation updates to continue while narration text is being streamed, so the UI and agent activity do not appear frozen.

**Why this priority**: Event-loop blocking stalls core simulation behavior and degrades the primary mission-control experience.

**Independent Test**: Trigger narration streaming while simulation ticks are running; verify tick updates and websocket event delivery continue without visible pause.

**Acceptance Scenarios**:

1. **Given** narration generation is active, **When** narration chunks are received, **Then** simulation tick events continue to be emitted during the same period.
2. **Given** narration generation is active, **When** operators observe real-time telemetry, **Then** telemetry updates continue at normal cadence and do not freeze.

---

### User Story 2 - Preserve Narration Chunk Behavior (Priority: P2)

As a mission operator, I need streamed narration chunks to remain ordered and readable, so commentary quality is preserved.

**Why this priority**: Performance fixes must not degrade user-facing narration output.

**Independent Test**: Run narration stream and verify chunk ordering, concatenation behavior, and event names remain unchanged.

**Acceptance Scenarios**:

1. **Given** narration streaming starts, **When** chunks are emitted, **Then** chunks arrive in source order without duplication.
2. **Given** narration streaming is complete, **When** final text is assembled, **Then** content is equivalent to expected streamed output.

---

### User Story 3 - Handle Streaming Failures Gracefully (Priority: P3)

As a mission operator, I need narration failures to degrade gracefully without impacting simulation continuity.

**Why this priority**: Fault tolerance prevents narration failures from becoming system-wide incidents.

**Independent Test**: Simulate streaming errors and verify simulation and websocket pipeline continue operating.

**Acceptance Scenarios**:

1. **Given** narration streaming encounters an upstream error, **When** the error occurs, **Then** narration processing exits safely and simulation ticks continue.
2. **Given** partial narration chunks were emitted before failure, **When** stream ends with error, **Then** no invalid or malformed events are emitted.

### Edge Cases

- Stream returns no chunks for a request.
- Stream emits chunks slowly over several seconds.
- Stream yields unexpected event envelope types.
- Back-to-back narration requests overlap in time.
- Client websocket consumers are temporarily slower than narration emission.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST process narration stream iteration in a way that does not block the main asynchronous event loop.
- **FR-002**: The system MUST continue emitting simulation and telemetry events while narration streaming is active.
- **FR-003**: The system MUST preserve narration chunk order and existing event semantics for streamed text.
- **FR-004**: The system MUST handle narration stream errors without interrupting simulation tick progression.
- **FR-005**: The system MUST include automated tests that assert non-blocking behavior under streamed narration load.
- **FR-006**: The system MUST include automated tests that assert narration chunk behavior remains backward-compatible after the fix.

### Key Entities *(include if feature involves data)*

- **Narration Stream Event**: A single upstream narration emission item that may or may not contain text content.
- **Narration Chunk Message**: Outbound websocket payload representing a partial narration text segment sent to clients.
- **Simulation Tick Event**: Periodic world update signal that must continue during narration generation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: During narration streaming, simulation tick emission cadence shows no freeze interval greater than one expected tick window.
- **SC-002**: In a controlled test that streams narration for at least 3 seconds, tick and telemetry events continue throughout the stream window.
- **SC-003**: 100% of existing narration-streaming behavior checks (ordering and emitted event type) pass after the fix.
- **SC-004**: New regression tests for non-blocking narration streaming pass consistently in CI.
