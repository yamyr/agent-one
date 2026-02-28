# Tasks: Mistral RAG-Enhanced Agent Intelligence

**Input**: Design documents from `/specs/003-mistral-rag-agents/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/rag-service.md
**Branch**: `003-mistral-rag-agents`

**Tests**: Included — plan.md specifies test tasks for each layer.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create RAG module scaffolding, configuration, and directory structure

- [x] T001 Add RAG configuration settings (`rag_enabled`, `rag_knowledge_top_k`, `rag_memory_top_k`, `rag_timeout_seconds`, `rag_max_context_tokens`) to `Settings` class in `server/app/config.py`
- [x] T002 [P] Create `server/data/` directory and add `.gitkeep` placeholder for generated knowledge document
- [x] T003 [P] Create `server/app/rag.py` module skeleton with imports (`mistralai`, `surrealdb`, `asyncio`, `logging`) and empty async function stubs matching the contract: `init_rag()`, `retrieve_context()`, `store_memory()`, `format_rag_context()` in `server/app/rag.py`
- [x] T004 [P] Create `server/app/rag_setup.py` CLI module skeleton with `__main__` entry point and empty subcommand stubs: `generate-knowledge`, `init-db`, `upload-library` in `server/app/rag_setup.py`

**Checkpoint**: RAG module files exist, config settings available, CLI entry point runnable (no-op)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core RAG infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Implement Mistral embedding helper function `_embed_texts(texts: list[str]) -> list[list[float]]` that calls `client.embeddings.create(model="mistral-embed", inputs=texts)` and returns 1024-dim vectors, with retry logic and timeout handling in `server/app/rag.py`
- [x] T006 Implement `_get_mistral_client()` helper that initializes and caches a `Mistral` client instance using `MISTRAL_API_KEY` from settings in `server/app/rag.py`
- [x] T007 Implement `init_knowledge_table()` that creates SurrealDB `knowledge_chunk` table (SCHEMAFULL) with fields: `source` (string), `section` (string), `content` (string), `embedding` (array<float>), `category` (string), `created_at` (datetime DEFAULT time::now()); and indexes: `idx_chunk_embedding` (HNSW DIMENSION 1024 DIST COSINE), `idx_chunk_category` (standard on `category`) in `server/app/rag.py`
- [x] T008 Implement `_build_situation_summary(agent_id: str) -> str` that reads agent state from WORLD dict (position, battery, current task, ground status, last action, recent memory) and returns a natural language situation summary for embedding in `server/app/rag.py`
- [x] T009 Wire `init_rag()` call into FastAPI `lifespan()` function after `init_db()` call, guarded by `settings.rag_enabled` flag in `server/app/main.py`
- [x] T010 Implement graceful fallback wrapper `_safe_rag_call(coro, default)` that wraps any RAG coroutine in `asyncio.wait_for()` with `rag_timeout_seconds`, catches `TimeoutError` and all exceptions, logs warning, and returns the default value in `server/app/rag.py`

**Checkpoint**: Foundation ready — Mistral embedding calls work, SurrealDB knowledge table created, fallback infrastructure in place. User story implementation can now begin.

---

## Phase 3: User Story 1 — Agents Reference Mars Knowledge During Decisions (Priority: P1) 🎯 MVP

**Goal**: Agents retrieve and reference curated Mars environment knowledge in their reasoning outputs

**Independent Test**: Run simulation, verify agent reasoning messages reference specific Mars facts from the knowledge base (e.g., "basalt veins near crater rims tend to be higher grade")

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T011 [P] [US1] Test knowledge document generation: verify `generate_knowledge()` produces markdown with all 8 required sections (terrain, geology, veins, concentration, battery, exploration, storms, procedures), each section ≤512 tokens, and that world.py constants (FUEL_CAPACITY_ROVER, MEMORY_MAX, vein grades) appear in content in `server/tests/test_rag.py`
- [x] T012 [P] [US1] Test SurrealDB knowledge schema creation: verify `init_knowledge_table()` creates `knowledge_chunk` table with correct fields and HNSW index (DIMENSION 1024, DIST COSINE), using in-memory SurrealDB from `conftest.py` in `server/tests/test_rag.py`
- [x] T013 [P] [US1] Test knowledge embedding and storage: verify `load_knowledge_chunks()` embeds all chunks via Mistral API, stores them in SurrealDB with correct fields (source, section, content, embedding, category), embedding has exactly 1024 dimensions, and is idempotent (second call doesn't duplicate) in `server/tests/test_rag.py`
- [x] T014 [P] [US1] Test knowledge retrieval: verify `retrieve_knowledge(agent_id)` returns top-3 chunks ranked by cosine similarity, each with `content`, `source`, and `distance` fields, and that results are contextually relevant to the agent's situation summary in `server/tests/test_rag.py`
- [x] T015 [P] [US1] Test graceful fallback: verify `retrieve_context()` returns `{"knowledge_chunks": [], "memory_entries": [], "query_text": ""}` when Mistral API times out, when SurrealDB is unreachable, and when `rag_enabled=False` in `server/tests/test_rag.py`
- [x] T016 [P] [US1] Test prompt injection: verify `format_rag_context()` produces string containing `== Mars Knowledge ==` header with bullet-pointed knowledge chunks, and that `_build_context()` includes this section when `rag_context` is present on the agent in `server/tests/test_rag.py`

### Implementation for User Story 1

- [x] T017 [P] [US1] Implement `generate_knowledge()` function that extracts constants from `world.py` (vein grades: low/medium/high/pristine, quantity ranges, rarity weights, battery costs per action, move distances, reveal radii, concentration formula) and combines with Mars geological flavor text (terrain descriptions, crater geology, basalt formation science, storm effects) into 8 structured sections (~512 tokens each) written to `server/data/mars_knowledge.md` in `server/app/rag_setup.py`
- [x] T018 [US1] Implement `_chunk_knowledge_document(doc_path: str) -> list[dict]` that reads `server/data/mars_knowledge.md`, splits by `##` section headers, and returns list of `{"source": "mars_knowledge", "section": "<header>", "content": "<text>", "category": "<terrain|geology|veins|concentration|battery|exploration|storms|procedures>"}` dicts in `server/app/rag.py`
- [x] T019 [US1] Implement `load_knowledge_chunks()` that calls `_chunk_knowledge_document()`, batch-embeds all chunk texts via `_embed_texts()`, and stores each chunk with its embedding in SurrealDB `knowledge_chunk` table; skip if chunks already exist (check `SELECT count() FROM knowledge_chunk GROUP ALL`) for idempotency in `server/app/rag.py`
- [x] T020 [US1] Implement `retrieve_knowledge(agent_id: str) -> list[dict]` that builds situation summary via `_build_situation_summary()`, embeds it via `_embed_texts()`, queries SurrealDB with `SELECT content, source, section, vector::distance::knn() AS distance FROM knowledge_chunk WHERE embedding <|{top_k},100|> $query_vector ORDER BY distance`, and returns top-K results (configurable via `rag_knowledge_top_k`) in `server/app/rag.py`
- [x] T021 [US1] Implement `retrieve_context(agent_id: str) -> dict` that calls `retrieve_knowledge()` (wrapped in `_safe_rag_call()`), assembles result dict `{"knowledge_chunks": [...], "memory_entries": [], "query_text": "..."}`, and stores in `WORLD["agents"][agent_id]["rag_context"]` in `server/app/rag.py`
- [x] T022 [US1] Implement `format_rag_context(rag_context: dict) -> str` that formats knowledge chunks as `== Mars Knowledge ==\n- <chunk1>\n- <chunk2>\n...` section, truncating total text to `rag_max_context_tokens` setting, and returns empty string if no chunks in `server/app/rag.py`
- [x] T023 [US1] Wire `init_rag()` to call `init_knowledge_table()` then `load_knowledge_chunks()` during app startup in `server/app/rag.py`
- [x] T024 [US1] Modify `MistralRoverReasoner._build_context()` to read `agent.get("rag_context")`, call `format_rag_context()`, and append the formatted RAG sections after the "Recent actions" section (after line ~302) in `server/app/agent.py`
- [x] T025 [P] [US1] Modify `DroneAgent._build_context()` (or equivalent drone reasoner method) to read `agent.get("rag_context")`, call `format_rag_context()`, and append the formatted RAG sections after the "Recent actions" section (after line ~560) in `server/app/agent.py`
- [x] T026 [US1] Wire `await retrieve_context(agent_id)` call into `RoverLoop.tick()` before `run_turn()` call (before line ~788), guarded by `settings.rag_enabled`, wrapped in `_safe_rag_call()` with fallback to empty context in `server/app/agent.py`
- [x] T027 [P] [US1] Wire `await retrieve_context(agent_id)` call into `DroneLoop.tick()` before `run_turn()` call (before line ~896), guarded by `settings.rag_enabled`, wrapped in `_safe_rag_call()` with fallback to empty context in `server/app/agent.py`
- [x] T028 [US1] Implement `upload_to_mistral_library(doc_path: str) -> str` that creates library via `client.beta.libraries.create(name="mars-mission-kb")`, uploads knowledge doc via `client.beta.libraries.documents.upload()`, polls `processing_status` until "Completed", and returns library UUID in `server/app/rag_setup.py`
- [x] T029 [US1] Implement `init-db` CLI subcommand that connects to SurrealDB, calls `init_knowledge_table()`, generates knowledge doc if missing, then calls `load_knowledge_chunks()` in `server/app/rag_setup.py`
- [x] T030 [US1] Implement `upload-library` CLI subcommand that calls `upload_to_mistral_library("server/data/mars_knowledge.md")` and prints the library ID in `server/app/rag_setup.py`
- [x] T031 [US1] Add `"rag_context"` key initialization to agent creation in WORLD dict (default `{}`) so `_build_context()` doesn't KeyError on first tick in `server/app/world.py`

