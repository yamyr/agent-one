# Implementation Plan: Mistral RAG-Enhanced Agent Intelligence

**Branch**: `003-mistral-rag-agents` | **Date**: 2026-02-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-mistral-rag-agents/spec.md`

## Summary

Integrate Mistral AI's RAG capabilities into the Mars mission simulation to give rover and drone agents deep environmental awareness. The system uses a hybrid architecture: (1) static Mars knowledge embedded and stored in SurrealDB via `mistral-embed`, also uploaded to Mistral Libraries for management, and (2) dynamic mission memory embedded and stored in SurrealDB for experiential recall. Both retrieval sources feed into the existing agent `_build_context()` prompt assembly, with zero changes to the core `chat.complete()` reasoning path.

## Technical Context

**Language/Version**: Python 3.14+
**Primary Dependencies**: `mistralai` (embeddings + libraries beta), `surrealdb` (vector storage), FastAPI (server)
**Storage**: SurrealDB (ws://localhost:4002, ns=dev, db=mars) — existing infrastructure
**Testing**: `rut` (unittest runner) with in-memory SurrealDB
**Target Platform**: Linux/macOS server (FastAPI on port 4009)
**Project Type**: Web service (FastAPI backend + Vue 3 frontend)
**Performance Goals**: RAG retrieval adds ≤500ms to agent tick latency
**Constraints**: Must not break existing agent loop; graceful fallback when RAG unavailable
**Scale/Scope**: 2 agents (rover + drone), ~50 knowledge chunks, ~500 mission memories per mission

## Constitution Check

*No constitution gates defined (template placeholder). Proceeding.*

## Project Structure

### Documentation (this feature)

```text
specs/003-mistral-rag-agents/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: technical research findings
├── data-model.md        # Phase 1: SurrealDB schema design
├── quickstart.md        # Phase 1: setup and verification guide
├── contracts/
│   └── rag-service.md   # Phase 1: RAG service interface contract
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
server/
├── app/
│   ├── rag.py               # NEW — RAG service (retrieve, store, embed, format)
│   ├── rag_setup.py          # NEW — CLI for knowledge generation, DB init, library upload
│   ├── agent.py              # MODIFIED — inject RAG context into _build_context() + tick loops
│   ├── world.py              # MODIFIED — add async memory storage after execute_action()
│   ├── config.py             # MODIFIED — add RAG settings (enabled, top_k, timeout)
│   ├── main.py               # MODIFIED — call init_rag() in lifespan
│   └── db.py                 # UNCHANGED — existing SurrealDB connection helpers
├── data/
│   └── mars_knowledge.md     # NEW — auto-generated Mars knowledge document
└── tests/
    ├── test_rag.py            # NEW — RAG service unit tests
    └── test_rag_integration.py # NEW — end-to-end RAG integration tests

ui/
└── src/
    └── (future: display RAG context in event log — deferred to Layer 4)
