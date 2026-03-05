# Research: Agents API — Persistent Conversation Threads

**Feature**: Persistent Conversation Threads + Training Logger Integration
**Date**: 2026-03-05
**Branch**: `184-agents-api-threads`

---

## R1: How does the Mistral Conversations API work?

**Decision**: Use `client.beta.conversations.start()` for the first turn and `client.beta.conversations.append()` for subsequent turns, storing the `conversation_id` on the reasoner instance.

**Rationale**: The installed SDK (mistralai 1.12.4) provides `client.beta.conversations` with `start()` and `append()` methods. `start()` returns a `ConversationResponse` with a stable `conversation_id`. `append()` takes this `conversation_id` and adds new messages to the existing thread. The conversation_id is stable across appends (confirmed from SDK source). The current code already uses `conversations.start()` but discards the ID each turn.

**Alternatives Considered**:
- **`client.agents.complete()`**: Rejected. This is the older non-beta path without conversation threading.
- **`client.beta.conversations.restart()`**: Not needed. Restart is for branching from a specific entry, not normal continuation.
- **Streaming variants**: Out of scope. `start_stream`/`append_stream` add complexity for no benefit in this batch-processing loop.

---

## R2: Where should conversation_id be stored?

**Decision**: Add `_conversation_id: str | None = None` as an instance attribute on each reasoner class (`AgentsApiRoverReasoner`, `AgentsApiDroneReasoner`, `AgentsApiStationReasoner`).

**Rationale**: The reasoner is instantiated once per agent and lives for the duration of the simulation. Storing on the instance keeps it co-located with `_mistral_agent_id`. On simulation reset, new reasoner instances are created (via `_register_agents()` in main.py), which naturally clears the conversation_id.

**Alternatives Considered**:
- **Store in WORLD state**: Rejected. Conversation IDs are Mistral-internal, not simulation state.
- **Store in Host**: Rejected. Host manages communication routing, not LLM session state.
- **Store in config/env**: Rejected. Conversation IDs are ephemeral per-session, not configuration.

---

## R3: How should the start/append switching work?

**Decision**: In `run_turn()`, check `self._conversation_id is None`. If None, call `start()` and store the returned `conversation_id`. Otherwise, call `append(conversation_id=self._conversation_id)`. Both return `ConversationResponse` with the same `outputs` structure.

**Rationale**: The response structure is identical for both `start()` and `append()` — both return `ConversationResponse` with `.outputs` and `.conversation_id`. The existing `_parse_conversation_response()` function works unchanged. The only difference is whether we pass `agent_id` (start) or `conversation_id` (append).

**Alternatives Considered**:
- **Always start, pass full history manually**: Rejected. Defeats the purpose of the Conversations API.
- **Use `store=False`**: Rejected. Without server-side storage, `append()` has nothing to append to.

---

## R4: How should the config toggle work?

**Decision**: Add `agents_api_persist_threads: bool = True` to the Settings class. When False, skip storing the conversation_id (always call `start()`). When True (default), store and reuse the conversation_id.

**Rationale**: Simple boolean toggle. Default True because thread persistence is the whole point of this feature. False is useful for debugging (seeing each turn in isolation) or cost control (shorter contexts = fewer tokens).

**Alternatives Considered**:
- **Environment variable only**: Rejected. pydantic-settings already reads from env vars automatically.
- **Per-agent toggle**: Rejected. Over-engineering. A global toggle is sufficient.

---

## R5: Where should training logger integration happen?

**Decision**: The training logger is already wired in the Loop classes (`RoverAgentsApiLoop`, `DroneAgentsApiLoop`, `StationAgentsApiLoop`) which inherit from `RoverLoop`, `DroneLoop`, `StationLoop` respectively. The `# TODO` at line 113 of agents_api.py is misleading — training logging happens in the loop's `tick()` method, not in the reasoner. However, we need to verify the Agents API loops actually call the parent tick which has the training logger code.

**Rationale**: Looking at the actual inheritance: `RoverAgentsApiLoop` extends `RoverLoop` and only overrides the reasoner. The `tick()` method from `RoverLoop` (which contains `training_logger.log_turn()`) runs unchanged. The `# TODO` comment should be removed since training logging already works through inheritance. However, the `model` field on TrainingTurn should correctly reflect the Agents API model.

**Alternatives Considered**:
- **Duplicate training logger calls in agents_api.py**: Rejected. Would double-log since the parent tick already logs.
- **Override tick() in Agents API loops**: Rejected. The parent tick already handles everything correctly.
