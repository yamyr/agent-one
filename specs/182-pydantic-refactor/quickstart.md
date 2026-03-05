# Quickstart: Station Power Allocation Tool

**Branch**: `182-pydantic-refactor`

## Prerequisites

- Python 3.14+, Node 24+, uv, SurrealDB running on port 4002
- `MISTRAL_API_KEY` set in `server/.env`

## Setup

```bash
git checkout 182-pydantic-refactor
cd server && uv sync
cd ../ui && npm install
```

## Run

```bash
# Terminal 1: Server
cd server && ./run

# Terminal 2: UI
cd ui && npm run dev
```

Open `http://localhost:4089`.

## Verify Feature

1. **Power allocation tool**: Start simulation and observe station behavior
   ```bash
   cd server && uv run pytest tests/ -v -k "allocate_power"
   ```

2. **PowerBudgetWarning events**: Verify warnings fire when agents drop below budget
   ```bash
   cd server && uv run pytest tests/ -v -k "power_budget_warning"
   ```

3. **EmergencyMode events**: Verify emergency mode activates under high demand
   ```bash
   cd server && uv run pytest tests/ -v -k "emergency_mode"
   ```

4. **Full Regression**: Run all tests
   ```bash
   cd server && uv run pytest tests/ -v
   ```

5. **Runtime Verification**: In the simulation UI, observe:
   - Station uses `allocate_power` tool to set budgets for agents
   - PowerBudgetBar appears in AgentPane for agents with set budgets
   - PowerBudgetWarning events appear in the timeline when agents drop below budget
   - EmergencyModeActivated appears when total demand exceeds capacity

## Key Files Changed

| File | Change |
|------|--------|
| `server/app/station.py` | Added `ALLOCATE_POWER_TOOL`, `_execute_allocate_power()`, updated system prompt with POWER MANAGEMENT section, added `power_budgets`/`emergency_mode` to StationContext |
| `server/app/world.py` | Added `STATION_POWER_CAPACITY` constant, `power_budgets`/`emergency_mode`/`_power_warn_ticks` to WORLD init, `check_power_budgets()` function, `allocate_power()` execution logic |
| `server/app/host.py` | Added `allocate_power` case to `route_station_actions()`, broadcast PowerBudgetWarning/EmergencyMode events from tick loop |
| `ui/src/components/PowerBudgetBar.vue` | New component: inline bar showing power budget threshold (mirrors BatteryBar pattern) |
| `ui/src/components/AgentPane.vue` | Added PowerBudgetBar in agent-row-2, conditionally displayed when budget is set |