```

**Structure Decision**: Extends the existing `server/app/` module with a new `rag.py` service module and `rag_setup.py` CLI tool. No new directories beyond `server/data/` for the generated knowledge document.

---

## Implementation Layers

### Layer 1: Static Knowledge Base (P1 — Core Value)

**Goal**: Agents reference Mars-specific knowledge in their reasoning.

**Tasks**:

1. **Generate Mars knowledge document** (`server/data/mars_knowledge.md`)
   - Extract constants from `world.py`: vein grades, weights, quantity ranges, battery costs, move distances, reveal radii, concentration formula
   - Add Mars geological flavor text: terrain descriptions, crater geology, basalt formation science, storm effects
   - Structure into 8 sections (~512 tokens each): terrain, geology, veins, concentration, battery, exploration, storms, procedures
   - File: `server/app/rag_setup.py` — `generate_knowledge()` function

2. **Create SurrealDB schema** (`knowledge_chunk` table)
   - Define table with fields: source, section, content, embedding (array\<float\>), category, created_at
   - Define HNSW index: DIMENSION 1024, DIST COSINE
   - File: `server/app/rag.py` — `init_knowledge_table()` function

3. **Embed and store knowledge chunks**
   - Chunk the Mars knowledge document by section headers
   - Call `client.embeddings.create(model="mistral-embed", inputs=[chunk_texts])` to batch-embed
   - Store each chunk with its embedding in SurrealDB `knowledge_chunk` table
   - Skip if chunks already exist (idempotent)
   - File: `server/app/rag.py` — `load_knowledge_chunks()` function

4. **Implement knowledge retrieval**
   - Build situation summary from agent's current state (position, battery, task, ground status)
   - Embed summary via `client.embeddings.create()`
   - Query SurrealDB: `SELECT content, source, vector::distance::knn() AS distance FROM knowledge_chunk WHERE embedding <|3,100|> $query_vector ORDER BY distance`
   - Return top-3 chunks
   - File: `server/app/rag.py` — `retrieve_knowledge(agent_id)` function

5. **Inject into agent prompts**
   - In `MistralRoverReasoner._build_context()` (after line 302): read `agent.get("rag_context")`, format as `== Mars Knowledge ==` section
   - In `DroneAgent._build_context()` (after line 560): same injection
   - File: `server/app/agent.py` — modify `_build_context()` methods

6. **Wire into tick loop**
   - In `RoverLoop.tick()` (before line 788): call `await retrieve_context(agent_id)`, store in WORLD
   - In `DroneLoop.tick()` (before line 896): same
   - File: `server/app/agent.py` — modify tick methods

7. **Add RAG config settings**
   - `rag_enabled: bool = True`
   - `rag_knowledge_top_k: int = 3`
   - `rag_memory_top_k: int = 3`
   - `rag_timeout_seconds: float = 2.0`
   - `rag_max_context_tokens: int = 800`
   - File: `server/app/config.py`

8. **Initialize in app startup**
   - Call `init_rag()` in `lifespan()` after `init_db()`
   - File: `server/app/main.py`

9. **Upload to Mistral Libraries** (management layer)
   - Create library: `client.beta.libraries.create(name="mars-mission-kb")`
   - Upload knowledge doc: `client.beta.libraries.documents.upload()`
   - Poll processing status until "Completed"
   - File: `server/app/rag_setup.py` — `upload_to_library()` function

10. **Graceful fallback**
    - Wrap all RAG calls in try/except with timeout
    - On failure: log warning, set `rag_context = {}`, agent continues without RAG
    - File: `server/app/rag.py` — `retrieve_context()` error handling

11. **Tests for Layer 1**
    - Test knowledge document generation (correct sections, chunk sizes)
    - Test SurrealDB schema creation (table exists, index defined)
    - Test embedding + storage (correct dimensions, chunk count)
    - Test retrieval (returns relevant chunks for given situation)
    - Test fallback (returns empty on timeout/error)
    - Test prompt injection (RAG section appears in context string)
    - Files: `server/tests/test_rag.py`

---

### Layer 2: Dynamic Mission Memory (P2 — Experiential Recall)

**Goal**: Agents recall past observations beyond the 8-slot memory window.

**Tasks**:

12. **Create SurrealDB schema** (`mission_memory` table)
    - Define table with fields: agent_id, content, embedding, tick, position, action_name, success, category, created_at
    - Define HNSW index: DIMENSION 1024, DIST COSINE
    - Define standard indexes on agent_id, category, tick
    - File: `server/app/rag.py` — `init_memory_table()` function

13. **Implement memory storage**
    - After `execute_action()` completes: create memory text, embed via `mistral-embed`, store in SurrealDB
    - Categorize by action type: exploration (move), discovery (analyze, check), extraction (dig, pickup), failure, scan, charging
    - Run embedding + storage async (don't block the tick loop)
    - File: `server/app/rag.py` — `store_memory()` function

14. **Wire memory storage into execute_action()**
    - After each `record_memory()` call in `world.py`, also call `store_memory()` async
    - Use `asyncio.create_task()` to avoid blocking
    - File: `server/app/world.py` — modify `execute_action()`

15. **Implement memory retrieval**
    - Embed current situation summary
    - Query SurrealDB: `SELECT content, agent_id, tick, vector::distance::knn() AS distance FROM mission_memory WHERE embedding <|3,100|> $query_vector ORDER BY distance`
    - Return top-3 memories
    - File: `server/app/rag.py` — `retrieve_memories(agent_id)` function

16. **Inject into agent prompts**
    - Format retrieved memories as `== Relevant Past Experience ==` section
    - Include agent_id and tick for attribution: `[drone-mistral, tick 12] Scanned area...`
    - File: `server/app/rag.py` — `format_rag_context()` function (already handles both knowledge + memory)

17. **Memory pruning** (optional, for long missions)
    - If `mission_memory` exceeds 500 entries, delete oldest entries beyond top-500
    - Run check after every 50 new entries
    - File: `server/app/rag.py` — `prune_memories()` function

18. **Tests for Layer 2**
    - Test memory storage (correct fields, embedding dimensions)
    - Test memory retrieval (returns relevant memories for situation)
    - Test cross-tick recall (memory from tick 3 retrievable at tick 20+)
    - Test memory pruning (oldest entries removed when exceeding limit)
    - Test async storage (doesn't block tick loop)
    - Files: `server/tests/test_rag.py` (extend)

---

### Layer 3: Cross-Agent Knowledge Sharing (P3 — Collective Intelligence)

**Goal**: Agents benefit from each other's observations.

**Tasks**:

19. **Cross-agent memory retrieval**
    - When retrieving memories, query WITHOUT agent_id filter (all agents' memories)
    - Or optionally query other agents' memories specifically
    - Rover sees drone's scan results; drone sees rover's vein discoveries
    - File: `server/app/rag.py` — modify `retrieve_memories()` to accept `cross_agent=True`

20. **Attribution in prompt context**
    - Format cross-agent memories with source attribution:
      - `[drone-mistral, tick 12] Scanned area around (5,8), peak concentration=0.742`
      - `[rover-mistral, tick 8] Found high vein at (3,5), qty=250`
    - Agents can reason about what their teammates discovered

21. **Tests for Layer 3**
    - Test cross-agent retrieval (rover retrieves drone's memories)
    - Test attribution formatting (agent_id visible in context)
    - Files: `server/tests/test_rag_integration.py`

---

### Layer 4: UI Visibility (P4 — Demo Polish)

**Goal**: Observers see knowledge-grounded reasoning in the UI.

**Tasks**:

22. **Extend broadcast events with RAG metadata**
    - Add optional `rag_context` field to thinking/action event payloads
    - Include `knowledge_used` and `memories_used` lists
    - File: `server/app/agent.py` — modify broadcast in tick loops

23. **Update WebSocket event schema**
    - UI receives `rag_context` in event payloads
    - Frontend can display "Knowledge sources" panel alongside agent reasoning
    - File: `ui/src/` — future component (deferred, just pass data for now)

24. **Tests for Layer 4**
    - Test broadcast events include rag_context when RAG is enabled
    - Test events work without rag_context when RAG is disabled
    - Files: `server/tests/test_rag_integration.py` (extend)

---

## Dependency Graph

```
Layer 1 (Static Knowledge)
  ├── Task 1: Generate knowledge doc
  ├── Task 2: Create knowledge_chunk schema
  ├── Task 3: Embed + store chunks (depends on 1, 2)
  ├── Task 4: Implement retrieval (depends on 2, 3)
  ├── Task 5: Inject into prompts (depends on 4)
  ├── Task 6: Wire into tick loop (depends on 4, 5)
  ├── Task 7: Add config settings
  ├── Task 8: Init in app startup (depends on 2, 3, 7)
  ├── Task 9: Upload to Mistral Libraries (depends on 1)
  ├── Task 10: Graceful fallback (depends on 4)
  └── Task 11: Tests (depends on all above)

