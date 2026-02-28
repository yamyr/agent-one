# RAG Service Contract

**Module**: `server/app/rag.py`

## Functions

### `init_rag()`
Initialize RAG system: create SurrealDB tables/indexes, load and embed knowledge chunks.
Called once during app startup in `lifespan()`.

**Signature**: `async def init_rag() -> None`
**Side effects**: Creates `knowledge_chunk` and `mission_memory` tables in SurrealDB. Embeds and stores knowledge chunks if not already present.

---

### `retrieve_context(agent_id: str) -> dict`
Retrieve relevant knowledge + memory for an agent's current situation.
Called before each agent's `run_turn()` in the tick loop.

**Signature**: `async def retrieve_context(agent_id: str) -> dict`

**Input**: Agent ID (used to read position, battery, recent actions from WORLD)

**Output**:
```python
{
    "knowledge_chunks": [
        {"content": "Basalt veins near crater rims...", "source": "mars_geology", "distance": 0.23},
        ...
    ],
    "memory_entries": [
        {"content": "Analyzed vein at (5,3), grade=high", "agent_id": "drone-mistral", "distance": 0.31},
        ...
    ],
    "query_text": "Rover at (5,3), battery 80%, found unknown vein"
}
```

**Constraints**:
- Max 3 knowledge chunks returned
- Max 3 memory entries returned
- Total retrieved text must not exceed 800 tokens
- Timeout: 2 seconds (return empty on timeout)

---

### `store_memory(agent_id: str, content: str, action_name: str, success: bool) -> None`
Store a new mission memory entry with embedding.
Called after each `execute_action()` completes.

**Signature**: `async def store_memory(agent_id: str, content: str, action_name: str, success: bool) -> None`

**Input**:
- `agent_id`: Agent identifier
- `content`: Memory text (same format as `record_memory()`)
- `action_name`: Action that triggered this (move, analyze, dig, etc.)
- `success`: Whether the action succeeded

**Side effects**: Embeds text via Mistral, stores in SurrealDB `mission_memory` table.

---

### `format_rag_context(rag_context: dict) -> str`
Format retrieved RAG context as prompt text for injection into `_build_context()`.

**Signature**: `def format_rag_context(rag_context: dict) -> str`

**Output example**:
```
== Mars Knowledge ==
- Basalt veins near crater rims tend to be higher grade due to volcanic mineral concentration
- Concentration readings above 0.6 indicate proximity to high-grade or pristine deposits within 2-3 tiles

== Relevant Past Experience ==
- [drone-mistral, tick 12] Scanned area around (5,8), peak concentration=0.742
- [rover-mistral, tick 8] Analyzed vein at (3,2), grade=low, qty=25
```

---

### `upload_to_mistral_library(doc_path: str) -> str`
Upload a knowledge document to Mistral's hosted Libraries API.
Called during setup/init. Returns library ID.

**Signature**: `async def upload_to_mistral_library(doc_path: str) -> str`

**Output**: Mistral library UUID string

---

## WebSocket Broadcast Extension

### RAG Context in Agent Events

When agents broadcast thinking/action events, optionally include RAG context:

```python
# Extended thinking event payload
{
    "source": "rover-mistral",
    "type": "event",
    "name": "thinking",
    "payload": {
        "text": "The concentration reading of 0.7 suggests...",
        "rag_context": {  # NEW — optional, for UI display
            "knowledge_used": ["Concentration gradients peak within 2-3 tiles of pristine deposits"],
            "memories_used": ["Scanned area around (5,8), peak=0.742"]
        }
    }
}
```