**Checkpoint**: At this point, agents retrieve and reference Mars knowledge in their reasoning. Run simulation and verify agent thinking messages include Mars-specific facts. US1 is fully functional and testable independently.

---

## Phase 4: User Story 2 — Agents Build and Recall Mission Memory (Priority: P2)

**Goal**: Agents accumulate and recall mission experience beyond the 8-slot memory window via RAG-backed memory

**Independent Test**: Run a 25+ tick simulation, verify that at tick 20+ an agent references an observation from tick 3 that is no longer in the sliding memory window

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T032 [P] [US2] Test mission memory schema creation: verify `init_memory_table()` creates `mission_memory` table with fields (`agent_id`, `content`, `embedding`, `tick`, `position`, `action_name`, `success`, `category`, `created_at`) and indexes (`idx_memory_embedding` HNSW 1024 COSINE, `idx_memory_agent`, `idx_memory_category`, `idx_memory_tick`) in `server/tests/test_rag.py`
- [x] T033 [P] [US2] Test memory storage: verify `store_memory()` creates a record in `mission_memory` table with correct fields, embedding has 1024 dimensions, and category is correctly derived from action_name (move→exploration, analyze→discovery, dig→extraction, scan→scan, charge→charging, failed→failure) in `server/tests/test_rag.py`
- [x] T034 [P] [US2] Test memory retrieval: verify `retrieve_memories(agent_id)` returns top-3 memories ranked by cosine similarity to current situation, each with `content`, `agent_id`, `tick`, and `distance` fields in `server/tests/test_rag.py`
- [x] T035 [P] [US2] Test cross-tick recall: store memories at simulated ticks 1-5, then query at simulated tick 25 with a similar situation, verify that relevant early-tick memories are returned even though they would be outside the 8-slot window in `server/tests/test_rag.py`
- [x] T036 [P] [US2] Test memory pruning: insert 510 memory entries, call `prune_memories()`, verify only the most recent 500 remain (oldest 10 deleted) in `server/tests/test_rag.py`
- [x] T037 [P] [US2] Test async storage doesn't block tick: verify `store_memory()` runs as `asyncio.create_task()` and the tick loop completes without waiting for storage to finish in `server/tests/test_rag.py`

