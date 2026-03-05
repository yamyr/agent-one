# Quickstart: Human-in-the-Loop (UiRequest::Confirm)

**Branch**: `183-human-in-the-loop`

## Prerequisites

- Python 3.14+, Node 24+, uv, SurrealDB running on port 4002
- `MISTRAL_API_KEY` set in `server/.env`

## Setup

```bash
git checkout 183-human-in-the-loop
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

1. **request_confirm tool**: Verify the tool is available to rovers
   ```bash
   cd server && uv run pytest tests/ -v -k "request_confirm"
   ```

2. **Confirmation flow**: Verify pause/resume and response routing
   ```bash
   cd server && uv run pytest tests/ -v -k "confirm"
   ```

3. **Timeout handling**: Verify auto-deny on timeout
   ```bash
   cd server && uv run pytest tests/ -v -k "confirm_timeout"
   ```

4. **Full Regression**: Run all tests
   ```bash
   cd server && uv run pytest tests/ -v
   ```

5. **Runtime Verification**: In the simulation UI, observe:
   - When a rover approaches a storm zone or hazard, it may call `request_confirm`
   - A modal appears with the rover's question, Confirm and Deny buttons, and a countdown
   - Clicking Confirm allows the rover to proceed; Deny prevents the action
   - If no response within timeout (30s default), the action is auto-denied
   - The event log shows confirm_request, confirm_response, and confirm_timeout events

## Key Files Changed

| File | Change |
|------|--------|
| `server/app/agent.py` | Added `REQUEST_CONFIRM_TOOL` to ROVER_TOOLS, special-case execution in RoverLoop.tick() with asyncio.Event await |
| `server/app/host.py` | Added `_pending_confirms` dict, `create_confirm()`, `resolve_confirm()`, `get_pending_confirm()`, `cleanup_confirm()` methods, `CONFIRM_DEFAULT_TIMEOUT` constant |
| `server/app/main.py` | Added `POST /api/confirm` endpoint |
| `server/app/views.py` | No changes (WebSocket events broadcast via existing broadcaster) |
| `server/app/world.py` | No world state changes (confirmation is transient, not persisted) |
| `ui/src/components/ConfirmModal.vue` | New component: modal with question, countdown, Confirm/Deny buttons |
| `ui/src/pages/SimulationPage.vue` | Added ConfirmModal integration, confirm_request event handling |
