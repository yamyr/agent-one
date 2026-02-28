# Quickstart: Non-Blocking Narration Streaming

## Goal

Validate that narration streaming no longer blocks simulation progress while preserving emitted chunk behavior.

## Steps

1. Run narrator-focused tests:

```bash
cd server
uv run pytest tests/test_narrator.py -q
```

2. Run full server test suite:

```bash
cd server
uv run pytest tests/ -q
```

3. Run server lint checks:

```bash
cd server
uv run ruff format --check app/ tests/
uv run ruff check app/ tests/
```

4. Manual runtime verification:

```bash
cd server
./run
```

While server is running and UI is connected, trigger narration-producing events and confirm:
- Simulation tick/event updates continue while narration text streams.
- Narration chunks continue to appear in order.
- No freeze in websocket-driven UI panels during narration.
