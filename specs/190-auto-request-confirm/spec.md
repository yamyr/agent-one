# Feature Specification: Automatic Request Confirm

**Feature Branch**: `190-auto-request-confirm`
**Created**: 2026-03-06
**Status**: Draft
**Input**: User description: "Automatic request_confirm: Make agents automatically trigger confirmation requests when entering hazard zones or making low-battery moves, independent of LLM decision."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Auto-Confirm on Hazardous Move (Priority: P1)

A mission operator is watching the simulation. An agent is about to move into a tile with an erupting or warning-phase geyser. Instead of relying on the LLM to request confirmation, the system automatically pauses the move and presents a confirmation dialog asking whether the agent should proceed into the dangerous zone.

**Why this priority**: This is the core safety mechanism. Geyser hazards cause direct battery damage, and preventing unintended agent loss is the primary goal of this feature.

**Independent Test**: Can be fully tested by setting up a world with a geyser in warning/erupting state at a destination tile, issuing a move action, and verifying a confirmation prompt appears in the UI before execution.

**Acceptance Scenarios**:

1. **Given** an agent is adjacent to an erupting geyser tile, **When** the agent issues a move action toward that tile, **Then** the system creates a confirmation request and waits for the operator to approve or deny before executing the move.
2. **Given** an agent is adjacent to a warning-phase geyser tile, **When** the agent issues a move toward that tile, **Then** the system creates a confirmation request describing the geyser warning at the destination.
3. **Given** a confirmation request is created for a hazardous move, **When** the operator confirms the action, **Then** the move executes normally and the agent enters the tile.
4. **Given** a confirmation request is created for a hazardous move, **When** the operator denies the action, **Then** the move is skipped and the agent receives an error response indicating the move was denied by the operator.

---

### User Story 2 - Auto-Confirm on Low Battery (Priority: P1)

An agent's battery is running low. When it attempts a move that would drop its battery below 15%, the system automatically asks the operator for confirmation before allowing the potentially stranding move.

**Why this priority**: Running out of battery can strand an agent, effectively removing it from the mission. This is as critical as geyser protection.

**Independent Test**: Can be tested by setting an agent battery to 16%, calculating a move cost that would reduce it below 15%, and verifying a confirmation prompt appears.

**Acceptance Scenarios**:

1. **Given** an agent has 16% battery and the move cost would bring it to 14%, **When** the agent issues a move action, **Then** the system creates a confirmation request warning about the post-move battery level.
2. **Given** an agent has 50% battery and a move would leave it at 48%, **When** the agent issues a move, **Then** no confirmation is requested and the move proceeds normally.

---

### User Story 3 - Auto-Confirm During Active Storm (Priority: P2)

A dust storm is active with intensity above 0.5. Any move action triggers a confirmation request, since storms cause increased battery drain and probabilistic move failures.

**Why this priority**: Storms are periodic and temporary — less immediately critical than geysers or battery depletion, but still a significant operational hazard.

**Independent Test**: Can be tested by setting storm phase to "active" with intensity > 0.5, then issuing a move and verifying confirmation is required.

**Acceptance Scenarios**:

1. **Given** a storm is active with intensity 0.7, **When** any movable agent issues a move, **Then** the system creates a confirmation request mentioning the active storm.
2. **Given** a storm is active with intensity 0.3, **When** an agent issues a move, **Then** no auto-confirmation is triggered for the storm condition alone.

---

### User Story 4 - Configuration Toggle (Priority: P2)

An administrator can disable the auto-confirm behavior via configuration, allowing moves to proceed without operator intervention when desired (e.g., during automated testing or demos).

**Why this priority**: Flexibility is important for different operational modes, but the feature defaults to enabled for safety.

**Independent Test**: Can be tested by setting the configuration toggle to disabled, then issuing a move into a hazard zone and verifying no confirmation is requested.

**Acceptance Scenarios**:

