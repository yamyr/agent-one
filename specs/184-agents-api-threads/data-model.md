# Data Model: Agents API — Persistent Conversation Threads

**Feature**: Persistent Conversation Threads + Training Logger Integration
**Date**: 2026-03-05

---

## Updated Entity: AgentsApiRoverReasoner (additions only)

| New Field | Type | Default | Description |
|-----------|------|---------|-------------|
| `_conversation_id` | `str \| None` | `None` | Mistral conversation thread ID, set after first `start()` |

**State Transitions**:
- None → Set: First `run_turn()` calls `conversations.start()`, stores returned `conversation_id`
- Set → Reused: Subsequent `run_turn()` calls `conversations.append(conversation_id=...)`
- Set → None: Simulation reset creates new reasoner instance

---

## Updated Entity: AgentsApiDroneReasoner (additions only)

| New Field | Type | Default | Description |
|-----------|------|---------|-------------|
| `_conversation_id` | `str \| None` | `None` | Same as Rover |

---

## Updated Entity: AgentsApiStationReasoner (additions only)

| New Field | Type | Default | Description |
|-----------|------|---------|-------------|
| `_conversation_id` | `str \| None` | `None` | Same as Rover |

---

## Updated Entity: Settings (additions only)

| New Field | Type | Default | Description |
|-----------|------|---------|-------------|
| `agents_api_persist_threads` | `bool` | `True` | When True, reuse conversation threads across turns |

**Environment variable**: `AGENTS_API_PERSIST_THREADS=true` (pydantic-settings auto-reads)

---

## Relationships

```
AgentsApiRoverReasoner
  |
  +--> _conversation_id = None (initial)
  |
  +--> run_turn() [first call]
  |      |
  |      +--> client.beta.conversations.start(agent_id=..., inputs=[...])
  |      +--> _conversation_id = response.conversation_id
  |      +--> return {thinking, action}
  |
  +--> run_turn() [subsequent calls, persist_threads=True]
  |      |
  |      +--> client.beta.conversations.append(conversation_id=..., inputs=[...])
  |      +--> return {thinking, action}
  |
  +--> run_turn() [persist_threads=False]
         |
         +--> client.beta.conversations.start(agent_id=..., inputs=[...])
         +--> (conversation_id NOT stored)
         +--> return {thinking, action}
```