### Implementation for User Story 2

- [x] T038 [US2] Implement `init_memory_table()` that creates SurrealDB `mission_memory` table (SCHEMAFULL) with fields: `agent_id` (string), `content` (string), `embedding` (array<float>), `tick` (int), `position` (array<int>), `action_name` (string), `success` (bool), `category` (string), `created_at` (datetime DEFAULT time::now()); and indexes: `idx_memory_embedding` (HNSW DIMENSION 1024 DIST COSINE), `idx_memory_agent` (standard on `agent_id`), `idx_memory_category` (standard on `category`), `idx_memory_tick` (standard on `tick`) in `server/app/rag.py`
- [x] T039 [US2] Implement `_categorize_action(action_name: str, success: bool) -> str` helper that maps action names to categories: move→exploration, analyze/check→discovery, dig/pickup→extraction, scan→scan, charge/deploy_solar→charging; and overrides to `failure` when `success=False` in `server/app/rag.py`
- [x] T040 [US2] Implement `store_memory(agent_id: str, content: str, action_name: str, success: bool) -> None` that reads agent state from WORLD (tick, position), categorizes via `_categorize_action()`, embeds content via `_embed_texts()`, creates record in SurrealDB `mission_memory` table with all fields in `server/app/rag.py`
- [x] T041 [US2] Implement `retrieve_memories(agent_id: str) -> list[dict]` that builds situation summary, embeds it, queries SurrealDB with `SELECT content, agent_id, tick, vector::distance::knn() AS distance FROM mission_memory WHERE agent_id = $agent_id AND embedding <|{top_k},100|> $query_vector ORDER BY distance`, returns top-K results (configurable via `rag_memory_top_k`) in `server/app/rag.py`
- [x] T042 [US2] Extend `retrieve_context()` to call `retrieve_memories(agent_id)` (wrapped in `_safe_rag_call()`), merge results into the `"memory_entries"` field of the returned context dict in `server/app/rag.py`
- [x] T043 [US2] Extend `format_rag_context()` to format memory entries as `== Relevant Past Experience ==\n- [<agent_id>, tick <tick>] <content>\n...` section after the Mars Knowledge section, respecting `rag_max_context_tokens` total budget in `server/app/rag.py`
- [x] T044 [US2] Wire `store_memory()` call into `execute_action()` in `world.py`: after each `record_memory()` call (lines ~478-549), spawn `asyncio.create_task(store_memory(agent_id, memory_text, action_name, success))` guarded by `settings.rag_enabled` in `server/app/world.py`
- [x] T045 [US2] Update `init_rag()` to also call `init_memory_table()` during app startup in `server/app/rag.py`
- [x] T046 [US2] Implement `prune_memories(max_entries: int = 500) -> int` that counts `mission_memory` records, and if exceeding `max_entries`, deletes the oldest entries beyond the limit using `DELETE FROM mission_memory WHERE id IN (SELECT id FROM mission_memory ORDER BY created_at ASC LIMIT $excess)`, returns count of deleted entries in `server/app/rag.py`
- [x] T047 [US2] Wire `prune_memories()` to run after every 50 new `store_memory()` calls (use a module-level counter `_memory_store_count`) in `server/app/rag.py`

