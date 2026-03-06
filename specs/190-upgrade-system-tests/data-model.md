# Data Model: Upgrade System Tests

This feature does not introduce new data entities. It tests existing entities documented below for reference.

## Existing Entities Under Test

### Base Upgrade (UPGRADES dict)

| Field | Type | Description |
|-------|------|-------------|
| water | int | Water cost from station_resources |
| gas | int | Gas cost from station_resources |
| description | str | Human-readable upgrade description |
| max_level | int | Maximum upgrade level (1 or 2) |

**Instances**:
- `charge_mk2`: water=50, gas=20, max_level=1 -- doubles station charge rate
- `extended_fuel`: water=30, gas=10, max_level=2 -- +100 rover fuel capacity per level
- `enhanced_scanner`: water=20, gas=15, max_level=2 -- +1 rover reveal radius per level
- `repair_bay`: water=40, gas=30, max_level=1 -- auto-repair rovers at station

### Station Upgrades State (WORLD["station_upgrades"])

| Field | Type | Description |
|-------|------|-------------|
| {upgrade_name} | int | Current level of each upgrade (0 = not purchased) |

### Station Resources (WORLD["station_resources"])

| Field | Type | Description |
|-------|------|-------------|
| water | int | Water available for upgrades |
| gas | int | Gas available for upgrades |
| parts | list | Salvaged parts (not used by base upgrades) |

### Structure (building upgrade target)

| Field | Type | Description |
|-------|------|-------------|
| type | str | One of: refinery, solar_panel_structure, accumulator |
| position | list[int] | [x, y] grid position |
| active | bool | Whether structure is operational |
| upgrade_level | int | Current level (1-3, default 1) |
| contents | dict | Type-specific attributes (affected by bonuses) |
| _base_contents | dict | Cached original contents (set on first bonus application) |

**Contents by type**:
- refinery: `{processing_capacity: 50}`
- solar_panel_structure: `{charge_rate: 0.01, charge_interval: 2, charge_radius: 1}`
- accumulator: `{capacity_bonus: 0.20, recharge_rate: 0.01, recharge_interval: 5}`

### Bonus Formula

`multiplier = 1.5 ^ (level - 1)`

| Level | Multiplier |
|-------|-----------|
| 1 | 1.0 |
| 2 | 1.5 |
| 3 | 2.25 |

Solar panel charge_radius: `base_radius + (level - 1)`
Accumulator recharge_interval: `max(1, base_interval - (level - 1))`