1. **Given** auto-confirm is disabled in settings, **When** an agent moves toward an erupting geyser, **Then** the move executes immediately without a confirmation dialog.
2. **Given** auto-confirm is enabled (default), **When** an agent moves toward a hazard, **Then** the confirmation flow is triggered.

---

### User Story 5 - Timeout Behavior (Priority: P3)

If the operator does not respond to an auto-confirmation request within the timeout period, the move is automatically denied for safety.

**Why this priority**: Timeout handling is a safety net for unattended operation, less common in normal use.

**Independent Test**: Can be tested by creating a confirmation request and letting it time out without responding, then verifying the move was skipped.

**Acceptance Scenarios**:

1. **Given** a confirmation request has been created for a hazardous move, **When** the timeout period elapses without a response, **Then** the move is denied and the agent receives an error indicating timeout.

---

### Edge Cases

- What happens when multiple hazard conditions are present simultaneously (e.g., geyser + low battery + storm)? The confirmation message should combine all active hazard reasons into a single prompt.
- What happens if an agent moves multiple tiles and only an intermediate tile has a hazard? The check should evaluate the destination tile for geysers (since the agent ends there), and post-move battery for the full cost.
- What happens if the host instance is not available (e.g., during tests)? The auto-confirm should be skippable when no host is provided.
- What happens for station agents that do not move? Station agents should never trigger auto-confirm since they do not perform move actions.
- What happens if a confirmation is already pending for the agent? The existing one-per-agent enforcement in the host should replace the old confirm with the new auto-confirm.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST automatically detect hazardous conditions before executing any move action for any movable agent type (rover, drone, hauler).
- **FR-002**: System MUST detect when the move destination tile has an erupting or warning-phase geyser.
- **FR-003**: System MUST detect when the agent's battery would drop below 15% after the move cost is applied.
- **FR-004**: System MUST detect when a dust storm is active with intensity greater than 0.5.
- **FR-005**: System MUST create a confirmation request through the existing host confirmation system when any hazard condition is detected.
- **FR-006**: System MUST generate a descriptive confirmation message that includes the specific hazard(s) detected and relevant details (geyser state, battery level, storm intensity).
- **FR-007**: System MUST wait for operator confirmation before executing the move when a hazard is detected.
- **FR-008**: System MUST execute the move normally when the operator confirms.
- **FR-009**: System MUST skip the move and return an error result when the operator denies or the request times out.
- **FR-010**: System MUST provide a configuration toggle (default enabled) to allow disabling auto-confirm behavior.
- **FR-011**: System MUST use the existing UI confirmation flow (WebSocket events and confirmation modal) without requiring UI changes.
- **FR-012**: System MUST use a 30-second timeout for auto-confirmation requests.

### Key Entities

- **Confirmation Request**: A pending approval that blocks a move action, containing the agent ID, hazard description, and timeout. Reuses the existing host confirmation entity.
- **Hazard Condition**: A detected danger at a move destination — geyser state, low post-move battery, or active high-intensity storm.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of moves toward erupting or warning-phase geyser tiles trigger a confirmation prompt when auto-confirm is enabled.
- **SC-002**: 100% of moves that would reduce battery below 15% trigger a confirmation prompt when auto-confirm is enabled.
- **SC-003**: 100% of moves during active storms with intensity > 0.5 trigger a confirmation prompt when auto-confirm is enabled.
- **SC-004**: Confirmed moves execute identically to non-hazardous moves (same result, same state changes).
- **SC-005**: Denied or timed-out moves produce no state changes (agent position, battery unchanged).
- **SC-006**: Auto-confirm can be fully disabled via configuration, with zero confirmation prompts generated when disabled.
- **SC-007**: All agent types that can move (rover, drone, hauler) are covered equally by the auto-confirm system.
- **SC-008**: Comprehensive test coverage: geyser warning, geyser erupting, active storm above threshold, low battery, combined conditions, config toggle off, timeout, confirm, and deny flows.