**Checkpoint**: Agents now accumulate mission memory and recall past experiences beyond the 8-slot window. Run a 25+ tick simulation, verify agents reference early-tick observations in later reasoning.

---

## Phase 5: User Story 3 — Cross-Agent Knowledge Sharing via Shared Memory (Priority: P3)

**Goal**: Agents access and benefit from knowledge gathered by other agents without explicit message passing

**Independent Test**: Have drone scan an area, verify rover retrieves and references drone's scan results when planning exploration

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T048 [P] [US3] Test cross-agent retrieval: store memories for both `rover-mistral` and `drone-mistral`, query as rover with `cross_agent=True`, verify drone's memories appear in results with correct attribution in `server/tests/test_rag_integration.py`
- [x] T049 [P] [US3] Test attribution formatting: verify that cross-agent memories in `format_rag_context()` output include source agent ID and tick number: `[drone-mistral, tick 12] Scanned area around (5,8)` in `server/tests/test_rag_integration.py`
- [x] T050 [P] [US3] Test mixed retrieval: verify that `retrieve_context()` with cross-agent enabled returns both own memories and other agents' memories, ranked by relevance not agent ownership in `server/tests/test_rag_integration.py`

### Implementation for User Story 3

- [x] T051 [US3] Modify `retrieve_memories()` to accept `cross_agent: bool = False` parameter; when `True`, remove the `WHERE agent_id = $agent_id` filter from the SurrealDB KNN query so all agents' memories are searched in `server/app/rag.py`
- [x] T052 [US3] Update `retrieve_context()` to call `retrieve_memories(agent_id, cross_agent=True)` by default, ensuring rover sees drone's scan results and drone sees rover's vein discoveries in `server/app/rag.py`
- [x] T053 [US3] Verify attribution formatting in `format_rag_context()` already includes `agent_id` in the `[agent_id, tick N]` prefix for memory entries — add it if missing, ensuring cross-agent memories are clearly attributed in `server/app/rag.py`

**Checkpoint**: Rover retrieves drone's scan results and vice versa. Run simulation with both agents, verify cross-agent references appear in reasoning.

