# Research: Human-in-the-Loop (UiRequest::Confirm)

**Feature**: Human-in-the-Loop Confirmation for High-Risk Rover Actions
**Date**: 2026-03-05
**Branch**: `183-human-in-the-loop`

---

## R1: How should the rover agent loop pause for confirmation?

**Decision**: Use an `asyncio.Event` stored in the Host, keyed by `request_id`. The rover tool `request_confirm` creates the Event, emits the WebSocket message, then `await`s the Event with a timeout. The `/api/confirm` endpoint sets the Event with the human's response.

**Rationale**: The existing `host.paused` flag pauses ALL agents globally — we need per-agent, per-request blocking. `asyncio.Event` is the standard asyncio primitive for "wait until something happens" and supports timeout via `asyncio.wait_for()`. Storing in Host aligns with the existing inbox/routing pattern. Only ONE pending confirmation per agent at a time (simplicity).

**Alternatives Considered**:
- **Global pause + inbox command**: Rejected. Would pause all agents, not just the requesting rover.
- **Polling pending_commands each tick**: Rejected. Wastes ticks and adds latency. Direct Event await is cleaner.
- **asyncio.Queue for responses**: Rejected. Over-engineered for single-value response; Event is simpler.
- **asyncio.Condition**: Rejected. Event is sufficient for binary signal (set/not set).

---

## R2: Where should the request_confirm tool live?

**Decision**: Define `REQUEST_CONFIRM_TOOL` in `server/app/agent.py` alongside existing rover tools (ROVER_TOOLS list). The execution logic lives in RoverLoop.tick() because it needs access to `host` and asyncio.

**Rationale**: Unlike other tools that execute via `execute_action()` in world.py (which mutates WORLD state), `request_confirm` doesn't mutate world state — it's a communication action. It needs access to the Host for broadcasting and the asyncio event loop for waiting. This makes the tick method the natural home. The tool DEFINITION (schema) goes with other rover tools; the EXECUTION is special-cased in the tick.

**Alternatives Considered**:
- **Add to world.py execute_action()**: Rejected. Confirmation is not a world state mutation.
- **Add to host.py**: Partial fit, but the await must happen in the agent's async context (tick method).
- **Separate module**: Rejected. Over-engineering for a single tool.

---

## R3: How should confirmation state be tracked?

**Decision**: Add a `_pending_confirms` dict to the Host: `{request_id: {"agent_id": str, "question": str, "event": asyncio.Event, "response": bool|None, "tick": int}}`. One pending confirmation per agent max.

**Rationale**: Host already manages per-agent communication (inboxes, routing). Confirmation state is transient (not persisted in WORLD). Using Host keeps it separate from simulation state. The `request_id` (UUID) links the request to the response. The `event` field holds the asyncio.Event for await/set. The `response` field is set by `/api/confirm` before setting the Event.

**Alternatives Considered**:
- **Store in WORLD dict**: Rejected. Confirmation is transient communication state, not simulation state. Would pollute snapshots.
- **Store in agent state**: Rejected. The response comes from the API endpoint, which has access to Host, not agent internals.
- **Store in a separate ConfirmationManager class**: Rejected. Host already manages agent communication; adding to it is more cohesive.

---

## R4: How should the `/api/confirm` endpoint work?

**Decision**: Add `POST /api/confirm` in `server/app/main.py` accepting `{"request_id": str, "confirmed": bool}`. It looks up the pending confirm in Host, sets the response, and sets the asyncio.Event. Also broadcasts a `confirm_response` event via WebSocket.

**Rationale**: Follows the pattern of existing POST endpoints (`/simulation/pause`, `/mission/abort`, `/rover/{id}/recall`). Simple JSON body, returns `{"ok": true}`. Broadcasting the response lets the UI dismiss the modal and shows the decision in the event log.

**Alternatives Considered**:
- **WebSocket bidirectional**: Rejected. The WS endpoint currently only receives keepalive pings. Adding structured input handling adds complexity. REST is simpler and follows existing patterns.
- **PUT endpoint**: Rejected. POST is idiomatic for actions/commands in this codebase.

---

## R5: How should timeout handling work?

**Decision**: Default timeout of 30 seconds, configurable per request. Use `asyncio.wait_for(event.wait(), timeout=timeout)` in the rover tick. On `asyncio.TimeoutError`, treat as denied. Broadcast a `confirm_timeout` event so the UI can dismiss the modal.

**Rationale**: 30 seconds gives the human enough time to read and decide without stalling the simulation too long. The rover's tick is already async, so `wait_for` integrates naturally. Timeout-as-denial is the safe default (don't proceed with risky action if human doesn't respond).

**Alternatives Considered**:
- **No timeout (block indefinitely)**: Rejected. Would freeze the rover permanently if human is AFK.
- **Short timeout (5s)**: Rejected. Too short for a meaningful decision.
- **Timeout as approval**: Rejected. Unsafe — silence should mean "no" for high-risk actions.

---

## R6: How should the frontend modal work?

**Decision**: Create `ConfirmModal.vue` component rendered in `SimulationPage.vue`. It listens for `confirm_request` events via the existing WebSocket composable. Shows agent name, question text, and a countdown timer. Confirm/Deny buttons POST to `/api/confirm`. Auto-dismisses on timeout or response.

**Rationale**: Follows the existing modal pattern (AgentDetailModal, HelpModal) with Transition wrapper. The countdown timer adds urgency and transparency. Using the existing `onSimEvent` callback in SimulationPage routes the event. The modal should be high z-index (above other modals) since it's time-critical.

**Alternatives Considered**:
- **Toast notification instead of modal**: Rejected. Too easy to miss for a critical decision.
- **Inline in AgentPane**: Rejected. Too small; confirmation needs prominence and focus.
- **Separate overlay page**: Rejected. Over-engineered; a modal is sufficient.

---

## R7: How should the rover system prompt guide usage?

**Decision**: Add a "HUMAN CONFIRMATION" section to the rover system prompt encouraging use before: (1) entering tiles adjacent to active storm zones, (2) crossing hazard tiles (mountains, erupting geysers), (3) moving with battery below 15%. Discourage use for routine moves.

**Rationale**: The prompt should be specific about when to use the tool. Vague guidance ("use for risky actions") would either lead to overuse (every move) or underuse. Storm zones and hazard tiles are the most dramatic scenarios from the ROADMAP vision. Low-battery moves add a resource management dimension.

**Alternatives Considered**:
- **No prompt guidance (rely on tool description)**: Rejected. LLMs need explicit behavioral cues.
- **Mandatory confirmation for all storm moves**: Rejected. Should be LLM's judgment call, not hardcoded.
- **Confirmation for dig/analyze too**: Rejected. Only movement into danger warrants confirmation. Dig/analyze are local actions.
