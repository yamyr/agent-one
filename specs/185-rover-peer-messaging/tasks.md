# Tasks: Rover Peer-to-Peer Messaging

**Input**: Design documents from `/specs/185-rover-peer-messaging/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Included (feature requires validation of tool execution, message delivery, and prompt).

**Organization**: Tasks grouped by user story (US1: Tool, US2: Prompt, US3: UI).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Foundational)

**Purpose**: No setup needed — all infrastructure exists. Proceed directly to US1.

---

## Phase 2: User Story 1 — notify_peer Tool (Priority: P1)

**Goal**: Rovers can send direct messages to other rovers via `notify_peer(target_id, message)`

**Independent Test**: `cd server && uv run pytest tests/ -v -k "notify_peer"`

### Tests for User Story 1

- [X] T001 [P] [US1] Write test `test_notify_peer_tool_schema` — verify NOTIFY_PEER_TOOL has correct name, params (target_id, message), and is in ROVER_TOOLS, in `server/tests/test_peer_messaging.py`
- [X] T002 [P] [US1] Write test `test_execute_notify_peer_success` — call `execute_action(agent_id, "notify_peer", {target_id, message})`, verify battery deducted and `send_agent_message()` called, in `server/tests/test_peer_messaging.py`
- [X] T003 [P] [US1] Write test `test_notify_peer_message_delivered` — after notify_peer, verify `get_unread_messages(target_id)` returns the message, in `server/tests/test_peer_messaging.py`
- [X] T004 [P] [US1] Write test `test_notify_peer_validates_target` — verify errors for: self-targeting, non-existent target, station target, drone target, empty message, low battery, in `server/tests/test_peer_messaging.py`

### Implementation for User Story 1

- [X] T005 [US1] Add `NOTIFY_PEER_TOOL` definition to `server/app/agent.py` (after NOTIFY_TOOL) and append to ROVER_TOOLS list
- [X] T006 [US1] Add `_execute_notify_peer(agent_id, agent, params)` to `server/app/world.py` with validation and `send_agent_message()` call
- [X] T007 [US1] Add `elif name == "notify_peer"` dispatch in `execute_action()` in `server/app/world.py`
- [X] T008 [US1] Add tick handler for `notify_peer` in `RoverLoop.tick()` in `server/app/agent.py` — broadcast `peer_message` event, save to sender memory

**Checkpoint**: Rovers can send peer messages; messages delivered to target inbox; tests pass

---

## Phase 3: User Story 2 — Prompt Peer Coordination (Priority: P1)

**Goal**: Rover system prompt encourages peer coordination and lists available peer IDs

**Independent Test**: `cd server && uv run pytest tests/ -v -k "peer_prompt"`

### Tests for User Story 2

- [X] T009 [US2] Write test `test_peer_communication_in_prompt` — verify rover `_build_context()` includes "PEER COMMUNICATION" section with other rover IDs, in `server/tests/test_peer_messaging.py`

### Implementation for User Story 2

- [X] T010 [US2] Add PEER COMMUNICATION section to `_build_context()` in `server/app/agent.py` — list peer rover IDs, explain notify_peer usage, suggest coordination scenarios

**Checkpoint**: Prompt includes peer rover IDs and coordination guidance; test passes

---

## Phase 4: User Story 3 — UI Communication Lines (Priority: P2)

**Goal**: Purple/magenta lines appear between rovers on the map when peer messages are sent

**Independent Test**: Visual verification at http://localhost:4089

### Implementation for User Story 3

- [X] T011 [US3] Add `peer: '#cc44cc'` to `COMM_COLORS` in `ui/src/components/WorldMap.vue`
- [X] T012 [US3] Add `peer_message` event handler in the event watcher in `ui/src/components/WorldMap.vue` — `addCommLine(ev.source, ev.payload?.target, 'peer')`

**Checkpoint**: Magenta communication lines appear between rovers on peer message events

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T013 Run full test suite: `cd server && uv run pytest tests/ -v`
- [X] T014 Run ruff format and lint: `cd server && uv run ruff format app/ tests/ && uv run ruff check --fix app/ tests/`
- [X] T015 Update `Changelog.md` with feature entries

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 2 (US1)**: No dependencies — core tool implementation
- **Phase 3 (US2)**: Can run in parallel with US1 (different code sections in agent.py)
- **Phase 4 (US3)**: Independent (different file: WorldMap.vue)
- **Phase 5 (Polish)**: Depends on all user stories complete

### Parallel Opportunities

- T001-T004: All test stubs can run in parallel
- T005 + T010: Both in agent.py but different sections (tool def vs prompt) — sequential
- T006 + T007: Both in world.py, sequential (T007 depends on T006)
- T011 + T012: Both in WorldMap.vue, sequential
- US1 (server) and US3 (UI) can run fully in parallel

### Parallel Swarm Strategy

```
Agent 1 (server/app/world.py):    T006, T007
Agent 2 (server/app/agent.py):    T005, T008, T010
Agent 3 (ui WorldMap.vue):        T011, T012
Agent 4 (tests):                  T001, T002, T003, T004, T009
```

---

## Implementation Strategy

### MVP First (US1)

1. T001-T004: Write tests (parallel)
2. T005-T008: Implement tool + handler + dispatch + tick (sequential)
3. **VALIDATE**: Run tests

### Complete Delivery

4. T009-T010: Prompt update
5. T011-T012: UI visualization
6. T013-T015: Full tests, lint, changelog

---

## Notes

- Leverages existing infrastructure: `send_agent_message()`, `get_unread_messages()`, `addCommLine()`
- No new data structures needed — reuses AGENT_MESSAGES global list
- Battery cost reuses BATTERY_COST_NOTIFY constant
- Total: 15 tasks, 5 parallelizable test tasks + 4-agent swarm execution
