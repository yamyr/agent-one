# Feature Specification: Mistral RAG-Enhanced Agent Intelligence

**Feature Branch**: `003-mistral-rag-agents`
**Created**: 2026-02-28
**Status**: Draft
**Input**: User description: "Explore how we can use the Mistral AI API libraries (RAG endpoints) to improve agents and make them feel like they understand their Mars environment deeply."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agents Reference Mars Knowledge During Decisions (Priority: P1)

When an agent encounters a new situation (e.g., an unknown vein type, a terrain feature, or a storm event), it retrieves relevant knowledge from a curated Mars environment knowledge base before making its decision. The agent's reasoning output references specific environmental facts (geology, terrain hazards, resource properties) rather than generic or hallucinated information.

**Why this priority**: This is the core value proposition — agents that *understand* their environment produce more believable, contextually appropriate decisions. Without grounded knowledge, agents make generic choices that feel robotic rather than expert.

**Independent Test**: Can be fully tested by running a simulation and verifying that agent reasoning messages reference specific Mars geology/terrain facts from the knowledge base (e.g., "basalt veins near crater rims tend to be higher grade" or "storm level 3 reduces visibility, making scanning less reliable").

**Acceptance Scenarios**:

1. **Given** a rover encounters an unknown vein, **When** the rover reasons about whether to analyze it, **Then** the rover's reasoning includes retrieved context about vein types, grades, and expected quantities from the knowledge base.
2. **Given** a drone is deciding where to scan next, **When** the drone plans its route, **Then** the drone references terrain knowledge (e.g., "crater floors have higher basalt concentration") to prioritize scan targets.
3. **Given** a storm event is broadcast to agents, **When** agents receive the event, **Then** they reference storm-related knowledge (visibility impact, battery drain risks, safe zones) in their reasoning.

---

### User Story 2 - Agents Build and Recall Mission Memory (Priority: P2)

Agents accumulate contextual knowledge during a mission — past observations, successful strategies, and environmental patterns discovered — and can recall this accumulated experience when making future decisions. This goes beyond the current 8-slot memory buffer to provide deeper, queryable recall of the full mission history.

**Why this priority**: Current agents have a shallow 8-entry memory window. RAG-backed memory lets agents recall earlier discoveries, past mistakes, and successful patterns, creating the illusion of a learning, adapting entity rather than a memoryless agent that repeats errors.

**Independent Test**: Can be fully tested by running a multi-turn simulation and verifying that an agent in turn 20+ correctly recalls and references observations from turn 3 that are no longer in the sliding memory window.

**Acceptance Scenarios**:

1. **Given** a rover analyzed a low-grade vein 15 turns ago (beyond the memory window), **When** the rover encounters a similar vein, **Then** it retrieves the earlier experience and adjusts its strategy accordingly (e.g., "last time I found low-grade veins in this region, so I should explore further east").
2. **Given** a drone discovered a high-concentration area 10 turns ago, **When** the rover is deciding where to explore, **Then** the system retrieves the drone's earlier scan data and presents it as relevant context.
3. **Given** an agent made an unsuccessful attempt (e.g., dig failed, battery ran out mid-return), **When** a similar situation arises, **Then** the agent recalls the prior failure and avoids repeating it.

---

### User Story 3 - Cross-Agent Knowledge Sharing via Shared Memory (Priority: P3)

Agents can access and benefit from knowledge gathered by other agents. When one agent discovers something relevant (e.g., drone finds a rich vein cluster), that knowledge becomes retrievable by other agents (e.g., rover queries for nearby high-value targets) without requiring explicit message passing for every piece of information.

**Why this priority**: Multi-agent coordination currently relies on direct message routing through the coordinator. RAG-backed shared memory allows passive knowledge sharing — agents naturally benefit from the team's collective intelligence without requiring explicit communication overhead.

**Independent Test**: Can be fully tested by having the drone scan an area, then verifying that the rover (without receiving a direct message) can retrieve and reference the drone's scan results when planning its exploration route.

**Acceptance Scenarios**:

1. **Given** the drone has scanned and found high concentration at coordinates (5, 8), **When** the rover queries for exploration targets, **Then** the rover receives the drone's scan data as relevant context and prioritizes moving toward (5, 8).
2. **Given** the station has recorded multiple charging events showing the rover returns with low battery from the east quadrant, **When** the rover plans a new eastern exploration, **Then** it retrieves historical charging patterns and plans a shorter route or deploys solar panels preemptively.

---

### User Story 4 - Observers See Knowledge-Grounded Agent Reasoning (Priority: P4)

Users watching the simulation in the UI can see that agent decisions are grounded in specific knowledge. The agent's reasoning text (displayed in the event log) includes references to retrieved knowledge, making the simulation feel more immersive and educational.

**Why this priority**: The simulation is a demo/showcase. Visible knowledge-grounded reasoning makes the experience dramatically more engaging — observers can see agents "thinking" with domain expertise rather than making opaque decisions.

**Independent Test**: Can be fully tested by observing the UI event log during a simulation and verifying that agent reasoning messages contain specific, contextual references rather than generic decision text.

**Acceptance Scenarios**:

1. **Given** the simulation is running and displayed in the UI, **When** an agent makes a decision, **Then** the event log shows the agent's reasoning with specific environmental references (e.g., "Concentration reading 0.7 suggests proximity to a high-grade vein — Mars geological surveys indicate basalt concentration gradients peak within 2-3 tiles of pristine deposits").
2. **Given** a user is observing the narrator output, **When** the narrator describes an agent's action, **Then** the narration includes contextual knowledge that makes the action feel intentional and expert-driven.