---

## Phase 6: User Story 4 — Observers See Knowledge-Grounded Agent Reasoning (Priority: P4)

**Goal**: UI event log displays RAG-grounded reasoning with visible knowledge references

**Independent Test**: Observe the UI event log during simulation, verify agent reasoning messages contain contextual Mars knowledge references and the event payload includes `rag_context` metadata

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T054 [P] [US4] Test broadcast events include RAG metadata: verify thinking/action event payloads contain optional `rag_context` field with `knowledge_used` and `memories_used` lists when RAG is enabled in `server/tests/test_rag_integration.py`
- [x] T055 [P] [US4] Test broadcast events without RAG: verify thinking/action event payloads do NOT contain `rag_context` field when `rag_enabled=False` in `server/tests/test_rag_integration.py`

### Implementation for User Story 4

- [x] T056 [US4] Extend rover tick loop broadcast: after reasoning completes, add optional `rag_context` field to thinking event payload containing `{"knowledge_used": [<chunk summaries>], "memories_used": [<memory summaries>]}` extracted from `agent["rag_context"]` in `server/app/agent.py`
- [x] T057 [P] [US4] Extend drone tick loop broadcast: same as T056 but for the drone's thinking event payload in `server/app/agent.py`
- [x] T058 [US4] Update action event broadcast to include `rag_context` metadata alongside existing action payload so UI can display what knowledge informed the decision in `server/app/agent.py`

**Checkpoint**: UI event log shows knowledge-grounded reasoning. WebSocket payloads include RAG metadata for future UI rendering.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Performance validation, documentation, cleanup

- [x] T059 Validate RAG retrieval latency: measure time from `retrieve_context()` call to completion across 20 ticks, verify average adds ≤500ms to tick duration, log timing metrics in `server/app/rag.py`
- [x] T060 [P] Run full `quickstart.md` validation: execute all setup steps (generate-knowledge, init-db, upload-library, run server), verify SurrealDB tables contain expected data, agents produce RAG-grounded reasoning
- [x] T061 [P] Add system prompt instruction to both rover and drone that states "Real-time world state always takes precedence over knowledge base content. If retrieved knowledge contradicts what you observe, trust your current observations." in `server/app/agent.py`
- [x] T062 [P] Update `CHANGELOG.md` with RAG feature summary: new files, modified files, configuration options, setup instructions
- [x] T063 Code cleanup: remove unused imports, verify all RAG functions have docstrings matching the contract in `contracts/rag-service.md`, run `ruff` linter on all modified files
- [x] T064 Run full test suite: `rut tests/` — verify all existing tests still pass and all new RAG tests pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 completion — MVP delivery target
- **US2 (Phase 4)**: Depends on Phase 2 completion; extends `rag.py` from US1, so practically depends on US1
- **US3 (Phase 5)**: Depends on US2 completion (extends `retrieve_memories()`)
- **US4 (Phase 6)**: Depends on US1 completion (needs `rag_context` in WORLD to exist)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependencies on other stories
- **US2 (P2)**: Depends on Phase 2 + uses embedding/retrieval infrastructure from US1 (`_embed_texts()`, `_build_situation_summary()`, `format_rag_context()`)
- **US3 (P3)**: Depends on US2 (extends `retrieve_memories()` function)
- **US4 (P4)**: Depends on US1 (needs `rag_context` in agent dict); can run in parallel with US2/US3

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Schema/infrastructure before service logic
- Service logic before integration wiring
- Integration wiring before prompt injection
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1** (all parallelizable):
```
T001 (config) | T002 (data dir) | T003 (rag.py skeleton) | T004 (rag_setup.py skeleton)
```

**Phase 3 — US1 tests** (all parallelizable):
```
T011 | T012 | T013 | T014 | T015 | T016
```

**Phase 3 — US1 implementation**:
```
T017 (generate knowledge) ──→ T018 (chunk) ──→ T019 (embed+store)
                                                      ↓
T020 (retrieval) ──→ T021 (retrieve_context) ──→ T022 (format)
                                                      ↓
                          T024 (rover prompt) | T025 (drone prompt)  [P]
                          T026 (rover tick)   | T027 (drone tick)    [P]
                                                      ↓
                          T028 (Mistral Libraries) | T029 (init-db CLI) | T030 (upload CLI)  [P]
```

