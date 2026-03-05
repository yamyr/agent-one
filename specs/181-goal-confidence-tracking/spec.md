# Feature Specification: Goal Confidence Tracking + UI Bars

**Feature Branch**: `181-goal-confidence-tracking`
**Created**: 2026-03-05
**Status**: Draft
**Input**: User description: "Add goal_confidence (float 0.0-1.0) to agent state, update after actions, expose in observations and snapshots, include in LLM context, add confidence bars to UI, include in training data"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Confidence Reflects Agent Progress (Priority: P1)

As a simulation observer, I want each agent's confidence in its current goal to update dynamically based on action outcomes, so that I can see whether agents are making meaningful progress toward their missions.

When an agent successfully completes an action relevant to its mission (e.g., drilling rock, delivering samples, analyzing terrain), its goal confidence increases. When an action fails, the agent encounters a hazard, or the agent falls back to a default behavior, its confidence decreases. This creates a real-time feedback signal that mirrors how well the agent is performing.

**Why this priority**: This is the foundational mechanic. Without confidence values being tracked and updated in the world model, no other part of the feature (UI, LLM reasoning, training data) can function.

**Independent Test**: Can be fully tested by running the simulation headless and verifying that agent confidence values change predictably in response to action success/failure events.

**Acceptance Scenarios**:

1. **Given** a rover is assigned a mission with initial confidence of 0.5, **When** the rover successfully drills a rock, **Then** its goal_confidence increases (remains clamped to 0.0–1.0).
2. **Given** a rover has confidence of 0.7, **When** the rover's action fails (e.g., move blocked by obstacle), **Then** its goal_confidence decreases.
3. **Given** a rover has confidence of 0.6, **When** a storm event occurs affecting the rover, **Then** its goal_confidence decreases reflecting the external hazard.
4. **Given** a rover has no assigned mission, **When** the simulation ticks, **Then** goal_confidence remains at its default value and is not updated.

---

### User Story 2 - Confidence Visible in UI (Priority: P2)

As a simulation observer watching the dashboard, I want to see a color-coded confidence bar for each agent alongside its existing status indicators (battery, position), so that I can quickly gauge which agents are confident in their current approach and which may be struggling.

The confidence bar displays the current goal_confidence value as a horizontal bar with color coding: green (0.7–1.0), amber (0.4–0.69), red (0.0–0.39). The bar animates smoothly when values change.

**Why this priority**: The visual display is the primary way observers interact with confidence data during a live demo. It transforms raw numbers into an intuitive, at-a-glance signal.

**Independent Test**: Can be tested by providing mock agent state with varying confidence levels and verifying the UI renders the correct bar color and percentage.

**Acceptance Scenarios**:

1. **Given** an agent has goal_confidence of 0.85, **When** the AgentPane renders, **Then** a green confidence bar is displayed showing "85%".
2. **Given** an agent's confidence changes from 0.75 to 0.45, **When** the UI receives the updated snapshot, **Then** the bar transitions smoothly from green to amber.
3. **Given** an agent has goal_confidence of 0.2, **When** the AgentPane renders, **Then** a red confidence bar is displayed showing "20%".
4. **Given** an agent has no assigned mission, **When** the AgentPane renders, **Then** the confidence bar is hidden or displays a neutral "no mission" state.

---

### User Story 3 - LLM Agents Reason About Confidence (Priority: P3)

As the simulation system, I want each agent's current goal_confidence to be included in the observation context passed to the LLM reasoning step, so that agents can factor their own confidence level into decisions (e.g., an agent with low confidence might request help or change strategy).

**Why this priority**: This closes the reasoning loop — agents don't just have confidence tracked externally, they can introspect on it. However, LLM behavior changes are emergent and less predictable, making this lower priority than deterministic tracking and display.

**Independent Test**: Can be tested by inspecting the prompt/context object sent to the LLM and verifying goal_confidence is present and accurate.

**Acceptance Scenarios**:

1. **Given** a rover has goal_confidence of 0.3, **When** the observe_rover() function builds the agent context, **Then** goal_confidence is included in the returned context object.
2. **Given** a hauler has goal_confidence of 0.9, **When** the observe_hauler() function builds the agent context, **Then** goal_confidence is included in the returned context object.
3. **Given** confidence is included in context, **When** the LLM generates a reasoning step, **Then** the confidence value is available in the prompt for the model to reference.

---

### User Story 4 - Confidence in Training Data (Priority: P4)

As a researcher analyzing simulation runs, I want goal_confidence captured before and after each action in the training data export, so that I can correlate confidence dynamics with agent decision quality during post-hoc analysis.

