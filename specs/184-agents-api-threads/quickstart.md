# Quickstart: Agents API — Persistent Conversation Threads

**Branch**: `184-agents-api-threads`

## Prerequisites

- Python 3.14+, Node 24+, uv, SurrealDB running on port 4002
- `MISTRAL_API_KEY` set in `server/.env`

## Setup

```bash
git checkout 184-agents-api-threads
cd server && uv sync
```

## Run

```bash
# Terminal 1: Server (with Agents API backend)
cd server
AGENT_BACKEND=agents_api ./run
```

## Verify Feature

1. **Thread persistence**: Verify conversation IDs are reused across turns
   ```bash
   cd server && uv run pytest tests/ -v -k "conversation_thread"
   ```

2. **Training logger**: Verify training data is logged for Agents API turns
   ```bash
   cd server && uv run pytest tests/ -v -k "agents_api_training"
   ```

3. **Config toggle**: Verify persist_threads config works
   ```bash
   cd server && uv run pytest tests/ -v -k "persist_threads"
   ```

4. **Full Regression**: Run all tests
   ```bash
   cd server && uv run pytest tests/ -v
   ```

## Key Files Changed

| File | Change |
|------|--------|
| `server/app/agents_api.py` | Added `_conversation_id` to all 3 reasoners, switched to `append()` on subsequent turns, removed `# TODO` |
| `server/app/config.py` | Added `agents_api_persist_threads: bool = True` |
| `server/tests/test_agents_api.py` | Added thread persistence and training logger tests |