---

### Edge Cases

- What happens when the knowledge base is unavailable or slow to respond? Agents must fall back to their current behavior (direct LLM reasoning without RAG context) and continue operating without interruption.
- What happens when retrieved knowledge contradicts the current world state? The agent's system prompt must clarify that real-time world state always takes precedence over static knowledge base content.
- How does the system handle knowledge base size limits? The knowledge base must stay within manageable bounds — old mission memories should be summarized or pruned to prevent unbounded growth.
- What happens when multiple agents query the knowledge base simultaneously? The system must handle concurrent queries without blocking agent decision loops or introducing unacceptable latency.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST maintain a Mars environment knowledge base containing curated information about terrain types, geological properties, vein characteristics, storm effects, battery management strategies, and exploration best practices.
- **FR-002**: System MUST retrieve relevant knowledge context before each agent's LLM reasoning call and inject it into the agent's prompt alongside the existing world state context.
- **FR-003**: System MUST store agent observations and decisions as searchable entries that can be retrieved in future reasoning cycles, extending beyond the current 8-entry sliding memory window.
- **FR-004**: System MUST support cross-agent knowledge retrieval — observations stored by one agent must be retrievable by other agents when contextually relevant.
- **FR-005**: System MUST fall back gracefully to non-RAG reasoning if the knowledge retrieval service is unavailable, slow (exceeding a configurable timeout), or returns no results.
- **FR-006**: System MUST limit the amount of retrieved context injected into prompts to avoid exceeding model context windows or diluting decision quality.
- **FR-007**: System MUST support configuring the knowledge base content (adding, updating, removing documents) without requiring code changes or server restarts.
- **FR-008**: System MUST ensure that knowledge retrieval does not significantly delay the agent decision loop — the overall tick duration must remain within acceptable bounds.

### Key Entities

- **Knowledge Base**: A collection of curated documents about the Mars environment, mission protocols, geological survey data, and operational best practices. Used as the static knowledge source for RAG retrieval.
- **Mission Memory Entry**: A structured record of an agent observation, decision, or outcome during the simulation. Includes the agent ID, timestamp, context (position, battery, situation), action taken, result, and an embedding vector of the situation description. Stored in SurrealDB with a vector index for cosine similarity retrieval. Used as the dynamic knowledge source for experiential recall.
- **Retrieved Context**: A set of relevant text passages extracted from the knowledge base and/or mission memory, ranked by relevance to the agent's current situation. Injected into the agent's prompt as supplementary context.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Agents reference specific environmental knowledge in at least 60% of their reasoning outputs (vs. 0% baseline without RAG).
- **SC-002**: Agents recall mission history beyond the current 8-entry memory window in at least 40% of situations where prior experience is relevant.
- **SC-003**: Agent decision loop latency increases by no more than 500ms on average when RAG is enabled compared to the non-RAG baseline.
- **SC-004**: The system operates without interruption when the knowledge retrieval service is temporarily unavailable (graceful degradation within 2 seconds).
- **SC-005**: Observers rate agent reasoning as "more intelligent and contextually aware" compared to baseline agents in qualitative assessments.

## Clarifications

### Session 2026-02-28

- Q: RAG architecture approach — hosted, local, or hybrid? → A: Hybrid — Mistral hosted Libraries API for static Mars knowledge (terrain, geology, protocols), local store for dynamic mission memory (agent observations, decisions, outcomes).
- Q: Agent scope for initial implementation? → A: Start with rover and drone only. Station agent deferred to a later layer.
- Q: Mission memory storage backend? → A: Use the existing SurrealDB database (port 4002, ns=dev, db=mars) already connected to the project. Provides persistence, queryability, and reuses existing infrastructure.
- Q: Static knowledge base content source? → A: Auto-generated from world model code constants (vein grades, battery costs, terrain rules from world.py) combined with hand-written Mars geological flavor text for immersion.
- Q: Mission memory retrieval strategy? → A: Embedding similarity — embed agent's current situation via Mistral embeddings endpoint, store vectors in SurrealDB, query via cosine similarity (SurrealDB native `vector::similarity::cosine()` + HNSW index).

## Assumptions

- The Mistral AI API's libraries/RAG endpoints (beta) are available and stable enough for production use in a hackathon demo context.
- The `mistralai` Python SDK supports the libraries/RAG beta endpoints. If not, direct HTTP API calls will be used.
- The knowledge base documents will be auto-generated from world model code constants (vein grades, concentration formulas, battery costs, terrain rules) combined with hand-written Mars geological flavor text, then uploaded to Mistral's hosted Libraries API.
- Mission memory entries will be stored in the existing SurrealDB database (port 4002, ns=dev, db=mars) with embedding vectors generated via Mistral's embeddings endpoint. Retrieval uses cosine similarity search via SurrealDB's native vector functions and HNSW indexing.
- The current agent decision loop (observe → reason → act) architecture remains unchanged — RAG retrieval is added as an enrichment step within the existing flow.
- Initial implementation targets the rover and drone agents only. Station agent RAG integration is deferred to a later phase.
- The hybrid approach uses two retrieval sources: (1) Mistral hosted Libraries for static Mars domain knowledge, (2) SurrealDB for dynamic mission memory accumulated during simulation.
