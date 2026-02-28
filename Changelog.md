# Changelog

## 2026-02-28 — Sim Engine Frontend Integration

### Added
- `server/app/sim_agent.py` — `MockSimAgent` class wrapping `SimulationEngine` with random action selection for demo
- `ui/src/components/MarsGrid.vue` — 12x12 CSS grid with fog-of-war, rover/station markers, stone indicators
- `ui/src/components/RoverTelemetry.vue` — battery bar, position, inventory, mission progress panel
- `ui/src/components/EventLog.vue` — color-coded step result log with tick numbers
- `server/tests/test_sim_agent.py` — 6 unit tests for MockSimAgent

### Changed
- `server/app/main.py` — replaced `MockRoverAgent`/`RoverAgent` with `MockSimAgent`; single 3s agent loop; stops on terminal state
- `server/app/views.py` — WebSocket sends initial observation on connect; `/mission/status` returns real sim data
- `ui/src/App.vue` — complete rewrite: composes MarsGrid, RoverTelemetry, EventLog; responsive layout (desktop/tablet/mobile)
- `server/tests/test_health.py` — updated `test_mission_status` to set up `sim_agent` on app state

### Errors Prevented
- Ensured tuples/sets in observation are serialized to lists for JSON safety
- Test client needs `app.state.sim_agent` set manually since TestClient doesn't run lifespan
