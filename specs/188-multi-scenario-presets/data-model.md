# Data Model: Multi-Scenario Presets

**Branch**: `188-multi-scenario-presets` | **Date**: 2026-03-06

---

## Entities

### PresetDefinition

A static configuration object describing a simulation scenario.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Unique preset identifier (e.g., "storm_survival") |
| `description` | `str` | Human-readable description for UI display |
| `world_overrides` | `dict` | Nested dict merged into WORLD state after reset |
| `agent_overrides` | `dict[str, dict]` | Per-agent or pattern-matched overrides (battery, position) |
| `active_agents` | `str or None` | Comma-separated agent list, or None to keep default |

### World Overrides Structure

```python
{
    "storm": {
        "next_storm_tick": int,    # when next storm triggers
        "intensity": float,        # 0.0-1.0 initial intensity
    },
    "mission": {
        "target_quantity": int,    # basalt delivery target
    },
}
```

### Agent Overrides Structure

```python
{
    "rover-mistral": {
        "battery": float,         # starting battery (0.0-1.0)
    },
    "*": {                        # wildcard: applies to all agents
        "battery": float,
    },
}
```

## Storage

- **Presets**: In-memory Python dict (`PRESETS` in `presets.py`). No database persistence.
- **Active preset**: Stored only as `settings.preset` config value. Not persisted in WORLD dict.

## Relationships

- PresetDefinition --[modifies]--> WORLD dict (in-memory)
- PresetDefinition --[overrides]--> Settings.active_agents (temporary)
- Settings.preset --[selects]--> PresetDefinition at startup
