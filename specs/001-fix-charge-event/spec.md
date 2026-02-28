# Feature Specification: Fix DroneLoop Charge Event Name

**Feature Branch**: `001-fix-charge-event`  
**Created**: 2026-03-01  
**Status**: Complete  
**Input**: User description: "Fix DroneLoop charge event name: DroneLoop._handle_charge_request() emits a 'charge_rover' event at agent.py line ~922 when it should emit 'charge_agent' or 'charge_drone' since it's charging a drone, not a rover. The incorrect event name causes confusion in the event log and could break any consumers filtering by event name."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Correct Charge Event Naming (Priority: P1)

When a drone is charged at the station, the broadcast event should use the generic name `charge_agent` instead of the misleading `charge_rover`. This ensures event log accuracy and prevents downstream consumers (narrator, UI filters, analytics) from misidentifying drone charges as rover charges.

**Why this priority**: This is the core bug — a semantically incorrect event name that misleads operators and could break event-filtering logic.

**Independent Test**: Can be fully tested by running the drone charge flow and verifying the emitted event name is `charge_agent`.

**Acceptance Scenarios**:

1. **Given** a drone is at the station with battery < 100%, **When** the drone auto-charges, **Then** the broadcast event name is `charge_agent` (not `charge_rover`).
2. **Given** a rover is at the station with battery < 100%, **When** the rover auto-charges, **Then** the broadcast event name is also `charge_agent` for consistency.

---

### User Story 2 - Consistent Event Naming Across Agent Types (Priority: P1)

Both RoverLoop and DroneLoop should emit the same generic `charge_agent` event name when charging, since the `charge_agent()` function in `world.py` already supports any agent type.

**Why this priority**: Consistency prevents future bugs when new agent types are added.

**Independent Test**: Can be tested by checking both RoverLoop and DroneLoop charge events emit `charge_agent`.

**Acceptance Scenarios**:

1. **Given** the RoverLoop auto-charge code, **When** inspected, **Then** the event name is `charge_agent`.
2. **Given** the DroneLoop auto-charge code, **When** inspected, **Then** the event name is `charge_agent`.

---

### User Story 3 - Narrator Compatibility (Priority: P2)

The narrator event filtering must recognize the new `charge_agent` event name to continue generating narration for charge events.

**Why this priority**: Without updating the narrator, charge events would silently stop being narrated.

**Independent Test**: Can be tested by sending a `charge_agent` event through the narrator and verifying it produces narration text.

**Acceptance Scenarios**:

1. **Given** a `charge_agent` event is broadcast, **When** the narrator processes it, **Then** it generates appropriate charge narration text.

---

### Edge Cases

- The station's `charge_rover` LLM tool name is kept unchanged (separate concern from broadcast event name).
- The `charge_rover = charge_agent` backward-compat function alias in world.py is untouched.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: DroneLoop MUST emit events with `name="charge_agent"` when a drone is charged at the station.
- **FR-002**: RoverLoop MUST emit events with `name="charge_agent"` when a rover is charged at the station.
- **FR-003**: The narrator MUST recognize `charge_agent` events and produce appropriate narration text.
- **FR-004**: The narrator drama weights MUST include `charge_agent` with weight 2.
- **FR-005**: All existing tests MUST pass after the event name change.

### Key Entities

- **Charge Event**: Broadcast message with `source="station"`, `type="action"`, `name="charge_agent"`, carrying battery before/after payload.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All charge events emitted by both RoverLoop and DroneLoop use the name `charge_agent`.
- **SC-002**: The narrator correctly narrates charge events using the `charge_agent` event name.
- **SC-003**: All existing tests pass without regression (0 test failures).
- **SC-004**: Ruff linting and formatting checks pass with no errors.