**Phase 4 — US2 tests** (all parallelizable):
```
T032 | T033 | T034 | T035 | T036 | T037
```

**Phase 5 — US3** (tests parallelizable):
```
T048 | T049 | T050  ──then──→  T051 → T052 → T053
```

**Phase 6 — US4** (tests parallelizable, then implementation):
```
T054 | T055  ──then──→  T056 | T057 [P]  ──then──→  T058
```

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests in parallel (write first, verify they fail):
T011: "Test knowledge document generation in server/tests/test_rag.py"
T012: "Test SurrealDB knowledge schema in server/tests/test_rag.py"
T013: "Test knowledge embedding and storage in server/tests/test_rag.py"
T014: "Test knowledge retrieval in server/tests/test_rag.py"
T015: "Test graceful fallback in server/tests/test_rag.py"
T016: "Test prompt injection in server/tests/test_rag.py"

# Then launch parallelizable implementation tasks:
T017: "Generate Mars knowledge document in server/app/rag_setup.py"  |
T024: "Modify rover _build_context() in server/app/agent.py"        | (different files)
T025: "Modify drone _build_context() in server/app/agent.py"        | (same file but different method)
```

## Parallel Example: User Story 2

```bash
# Launch all US2 tests in parallel:
T032-T037: All test tasks for mission memory

# Then sequential core implementation:
T038 → T039 → T040 → T041 → T042 → T043

# Then parallel wiring:
T044: "Wire store_memory into world.py"  |
T045: "Update init_rag() in rag.py"      | (different files)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T010)
3. Complete Phase 3: User Story 1 (T011-T031)
4. **STOP and VALIDATE**: Run simulation, verify agents reference Mars knowledge
5. Deploy/demo if ready — agents already feel significantly smarter

### Incremental Delivery

1. Setup + Foundational → RAG infrastructure ready
2. Add US1 (Static Knowledge) → Test independently → **Demo: "Agents know Mars geology"**
3. Add US2 (Mission Memory) → Test independently → **Demo: "Agents learn from experience"**
4. Add US3 (Cross-Agent Sharing) → Test independently → **Demo: "Agents share collective intelligence"**
5. Add US4 (UI Visibility) → Test independently → **Demo: "Observers see grounded reasoning"**
6. Each story adds value without breaking previous stories

### Agent Swarm Strategy

With multiple agents working in parallel:

1. **All agents**: Complete Setup (Phase 1) together — 4 parallel tasks
2. **All agents**: Complete Foundational (Phase 2) — sequential but fast
3. Once Foundational is done:
   - **Agent A**: US1 tests (T011-T016 in parallel) → US1 implementation (T017-T031)
   - **Agent B**: US2 tests (T032-T037 in parallel) → US2 implementation (T038-T047) [starts after US1 core rag.py functions exist]
   - **Agent C**: US4 tests (T054-T055) → waits for US1 agent.py changes → US4 implementation (T056-T058)
4. After US2 completes:
   - **Agent B** or **Agent C**: US3 (T048-T053)
5. **All agents**: Polish phase (T059-T064)

---

## Task Summary

| Phase | Tasks | Parallelizable | Story |
|-------|-------|----------------|-------|
| Phase 1: Setup | T001-T004 (4) | 3 of 4 | — |
| Phase 2: Foundational | T005-T010 (6) | 0 | — |
| Phase 3: US1 (P1) | T011-T031 (21) | 12 of 21 | US1 |
| Phase 4: US2 (P2) | T032-T047 (16) | 7 of 16 | US2 |
| Phase 5: US3 (P3) | T048-T053 (6) | 3 of 6 | US3 |
| Phase 6: US4 (P4) | T054-T058 (5) | 3 of 5 | US4 |
| Phase 7: Polish | T059-T064 (6) | 3 of 6 | — |
| **Total** | **64 tasks** | **31 parallelizable** | |

---

## Notes

- [P] tasks = different files, no dependencies — safe for parallel execution
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Tests written FIRST (TDD) — verify they fail before implementation
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- World.py constants referenced: FUEL_CAPACITY_ROVER=350, MEMORY_MAX=8, vein grades (low/medium/high/pristine)
- SurrealDB connection: ws://localhost:4002, ns=dev, db=mars
- Embedding model: `mistral-embed` (1024 dimensions, $0.01/1M tokens)
- KNN query syntax: `WHERE embedding <|K,100|> $query_vector`
