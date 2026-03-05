# Data Model: Test Coverage Expansion

No data model changes required. This feature adds tests only -- no new models, tables, or state mutations.

## Relevant Existing Data Structures

- `WORLD["structures"]` -- list of structure dicts (gas_plant, solar_panel_structure, etc.)
- `WORLD["agents"]` -- dict of agent dicts keyed by agent_id
- `WORLD["storm"]` -- storm state dict with phase, intensity, multiplier info
- `WORLD["station_resources"]` -- `{water: int, gas: int, parts: list}`
- `WORLD["station_upgrades"]` -- `{upgrade_name: level}`
- `WORLD["ground_items"]` -- list of dropped items on the ground
- `WORLD["delivered_items"]` -- list of items delivered to station
