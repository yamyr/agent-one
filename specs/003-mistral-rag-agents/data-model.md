# Data Model: Mistral RAG-Enhanced Agent Intelligence

**Date**: 2026-02-28 | **Branch**: `003-mistral-rag-agents`

## Entity: Knowledge Chunk (SurrealDB table: `knowledge_chunk`)

Stores chunked static Mars knowledge with embedding vectors for retrieval.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | record ID | auto | SurrealDB record ID |
| `source` | string | yes | Source document name (e.g., "mars_geology", "vein_classification") |
| `section` | string | yes | Section title within the source document |
| `content` | string | yes | Chunk text content (~512 tokens max) |
| `embedding` | array\<float\> | yes | 1024-dim vector from `mistral-embed` |
| `category` | string | yes | One of: terrain, geology, battery, exploration, storms, procedures, coordination |
| `created_at` | datetime | auto | Timestamp of creation |

**Indexes**:
- `idx_chunk_embedding`: HNSW on `embedding` (DIMENSION 1024, DIST COSINE)
- `idx_chunk_category`: Standard on `category`

**Lifecycle**: Created once at startup from generated Mars knowledge document. Updated when knowledge document changes. Never deleted during a mission.

---

## Entity: Mission Memory (SurrealDB table: `mission_memory`)

Stores agent observations and decisions with embedding vectors for experiential recall.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | record ID | auto | SurrealDB record ID |
| `agent_id` | string | yes | Agent identifier (e.g., "rover-mistral", "drone-mistral") |
| `content` | string | yes | Memory text (same format as current `record_memory()` strings) |
| `embedding` | array\<float\> | yes | 1024-dim vector from `mistral-embed` |
| `tick` | int | yes | World tick when memory was recorded |
| `position` | array\<int\> | yes | Agent position [x, y] at time of memory |
| `action_name` | string | yes | Action that triggered this memory (move, analyze, dig, pickup, scan) |
| `success` | bool | yes | Whether the action succeeded |
| `category` | string | yes | One of: exploration, discovery, extraction, failure, scan, charging |
| `created_at` | datetime | auto | Timestamp of creation |

**Indexes**:
- `idx_memory_embedding`: HNSW on `embedding` (DIMENSION 1024, DIST COSINE)
- `idx_memory_agent`: Standard on `agent_id`
- `idx_memory_category`: Standard on `category`
- `idx_memory_tick`: Standard on `tick`

**Lifecycle**: Created after each agent action in `execute_action()`. Grows throughout a mission. Optionally pruned when exceeding a configurable max (e.g., 500 entries).

---

## Entity: RAG Context (in-memory, WORLD dict)

Transient context injected into agent prompts. Not persisted to SurrealDB.

| Field | Type | Description |
|-------|------|-------------|
| `knowledge_chunks` | list\<dict\> | Top-K retrieved knowledge chunks with content + distance |
| `memory_entries` | list\<dict\> | Top-K retrieved mission memories with content + agent_id + distance |
| `query_text` | string | The situation summary used for retrieval |
| `retrieved_at` | float | Timestamp of retrieval (for staleness check) |

**Storage**: `WORLD["agents"][agent_id]["rag_context"]`

**Lifecycle**: Overwritten on every tick. Never persisted.

---

## Entity: Library Reference (in-memory, settings/config)

Reference to the Mistral-hosted library for document management.

| Field | Type | Description |
|-------|------|-------------|
| `library_id` | string | Mistral library UUID |
| `library_name` | string | Library name (e.g., "mars-mission-kb") |
| `document_ids` | list\<string\> | Uploaded document UUIDs |

**Storage**: Stored in `app/config.py` settings or environment variable after initial creation.

**Lifecycle**: Created once. Library ID persisted across restarts via config.

---

## Relationships

```
knowledge_chunk  ──retrieves──>  rag_context.knowledge_chunks
mission_memory   ──retrieves──>  rag_context.memory_entries
rag_context      ──injected──>   agent._build_context() prompt
execute_action() ──creates──>    mission_memory (after each action)
```

## State Transitions

### Mission Memory Entry
```
[Action executed] → [record_memory() called] → [Embed text] → [Store in SurrealDB] → [Available for retrieval]
```

### Knowledge Chunk
```
[Generate document] → [Chunk into sections] → [Embed all chunks] → [Store in SurrealDB] → [Available for retrieval]
[Upload to Mistral Libraries] → [Processing...] → [Completed] → [Available for Mistral agent queries]
```

### RAG Context (per tick)
```
[Build situation summary] → [Embed summary] → [Query SurrealDB] → [Format results] → [Inject into prompt] → [Discarded next tick]
```
