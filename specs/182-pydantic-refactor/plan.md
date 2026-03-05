# Implementation Plan: Station Power Allocation Tool (allocate_power) + Budget Events

**Branch**: `182-pydantic-refactor` | **Date**: 2026-03-05 | **Spec**: `/specs/182-pydantic-refactor/spec.md`
**Input**: Feature specification + user description of power allocation scope

## Summary

Add `allocate_power(agent_id, amount)` tool to the station agent, enabling fine-grained power budget management. The tool sets a minimum battery threshold per agent. The simulation tick loop monitors budgets and emits `PowerBudgetWarning` events when agents drop below their threshold, and `EmergencyModeActivated` when total demand exceeds station capacity. The station system prompt is updated with power management guidance, and the UI gains a `PowerBudgetBar` indicator in AgentPane.

## Technical Context

**Language/Version**: Python 3.14+ (server), JavaScript/Vue 3 (UI)
**Primary Dependencies**: FastAPI, Pydantic v2, mistralai SDK, Vue 3, Vite
**Storage**: In-memory WORLD dict (simulation state), SurrealDB on port 4002 (unchanged)
**Testing**: pytest with in-memory SurrealDB (server), manual verification (UI)
**Target Platform**: Linux/macOS server, modern browser (desktop/tablet/mobile)
**Project Type**: Web application (FastAPI backend + Vue 3 SPA)
**Performance Goals**: No measurable latency impact; budget check runs O(n) per tick where n = budgeted agents (max ~9)
**Constraints**: Must not break existing station tools or charge mechanics; backward-compatible world state
**Scale/Scope**: 4 server files + 2 UI files changed, ~200 lines added

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution is not yet configured (template placeholders). No gates to evaluate. Proceeding.

**Post-Phase 1 Re-check**: Constitution still unconfigured. No violations to report.

## Project Structure

### Documentation (this feature)

```text
specs/182-pydantic-refactor/
├── plan.md              # This file
├── research.md          # Phase 0: 7 research decisions
├── data-model.md        # Phase 1: entities, events, tool schema
├── quickstart.md        # Phase 1: verification guide
├── contracts/
│   └── websocket-message-schema.md  # Phase 1: new WS events
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (changes)

```text
server/app/
├── station.py           # ALLOCATE_POWER_TOOL, _execute_allocate_power(), system prompt update, StationContext fields
├── world.py             # STATION_POWER_CAPACITY, WORLD init, check_power_budgets(), allocate_power()
├── host.py              # route_station_actions() allocate_power case, budget event broadcasting
└── tests/
    ├── test_station.py  # allocate_power tool tests
    └── test_power_budget.py  # PowerBudgetWarning, EmergencyMode tests (new)

ui/src/
├── components/
│   ├── PowerBudgetBar.vue   # New component (mirrors BatteryBar.vue)
│   └── AgentPane.vue        # Add PowerBudgetBar to agent-row-2
└── (no new composables needed — uses existing worldState from useWebSocket)
```

**Structure Decision**: Web application (Option 2 pattern). Backend changes in `server/app/`, frontend changes in `ui/src/components/`. No new directories created.

## Design Decisions

### D1: Power Budget as Minimum Threshold (not charge cap)

`allocate_power(agent_id, amount)` sets a minimum battery threshold. When `agent.battery < amount`, a `PowerBudgetWarning` fires. Charging is NOT capped — station can always charge to 1.0. The budget is for monitoring and prioritization, not enforcement.

**Why**: Simpler, backward-compatible with existing charge mechanics, and more useful for the LLM (warnings inform strategic decisions rather than artificial limits).

### D2: Budget Check in Tick Loop

`check_power_budgets()` is called from `next_tick()` in `world.py`, alongside existing `apply_structure_passive_effects()`. Returns a list of events to broadcast.

**Why**: Natural extension point. Budget violations are detected every tick regardless of agent actions.

### D3: EmergencyMode as Aggregate Demand Signal

Emergency mode activates when `sum(deficits) > STATION_POWER_CAPACITY`. This is a station-level crisis distinct from individual `PowerBudgetWarning` events.

**Why**: Gives the LLM a clear signal to change strategy (e.g., recall all agents, prioritize critical missions).

### D4: Debounced Warnings (3-tick cooldown)

`PowerBudgetWarning` is emitted max once per 3 ticks per agent to avoid flooding the station's context and the WebSocket channel.

**Why**: Without debouncing, an agent with low battery would generate a warning every tick, bloating station memory and UI timeline.

### D5: UI PowerBudgetBar (conditional)

Displayed only when `worldState.power_budgets[agentId]` exists. Uses the same visual pattern as `BatteryBar.vue` (3rem inline bar, color-coded).

**Why**: Zero visual change until station starts using allocate_power. Consistent with existing design system.

## Implementation Order

1. **world.py** — WORLD state additions + `check_power_budgets()` + `_execute_allocate_power()`
2. **station.py** — ALLOCATE_POWER_TOOL + system prompt + StationContext fields
3. **host.py** — Route allocate_power action + broadcast budget events from tick
4. **tests** — Unit tests for allocate_power, budget warnings, emergency mode
5. **PowerBudgetBar.vue** — New UI component
6. **AgentPane.vue** — Integrate PowerBudgetBar

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Station LLM ignores allocate_power tool | Low — feature is opt-in | System prompt explicitly guides usage; tool is included in tools array |
| PowerBudgetWarning floods station memory | Medium — context overflow | 3-tick debounce; memory cap already enforced (8 entries) |
| EmergencyMode triggers too aggressively | Low | STATION_POWER_CAPACITY = 1.0 is generous; tunable constant |
| UI breaks on missing power_budgets field | Low | Conditional rendering; field defaults to empty dict |

## Complexity Tracking

No constitution violations to justify. Feature is additive with minimal complexity.
