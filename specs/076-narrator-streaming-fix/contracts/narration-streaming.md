# Contract: Narration Streaming Behavior (Issue #92)

## Scope

Behavioral contract for server-side narration streaming responsiveness and compatibility.

## Must Preserve

1. Narration chunk event name and payload structure remain unchanged.
2. Chunk order remains source-ordered.
3. Existing consumers continue to parse events without schema updates.

## Must Improve

1. Narration stream processing must not block core async loop progression.
2. Simulation/websocket activity continues while narration stream is active.
3. Error path does not freeze or deadlock simulation.

## Verification Contract

1. Automated test proves progress in simulation-related operations during active narration stream window.
2. Automated test proves chunk behavior parity after fix (order and content consistency).
