# Feature Specification: Human-in-the-Loop (UiRequest::Confirm)

**Branch**: `183-human-in-the-loop`
**Date**: 2026-03-05
**ROADMAP**: Milestone 4 — "Rover emits UiRequest::Confirm before high-risk moves"

---

## Problem Statement

The ROADMAP describes: "Rover emits UiRequest::Confirm before high-risk moves; storm arrives, rover asks human 'cross hazard zone?', human decides, agents adapt." This is the most compelling human-AI collaboration feature in the entire vision and is completely absent. Currently, rovers autonomously execute all moves including into storm zones and hazard tiles without any human oversight.

## User Stories

### US1 (P1): Rover Request Confirm Tool
**As a** rover agent, **I want to** emit a confirmation request before high-risk actions, **so that** a human operator can approve or deny dangerous moves.

**Acceptance Criteria**:
- Rover has a `request_confirm` tool that emits a `confirm_request` event
- The tool accepts a `question` (string) and `timeout` (int, seconds) parameter
- The rover's agent loop pauses until a response arrives or timeout expires
- On timeout, the action defaults to denied

### US2 (P1): Backend Pause & Resume
**As a** system, **I want to** pause the requesting agent's loop until confirmation arrives, **so that** the rover doesn't proceed with the risky action before human decision.

**Acceptance Criteria**:
- Agent loop blocks on a confirmation request (asyncio Event or similar)
- A `/api/confirm` POST endpoint accepts `{request_id, confirmed: bool}`
- The response is routed back to the agent as a `confirm_response` command
- Timeout handling gracefully resumes the agent with a denial

### US3 (P2): Frontend Confirmation Modal
**As a** human operator, **I want to** see a modal overlay when the rover requests confirmation, **so that** I can make an informed decision about high-risk actions.

**Acceptance Criteria**:
- A modal/overlay appears in SimulationPage.vue with the rover's question
- Confirm and Deny buttons are clearly visible
- The modal shows context: which agent, what action, current conditions
- The modal auto-dismisses on timeout with a visual countdown
- Response is sent via POST to `/api/confirm`

### US4 (P3): Rover Prompt Integration
**As a** rover agent, **I want** my system prompt to guide me on when to request confirmation, **so that** I use the tool appropriately for high-risk situations.

**Acceptance Criteria**:
- Rover system prompt includes guidance on using `request_confirm`
- Recommended triggers: entering storm zones, crossing hazard tiles, low battery moves
- The prompt discourages overuse (not every move needs confirmation)

## Scope

### In Scope
- `request_confirm` rover tool definition and execution
- Backend pause/resume mechanism with asyncio
- `confirm_request` WebSocket event (rover -> UI)
- `confirm_response` command routing (UI -> rover)
- `/api/confirm` REST endpoint
- Frontend confirmation modal component
- Rover system prompt update
- Timeout handling with configurable default

### Out of Scope
- Station or drone confirmation requests (rover only for now)
- Confirmation history/audit log
- Customizable timeout per-request-type
- Multi-agent confirmation (only one pending at a time)

## Files Affected
- `server/app/agent.py` — rover tool, pause/resume logic
- `server/app/world.py` — confirmation state tracking
- `server/app/host.py` — routing confirm responses
- `server/app/main.py` or `server/app/views.py` — `/api/confirm` endpoint
- `ui/src/components/ConfirmModal.vue` — new confirmation modal
- `ui/src/views/SimulationPage.vue` — modal integration
