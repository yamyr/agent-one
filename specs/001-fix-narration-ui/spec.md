# Feature Specification: Fix Narration Text Display & Voice Toggle

**Feature Branch**: `001-fix-narration-ui`
**Created**: 2026-02-28
**Status**: Draft
**Input**: User description: "check if all is implemented correctly, I can't see the narration wording and I also cannot turn on the sound, please check, I think the switch might not be correct"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See Narration Text During Simulation (Priority: P1)

As a user watching the Mars simulation, I want to see narration text appearing in the narrator bar as mission events happen, so I can follow the dramatic commentary without needing audio.

**Why this priority**: Core feature — if narration text never appears, the entire narration system is invisible to users.

**Independent Test**: Start the simulation, wait for rover to perform actions (dig, check, move). Narration text should appear in the narrator bar with a typewriter streaming effect within 5 seconds of interesting events.

**Acceptance Scenarios**:

1. **Given** the simulation is running and a rover digs a stone, **When** the narrator generates text, **Then** the narration text streams into the narrator bar character-by-character
2. **Given** the simulation is running, **When** no events have occurred yet, **Then** the narrator bar shows "Awaiting mission events..."
3. **Given** narration text is streaming, **When** a new narration batch arrives, **Then** the previous text is replaced with the full text and new streaming begins

---

### User Story 2 - Toggle Voice Narration On/Off (Priority: P1)

As a user, I want to toggle voice narration on and off using a clearly labeled button, so I can choose whether to hear audio narration or just read the text.

**Why this priority**: Equal to P1 — the toggle is completely broken, preventing users from enabling voice even if they want it.

**Independent Test**: Click the "Voice OFF" button. It should call the server, update to "Voice ON", and subsequent narrations should include audio playback. Click again to turn off.

**Acceptance Scenarios**:

1. **Given** voice is off (default), **When** I click the voice toggle button, **Then** the button changes to "Voice ON" and the server enables voice synthesis
2. **Given** voice is on, **When** I click the voice toggle button, **Then** the button changes to "Voice OFF" and the server disables voice synthesis
3. **Given** voice is on, **When** a narration event arrives with audio, **Then** the audio plays automatically
4. **Given** voice is off, **When** a narration event arrives, **Then** only text is shown, no audio plays

---

### User Story 3 - Voice Toggle State Syncs on Page Load (Priority: P2)

As a user, I want the voice toggle button to reflect the actual server state when I open or refresh the page, so I'm not confused by a mismatched UI.

**Why this priority**: Prevents user confusion but is secondary to getting text and toggle working at all.

**Independent Test**: Set voice to ON via toggle. Refresh the page. The toggle should still show "Voice ON" after reload.

**Acceptance Scenarios**:

1. **Given** the server has narration voice enabled, **When** I load the page, **Then** the toggle shows "Voice ON"
2. **Given** the server has narration voice disabled, **When** I load the page, **Then** the toggle shows "Voice OFF"

---

### Edge Cases

- What happens when the WebSocket reconnects mid-narration? Text resets to idle state (handled by existing reconnect logic clearing events).
- What happens when the toggle API call fails? Button state should not change — only update on successful server response.
- What happens when narration chunks arrive but no final narration event follows? Partial text stays visible until next narration batch.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: WebSocket handler MUST correctly route narration chunk events by matching on `event.name === 'narration_chunk'` (not `event.type`)
- **FR-002**: WebSocket handler MUST correctly route full narration events by matching on `event.name === 'narration'`
- **FR-003**: Voice toggle button MUST call the server API and update the UI to reflect the actual server response
- **FR-004**: On page load/reconnect, the UI MUST fetch the current voice status from the server and initialize the toggle accordingly
- **FR-005**: Text narration MUST always display regardless of voice toggle state

### Key Entities

- **Narration Event**: Complete narration with text and optional audio (`source: "narrator", type: "narration", name: "narration", payload: {text, audio}`)
- **Narration Chunk**: Streaming text fragment (`source: "narrator", type: "narration", name: "narration_chunk", payload: {text}`)
- **Voice Toggle State**: Boolean server-side flag controlling ElevenLabs TTS synthesis

## Root Cause Analysis

| Bug | Location                | Issue                                                                                              | Fix                                                  |
| --- | ----------------------- | -------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| #1  | useWebSocket.js:43      | Checks `event.type === 'narration_chunk'` but server sends `name: 'narration_chunk'`               | Match on `event.name === 'narration_chunk'`           |
| #2  | useWebSocket.js:41      | Full narration matched by `type` only — ambiguous with chunks that share same `type`                | Match on `event.name === 'narration'`                 |
| #3  | App.vue:14              | Hardcodes `narrationEnabled = ref(true)` but server defaults to `false`                            | Initialize to `false`, fetch from server on connect   |
| #4  | App.vue (missing)       | No startup call to `/api/narration/status`                                                         | Add fetch in `onWsConnect` callback                   |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Narration text appears in the narrator bar within 5 seconds of interesting simulation events occurring
- **SC-002**: Voice toggle correctly reflects server state after every click and on page load
- **SC-003**: All existing narrator tests continue to pass
- **SC-004**: No console errors related to narration events during normal simulation operation
