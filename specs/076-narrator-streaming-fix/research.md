# Research: Non-Blocking Narration Streaming

**Branch**: `076-narrator-streaming-fix` | **Date**: 2026-03-01

## Decision 1: Move Stream Iteration Off Event Loop

**Decision**: Execute synchronous narration stream iteration in a worker thread boundary so the async loop remains free to schedule simulation and websocket tasks.

**Rationale**: Issue #92 identifies event-loop stalls caused by synchronous waiting during stream iteration. Offloading iteration avoids loop starvation while preserving streaming semantics.

**Alternatives considered**:
- Keep synchronous iteration in coroutine and reduce polling frequency - rejected (still blocks during waits).
- Switch to non-streaming narration only - rejected (regresses user experience).

## Decision 2: Preserve Event Contract and Ordering

**Decision**: Keep existing narration event names and payload structure unchanged, preserving chunk-by-chunk order.

**Rationale**: UI and existing tests rely on current event semantics; performance fix should be behavior-preserving.

**Alternatives considered**:
- Introduce new event types for threaded streaming - rejected (unnecessary protocol churn).

## Decision 3: Add Regression Validation for Loop Responsiveness

**Decision**: Add focused tests that assert simulation/task progression continues while narration stream is active.

**Rationale**: Prevents recurrence of hidden blocking regressions and validates user-visible responsiveness.

**Alternatives considered**:
- Rely only on manual observation - rejected (not deterministic for CI).
