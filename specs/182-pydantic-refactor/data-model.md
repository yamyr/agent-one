# Data Model: Station Power Allocation Tool

**Feature**: Station Power Allocation Tool (allocate_power) + Budget Events
**Date**: 2026-03-05

---

## Entity: PowerBudget (new)

Stored in `WORLD["power_budgets"]` as a flat dict.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| agent_id (key) | `str` | Target agent identifier | Must exist in `WORLD["agents"]` |
| threshold (value) | `float` | Minimum battery level to maintain | Clamped to [0.0, 1.0] |

**Example state**:
```python
WORLD["power_budgets"] = {
    "rover-mistral": 0.3,
    "drone-mistral": 0.4,
    "hauler-mistral": 0.25,
}
```

**State Transitions**:
- Unset -> Set: Station calls `allocate_power(agent_id, amount)`
- Set -> Updated: Station calls `allocate_power` again with different amount
- Set -> Cleared: Mission ends or world reset

---

## Constant: STATION_POWER_CAPACITY (new)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| STATION_POWER_CAPACITY | `float` | `1.0` | Max aggregate power deficit the station can service per cycle |

Scalable by future upgrades (e.g., `power_mk2`).

---

## Event: PowerBudgetWarning (new)

Emitted when an agent's battery drops below its allocated power budget.

| Field | Type | Value |
|-------|------|-------|
| source | `str` | `"world"` |
| type | `str` | `"event"` |
| name | `str` | `"power_budget_warning"` |
| payload.agent_id | `str` | Agent whose battery is below budget |
| payload.battery | `float` | Current battery level |
| payload.budget | `float` | Allocated minimum threshold |
| payload.deficit | `float` | `budget - battery` (positive when below) |
| tick | `int` | Current simulation tick |

**Trigger**: `agent.battery < power_budgets[agent_id]`
**Debounce**: Max once per 3 ticks per agent.

---

## Event: EmergencyModeActivated (new)

Emitted when total power demand exceeds station capacity.

| Field | Type | Value |
|-------|------|-------|
| source | `str` | `"world"` |
| type | `str` | `"event"` |
| name | `str` | `"emergency_mode_activated"` |
| payload.total_demand | `float` | Sum of all budget deficits |
| payload.capacity | `float` | Station power capacity |
| payload.agents_in_deficit | `list[dict]` | `[{agent_id, battery, budget, deficit}]` |
| tick | `int` | Current simulation tick |

**Trigger**: `sum(max(0, budget - battery) for budgeted agents) > STATION_POWER_CAPACITY`
**Latch**: Emitted on activation; EmergencyModeDeactivated emitted when condition clears.

---

## Event: EmergencyModeDeactivated (new)

Emitted when total power demand drops back below station capacity after emergency.

| Field | Type | Value |
|-------|------|-------|
| source | `str` | `"world"` |
| type | `str` | `"event"` |
| name | `str` | `"emergency_mode_deactivated"` |
| payload.total_demand | `float` | Current total demand |
| payload.capacity | `float` | Station power capacity |
| tick | `int` | Current simulation tick |

---

## Updated Entity: WORLD (additions only)

| New Field | Type | Default | Description |
|-----------|------|---------|-------------|
| `power_budgets` | `dict[str, float]` | `{}` | Per-agent power budget thresholds |
| `emergency_mode` | `bool` | `False` | Whether emergency mode is active |
| `_power_warn_ticks` | `dict[str, int]` | `{}` | Internal debounce: last warning tick per agent |

---

## Updated Entity: StationContext (Pydantic model in station.py)

| New Field | Type | Default | Description |
|-----------|------|---------|-------------|
| `power_budgets` | `dict[str, float]` | `{}` | Current power allocations visible to station LLM |
| `emergency_mode` | `bool` | `False` | Whether emergency mode is active |

---

## Tool Schema: ALLOCATE_POWER_TOOL (new)

```python
ALLOCATE_POWER_TOOL = {
    "type": "function",
    "function": {
        "name": "allocate_power",
        "description": (
            "Set a power budget for an agent. Defines the minimum battery "
            "threshold to maintain. A PowerBudgetWarning event fires when "
            "the agent's battery drops below this level."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "The agent to set a power budget for (e.g. 'rover-mistral', 'drone-mistral').",
                },
                "amount": {
                    "type": "number",
                    "description": "Minimum battery threshold (0.0-1.0). Agent receives warnings below this level.",
                },
            },
            "required": ["agent_id", "amount"],
        },
    },
}
```

---

## Relationships

```
Station --[calls]--> allocate_power(agent_id, amount)
  |
  v
WORLD["power_budgets"][agent_id] = amount
  |
  v (each tick)
check_power_budgets()
  |
  +--> agent.battery < budget? --> PowerBudgetWarning
  |
  +--> total_demand > capacity? --> EmergencyModeActivated
  |
  +--> previously emergency, now resolved? --> EmergencyModeDeactivated
```