**Why this priority**: Training data enrichment is valuable for offline analysis but does not affect the live simulation experience.

**Independent Test**: Can be tested by running a simulation turn and verifying the exported training record contains goal_confidence_before and goal_confidence_after fields.

**Acceptance Scenarios**:

1. **Given** a rover takes an action during a simulation turn, **When** the training data record is generated, **Then** it includes goal_confidence_before (pre-action) and goal_confidence_after (post-action) fields.
2. **Given** the world snapshot is captured for a training turn, **When** the snapshot is serialized, **Then** it includes the agent's current goal_confidence value.

---

### Edge Cases

- What happens when confidence would exceed 1.0 after a success? It must be clamped to 1.0.
- What happens when confidence would drop below 0.0 after a failure? It must be clamped to 0.0.
- What happens when a mission is reassigned mid-simulation? Confidence resets to 0.5 for the new mission.
- What happens when an agent has no active mission? Confidence is not updated; it retains its last value or remains at the default.
- What happens during rapid successive events (e.g., storm + action failure in same tick)? Each modifier applies sequentially; final value is clamped.
- How does the station agent's confidence work? Station confidence follows the same pattern — increases on successful charge/alert operations, decreases on failures.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST maintain a `goal_confidence` value (float, 0.0–1.0) for every agent (rover, hauler, station) in the world state.
- **FR-002**: System MUST initialize `goal_confidence` to 0.5 when a mission is assigned to an agent.
- **FR-003**: System MUST increase `goal_confidence` when an agent's action succeeds (e.g., dig, deliver, analyze, charge).
- **FR-004**: System MUST decrease `goal_confidence` when an agent's action fails, the agent takes a fallback action, or a hazard event (storm, terrain shift) affects the agent.
- **FR-005**: System MUST clamp `goal_confidence` to the range [0.0, 1.0] after every update.
- **FR-006**: System MUST include `goal_confidence` in the observation context provided to each agent's LLM reasoning step (observe_rover, observe_hauler, observe_station).
- **FR-007**: System MUST include `goal_confidence` per agent in the world snapshot broadcast to the UI.
- **FR-008**: The UI MUST display a confidence bar for each agent, color-coded: green (0.7–1.0), amber (0.4–0.69), red (0.0–0.39).
- **FR-009**: The UI confidence bar MUST animate smoothly when the value changes.
- **FR-010**: System MUST include `goal_confidence` in the TurnWorldSnapshot training data structure.
- **FR-011**: System MUST record `goal_confidence_before` and `goal_confidence_after` in each TrainingTurn record.
- **FR-012**: System MUST reset `goal_confidence` to 0.5 when an agent receives a new mission assignment.
- **FR-013**: System MUST include `goal_confidence` in the RoverSummary provided to the station agent, so the station can factor rover confidence into its decisions.

### Key Entities

- **Goal Confidence**: A float value (0.0–1.0) representing an agent's estimated likelihood of completing its current mission. Initialized at 0.5 on mission assignment. Updated incrementally after each action or event. Associated with a single agent and its active mission.
- **Confidence Update**: A discrete change to an agent's goal_confidence, triggered by an action result (success/failure), a fallback turn, or a hazard event. Each update has a direction (increase/decrease) and a magnitude.

### Assumptions

- Confidence update magnitudes will use fixed increments (e.g., +0.05 for success, -0.05 for failure, -0.08 for hazard). These values can be tuned later without changing the architecture.
- There is no time-based confidence decay — confidence only changes in response to discrete events (actions, hazards). This keeps the system deterministic and easier to test.
- Confidence is tracked per-agent, not per-sub-goal. Each agent has a single `goal_confidence` value tied to their overall active mission.
- The UI confidence bar will be placed alongside the existing battery bar in the AgentPane component.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every agent in the simulation has a visible, updating confidence value within 1 second of each action completion.
- **SC-002**: 100% of action successes result in a confidence increase, and 100% of action failures or hazard events result in a confidence decrease.
- **SC-003**: The UI confidence bar correctly reflects the agent's current confidence with color coding matching the defined thresholds (green/amber/red) in all simulation states.
- **SC-004**: Goal confidence data is present in 100% of training data records exported from the simulation.
- **SC-005**: Observers can distinguish high-performing agents from struggling agents at a glance within 2 seconds of viewing the dashboard.
- **SC-006**: All confidence values remain within the valid range [0.0, 1.0] throughout the entire simulation, regardless of event sequences.
