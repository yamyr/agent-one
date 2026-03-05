# Quickstart: Multi-Scenario Presets

**Branch**: `188-multi-scenario-presets` | **Date**: 2026-03-06

---

## Verification Steps

### 1. Run Tests
```bash
cd server && uv run pytest tests/test_presets.py -v
```

### 2. List Presets via API
```bash
curl http://localhost:4009/api/presets | python3 -m json.tool
```

Expected: JSON array with 5 presets (default, storm_survival, resource_race, exploration, cooperative).

### 3. Apply a Preset
```bash
curl -X POST http://localhost:4009/api/presets/storm_survival/apply
```

Expected: `{"ok": true, "preset": "storm_survival"}`

### 4. Verify Storm Survival Mode
After applying `storm_survival`, check world snapshot:
```bash
curl http://localhost:4009/api/presets | python3 -m json.tool
```

Observe that storm timing is accelerated and agent batteries are reduced.

### 5. Startup Preset via Config
```bash
# In server/.env:
PRESET=exploration

# Restart server:
cd server && ./run
```

Server should log: "Applying startup preset: exploration"

### 6. Full Test Suite
```bash
cd server && uv run pytest tests/ -v
```

All tests should pass, including existing tests unaffected by the preset system.
