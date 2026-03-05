# Quickstart: Rover Peer-to-Peer Messaging

**Branch**: `185-rover-peer-messaging`

## Prerequisites

- Python 3.14+, Node 24+, uv, SurrealDB running on port 4002
- `MISTRAL_API_KEY` set in `server/.env`

## Setup

```bash
git checkout 185-rover-peer-messaging
cd server && uv sync
```

## Run

```bash
# Terminal 1: Server
cd server && ./run

# Terminal 2: UI
cd ui && npm run dev
```

## Verify Feature

1. **notify_peer tool**: Verify tool definition and execution
   ```bash
   cd server && uv run pytest tests/ -v -k "notify_peer"
   ```

2. **Message delivery**: Verify messages arrive in target rover's inbox
   ```bash
   cd server && uv run pytest tests/ -v -k "peer_message_delivery"
   ```

3. **Prompt integration**: Verify peer section in rover context
   ```bash
   cd server && uv run pytest tests/ -v -k "peer_prompt"
   ```

4. **UI visualization**: Open http://localhost:4089, watch for purple/magenta communication lines between rovers when peer messages are sent

5. **Full Regression**: Run all tests
   ```bash
   cd server && uv run pytest tests/ -v
   ```

## Key Files Changed

| File | Change |
|------|--------|
| `server/app/world.py` | Added `_execute_notify_peer()` with validation and `send_agent_message()` call |
| `server/app/agent.py` | Added `NOTIFY_PEER_TOOL`, tick handler for peer messages, PEER COMMUNICATION prompt section |
| `ui/src/components/WorldMap.vue` | Added `peer` color (#cc44cc) and `peer_message` event handler |
| `server/tests/test_peer_messaging.py` | Tests for tool execution, delivery, validation, prompt |
