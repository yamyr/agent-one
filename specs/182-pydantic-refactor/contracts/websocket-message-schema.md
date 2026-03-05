# WebSocket Message Schema Contract: Power Allocation Events

**Feature**: Station Power Allocation Tool | **Date**: 2026-03-05

## New Events Added to WebSocket `/ws` Endpoint

All events follow the existing base message schema:
```json
{
  "source": "string",
  "type": "string",
  "name": "string",
  "payload": "object",
  "id": "string (UUID v4)",
  "ts": "number (Unix timestamp)",
  "tick": "integer",
  "correlation_id": "string|null"
}
```

---

### EventMessage: power_budget_warning

Emitted when an agent's battery drops below its allocated power budget threshold.

```json
{
  "source": "world",
  "type": "event",
  "name": "power_budget_warning",
  "payload": {
    "agent_id": "rover-mistral",
    "battery": 0.22,
    "budget": 0.30,
    "deficit": 0.08
  },
  "tick": 45
}
```

| payload key | type | description |
|-------------|------|-------------|
| agent_id | string | Agent whose battery is below budget |
| battery | number (0-1) | Current battery level |
| budget | number (0-1) | Allocated minimum threshold |
| deficit | number (0-1) | budget - battery (positive when below) |

**Frequency**: Max once per 3 ticks per agent (debounced).

---

### EventMessage: emergency_mode_activated

Emitted when total power demand across all budgeted agents exceeds station capacity.

```json
{
  "source": "world",
  "type": "event",
  "name": "emergency_mode_activated",
  "payload": {
    "total_demand": 1.35,
    "capacity": 1.0,
    "agents_in_deficit": [
      {"agent_id": "rover-mistral", "battery": 0.10, "budget": 0.30, "deficit": 0.20},
      {"agent_id": "drone-mistral", "battery": 0.05, "budget": 0.40, "deficit": 0.35},
      {"agent_id": "rover-2", "battery": 0.00, "budget": 0.30, "deficit": 0.30},
      {"agent_id": "hauler-mistral", "battery": 0.10, "budget": 0.25, "deficit": 0.15},
      {"agent_id": "rover-large", "battery": 0.15, "budget": 0.30, "deficit": 0.15},
      {"agent_id": "rover-4", "battery": 0.10, "budget": 0.30, "deficit": 0.20}
    ]
  },
  "tick": 78
}
```

| payload key | type | description |
|-------------|------|-------------|
| total_demand | number | Sum of all budget deficits |
| capacity | number | Station power capacity (default 1.0) |
| agents_in_deficit | array | List of agents with deficit details |

---

### EventMessage: emergency_mode_deactivated

Emitted when total power demand drops back below capacity after emergency.

```json
{
  "source": "world",
  "type": "event",
  "name": "emergency_mode_deactivated",
  "payload": {
    "total_demand": 0.75,
    "capacity": 1.0
  },
  "tick": 92
}
```

---

### ActionMessage: allocate_power

Emitted when station executes the allocate_power tool.

```json
{
  "source": "station",
  "type": "action",
  "name": "allocate_power",
  "payload": {
    "ok": true,
    "agent_id": "rover-mistral",
    "amount": 0.30,
    "previous": null
  },
  "tick": 5
}
```

| payload key | type | description |
|-------------|------|-------------|
| ok | boolean | Whether allocation succeeded |
| agent_id | string | Target agent |
| amount | number (0-1) | Allocated minimum threshold |
| previous | number or null | Previous budget (null if first allocation) |
| error | string (optional) | Error message if ok=false |

---

### World State Snapshot Additions

The periodic `state` event (`name: "state"`) payload gains:

```json
{
  "power_budgets": {
    "rover-mistral": 0.30,
    "drone-mistral": 0.40
  },
  "emergency_mode": false
}
```

UI consumers should read `power_budgets[agentId]` to display the PowerBudgetBar.

---

## Backward Compatibility

- Existing events are unchanged
- New events use the same base schema
- UI consumers that don't handle `power_budget_warning`/`emergency_mode_activated` will simply ignore them
- World state snapshot additions are additive (new keys, no removed/renamed keys)