Layer 2 (Mission Memory) — depends on Layer 1 completion
  ├── Task 12: Create mission_memory schema
  ├── Task 13: Implement memory storage (depends on 12)
  ├── Task 14: Wire into execute_action (depends on 13)
  ├── Task 15: Implement memory retrieval (depends on 12)
  ├── Task 16: Format context (extends Layer 1 formatting)
  ├── Task 17: Memory pruning (depends on 12)
  └── Task 18: Tests (depends on all above)

Layer 3 (Cross-Agent) — depends on Layer 2 completion
  ├── Task 19: Cross-agent retrieval (extends Layer 2)
  ├── Task 20: Attribution formatting
  └── Task 21: Tests

Layer 4 (UI Visibility) — depends on Layer 1 completion
  ├── Task 22: Extend broadcast events
  ├── Task 23: WebSocket schema update
  └── Task 24: Tests
```

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Mistral embeddings API latency adds >500ms per tick | Agent responsiveness degrades | Batch embed calls; cache embeddings for unchanged situations; async storage |
| SurrealDB HNSW index memory usage grows with mission length | Memory pressure on server | Prune memories beyond 500 entries; use F32 instead of F64 for vectors |
| Mistral Libraries beta API breaks or changes | Library upload fails | Library upload is non-critical (management only); retrieval uses local SurrealDB |
| Retrieved knowledge contradicts world state | Agent confusion, bad decisions | System prompt explicitly states "real-time world state takes precedence over knowledge base" |
| RAG context dilutes prompt, making agent less focused | Worse decisions with RAG than without | Limit to 3 chunks + 3 memories, max 800 tokens; A/B test with and without RAG |

## Complexity Tracking

No constitution violations to justify. The design adds one new module (`rag.py`), one CLI tool (`rag_setup.py`), and one data file (`mars_knowledge.md`) while modifying 4 existing files minimally.
