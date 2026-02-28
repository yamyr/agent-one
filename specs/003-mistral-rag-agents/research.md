# Research: Mistral RAG-Enhanced Agent Intelligence

**Date**: 2026-02-28 | **Branch**: `003-mistral-rag-agents`

## Decision 1: Embedding Model & Dimensions

**Decision**: Use `mistral-embed` with 1024 dimensions for all embeddings (knowledge chunks + mission memory).

**Rationale**: `mistral-embed` is the general-purpose embedding model at $0.01/1M tokens — negligible cost. 1024 dimensions provide excellent semantic search quality. `codestral-embed` (1536 dims) is code-focused and unnecessary for natural language mission contexts.

**Alternatives considered**:
- `codestral-embed` (1536 dims): Overkill for mission text, higher storage per vector
- External embedding models: Unnecessary dependency when Mistral provides native embeddings

**Technical details**:
- SDK: `client.embeddings.create(model="mistral-embed", inputs=["text1", "text2"])`
- Max input: 8192 tokens per request
- Batch: Pass list of strings for multiple embeddings in one call
- Response: `response.data[i].embedding` → list of 1024 floats

## Decision 2: SurrealDB Vector Schema

**Decision**: Create `mission_memory` table with HNSW index on a 1024-dim embedding field using COSINE distance.

**Rationale**: SurrealDB v1.5+ natively supports HNSW vector indexing with cosine similarity. The project already runs SurrealDB on port 4002 — no new infrastructure needed. HNSW provides approximate nearest neighbor search that's fast enough for real-time agent ticks.

**Alternatives considered**:
- MTREE index: Deprecated in favor of HNSW in SurrealDB v2+
- Brute force (no index): Acceptable for small datasets but doesn't scale
- External vector DB (Pinecone, Qdrant): Unnecessary infrastructure for hackathon scope

**Technical details**:
```sql
DEFINE TABLE mission_memory SCHEMAFULL;
DEFINE FIELD agent_id ON mission_memory TYPE string;
DEFINE FIELD content ON mission_memory TYPE string;
DEFINE FIELD embedding ON mission_memory TYPE array<float>;
DEFINE FIELD tick ON mission_memory TYPE int;
DEFINE FIELD position ON mission_memory TYPE array<int>;
DEFINE FIELD category ON mission_memory TYPE string;
DEFINE FIELD created_at ON mission_memory TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_memory_embedding ON mission_memory
  FIELDS embedding HNSW DIMENSION 1024 DIST COSINE;
DEFINE INDEX idx_memory_agent ON mission_memory FIELDS agent_id;
DEFINE INDEX idx_memory_category ON mission_memory FIELDS category;
```

KNN query syntax:
```sql
SELECT id, agent_id, content, vector::distance::knn() AS distance
FROM mission_memory
WHERE embedding <|5,100|> $query_vector
ORDER BY distance;
```

## Decision 3: RAG Retrieval Architecture (Hybrid)

**Decision**: Use a unified SurrealDB vector store for BOTH static knowledge and dynamic mission memory. Additionally upload static knowledge to Mistral Libraries for management and future agent-based retrieval.

**Rationale**: The Mistral Libraries API has NO direct search endpoint — retrieval only works through their agents/conversations API, which would require migrating from `chat.complete()` to `conversations.start()`. This is too large an architectural change for a hackathon. Instead, we embed all knowledge chunks locally via `mistral-embed` and store in SurrealDB for fast, unified vector search. The Mistral Libraries upload serves as a management layer and enables future migration.

**Alternatives considered**:
- Full Mistral Agents API migration: Would require rewriting the reasoner layer from `chat.complete()` to `conversations.start()`. Cleaner long-term but risky for hackathon timeline.
- Separate retrieval paths for static vs dynamic: More complex, two search systems, harder to maintain.

**Integration pattern**:
```
Agent Tick:
  1. Build situation summary (position, battery, current task, what just happened)
  2. Embed summary via client.embeddings.create(model="mistral-embed")
  3. Query SurrealDB: top-K from knowledge_base table (static Mars knowledge)
  4. Query SurrealDB: top-K from mission_memory table (dynamic experience)
  5. Inject both into _build_context() as new sections
  6. Call chat.complete() as before (unchanged)

Post-Action:
  7. Create memory text from action result
  8. Embed via client.embeddings.create()
  9. Store in SurrealDB mission_memory table
```

## Decision 4: Mistral Libraries Integration

**Decision**: Upload static Mars knowledge documents to Mistral Libraries at startup for management/visibility, but perform actual retrieval via local SurrealDB vector search.

**Rationale**: Mistral Libraries provides document management (upload, versioning, deduplication) and positions us for future migration to their full agents API. But for real-time per-tick retrieval, local SurrealDB is faster (no network latency to Mistral cloud) and doesn't require architectural changes.

**Technical details**:
- Create library: `client.beta.libraries.create(name="mars-mission-kb")`
- Upload doc: `client.beta.libraries.documents.upload(library_id=..., file={"file_name": "...", "content": f})`
- Supported formats: PDF, DOCX, TXT, MD, CSV
- File limit: 100 MB per file, 100 files per library
- Processing: Async — poll `processing_status` until "Completed"

## Decision 5: Agent Injection Points

**Decision**: Insert RAG retrieval at two points in the existing agent architecture.

**Rationale**: Analysis of agent.py identified exact insertion points that require minimal code changes.

**Pre-reasoning retrieval** (async, in tick loop):
- Rover: `agent.py` line 788, before `run_turn()` call
- Drone: `agent.py` line 896, before `run_turn()` call
- Action: Embed current situation, query SurrealDB, store results in `WORLD["agents"][agent_id]["rag_context"]`

**Context assembly** (sync, in _build_context):
- Rover: `agent.py` line 302, after "Recent actions" section
- Drone: `agent.py` line 560, after "Recent actions" section
- Action: Read `agent.get("rag_context")`, format as `== Mars Knowledge ==` and `== Relevant Past Experience ==` sections

**Post-action memory storage**:
- `world.py` lines 478-549: `execute_action()` already calls `record_memory()` after each action
- Extension: Add async embedding + SurrealDB write after `record_memory()`

## Decision 6: Knowledge Document Content

**Decision**: Auto-generate a structured Mars knowledge document from `world.py` constants combined with hand-written geological flavor text. Chunk into ~512-token sections for optimal retrieval granularity.

**Rationale**: The world model code contains all authoritative facts (vein grades, battery costs, terrain rules). Auto-generating ensures knowledge base stays consistent with simulation logic. Mars flavor text adds immersion without contradicting the simulation.

**Document structure** (planned sections):
1. Mars Terrain & Geology (terrain types, crater formations, basalt distribution)
2. Vein Classification (grades: low→pristine, quantity ranges, rarity weights)
3. Concentration Gradients (how concentration maps relate to nearby vein quality)
4. Battery & Fuel Management (costs per action, return-to-base thresholds, solar panels)
5. Exploration Strategy (systematic scanning, concentration-guided navigation)
6. Storm & Hazard Protocols (storm levels, visibility impact, safe zones)
7. Mission Procedures (analyze→dig→pickup workflow, delivery to station)
8. Agent Coordination (drone scan data usage, charging schedules)
