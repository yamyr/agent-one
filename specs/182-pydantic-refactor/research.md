# Research: Station Power Allocation Tool (allocate_power) + Budget Events

**Feature**: Station Power Allocation Tool
**Date**: 2026-03-05
**Branch**: `182-pydantic-refactor`

---

## R1: How does the existing charge mechanism work?

**Decision**: Extend the existing charge system with budget-aware monitoring, not replace it.

**Rationale**: The current `_execute_charge()` in `world.py:1869-1895` adds `CHARGE_RATE = 0.20` (20%) per call, with optional `charge_mk2` upgrade doubling it. Charging requires co-location with station. The mechanism is clean and well-tested. Power allocation should layer on top: `allocate_power` sets a budget threshold, and the tick loop monitors agents against their budgets to emit warnings.

**Alternatives Considered**:
- **Replace charge system entirely**: Rejected. Existing charge flow is stable, tested, and backward-compatible.
- **Make allocate_power control charge rate**: Rejected. A threshold-based budget (minimum battery to maintain) is more intuitive for the LLM and aligns with ROADMAP language.

---

## R2: Where should power budgets be stored in world state?

**Decision**: Add `WORLD["power_budgets"]` as a top-level dict `{agent_id: float}` where the float is the minimum battery threshold (0.0-1.0).

**Rationale**: WORLD dict is the single source of truth. Power budgets are a station-level concept that applies across agents. A flat dict keyed by agent_id mirrors the existing `WORLD["agents"]` pattern. Storing as a minimum threshold aligns with event semantics: PowerBudgetWarning fires when battery drops below the allocated minimum.

**Alternatives Considered**:
- **Store inside each agent's state dict**: Rejected. Power budgets are a station concern, not an agent concern.
- **Nested structure with allocation history**: Rejected. Over-engineering for current scope.
- **Absolute power units (e.g., 100 fuel units)**: Rejected. System uses 0.0-1.0 fractions everywhere.

---

## R3: How should PowerBudgetWarning events be emitted?

**Decision**: Add `check_power_budgets()` function in `world.py`, called from the tick loop. Emit when `agent.battery < power_budgets[agent_id]`. Debounce warnings to avoid spam (max once per 3 ticks per agent).

**Rationale**: The tick loop (`next_tick()`) already calls `apply_structure_passive_effects()`. Adding a budget check here is natural. Events emit via standard `make_message()` -> broadcast pipeline. Include agent_id, current battery, allocated threshold, and deficit amount.

**Alternatives Considered**:
- **Check only during charge operations**: Rejected. Warnings should fire whenever battery drops below threshold, not just at charge time.
- **Check in agent reasoning loop**: Rejected. Power budget monitoring is a station/world responsibility.

---

## R4: How should EmergencyModeActivated be triggered?

**Decision**: Define `STATION_POWER_CAPACITY = 1.0`. Calculate total demand as `sum(max(0, budget - agent.battery) for each budgeted agent)`. Emit EmergencyModeActivated when `total_demand > STATION_POWER_CAPACITY`.

**Rationale**: Introducing a finite station capacity creates meaningful resource management decisions for the LLM. The capacity can scale with upgrades. EmergencyMode represents a systemic crisis (distinct from single-agent PowerBudgetWarning).

**Alternatives Considered**:
- **Trigger on agent count threshold**: Rejected. Doesn't capture actual power demand dynamics.
- **Trigger when N agents have battery < 20%**: Rejected. Arbitrary, ignores allocated budgets.
- **No station capacity, emit when any budget is violated**: Rejected. EmergencyMode should be systemic, not single-agent.

---

## R5: How should the station system prompt be updated?

**Decision**: Add a "POWER MANAGEMENT" section to the station system prompt describing the allocate_power tool semantics, budget monitoring, and recommended strategies.

**Rationale**: Existing prompt has structured sections (AGENT TYPES, RESOURCES, DRONE COORDINATION, HAULER COORDINATION). A parallel POWER MANAGEMENT section follows the pattern. The LLM needs guidance on when to allocate power (mission start, after storms), threshold recommendations, and how to respond to budget events.

**Alternatives Considered**:
- **Rely solely on tool description**: Rejected. Tool descriptions are terse; system prompt provides strategic guidance.
- **Add to existing RESOURCES section**: Rejected. Power management is a distinct operational concern.

---

## R6: How should the UI display power budgets?

**Decision**: Add a `PowerBudgetBar` component (based on `BatteryBar.vue`) in `AgentPane.vue` agent-row-2. Display conditionally when a power budget is set.

**Rationale**: `BatteryBar.vue` is a clean 3rem-wide inline bar with dynamic color coding and CSS transitions. Duplicating this pattern for power budget maintains visual consistency. Show only when `power_budget` is set (backward compatible).

**Alternatives Considered**:
- **Overlay on BatteryBar**: Rejected. Mixing concepts in one bar is confusing.
- **Text-only display**: Rejected. Visual bars are more scannable in compact AgentPane layout.

---

## R7: Should charge operations enforce budgets?

**Decision**: No. The budget is a MINIMUM threshold for warnings, not a charge cap. `charge_agent` continues to charge to 1.0 regardless of budget.

**Rationale**: The allocate_power tool sets the floor (minimum desired battery), not the ceiling. The station should always be able to charge agents fully. The budget is for prioritization via warnings, not enforcement. This avoids confusing the LLM with artificial charge limits.

**Alternatives Considered**:
- **Cap charging at budget level**: Rejected. Would prevent full charges and confuse the LLM.
- **Scale charge rate by budget proportion**: Rejected. Adds complexity without clear benefit.
