# Quickstart: Goal Confidence Tracking

**Branch**: `181-goal-confidence-tracking`

## Prerequisites

- Python 3.14+, Node 24+, uv, SurrealDB running on port 4002
- `MISTRAL_API_KEY` set in `server/.env`

## Setup

```bash
git checkout 181-goal-confidence-tracking
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

Open `http://localhost:4089`. Each agent pane now shows a confidence bar below the battery bar.

## Verify Feature

1. **Backend**: Run tests
   ```bash
   cd server && uv run pytest tests/ -v -k "confidence"
   ```

2. **UI**: Watch the simulation dashboard — confidence bars should:
   - Start at 50% (amber) when mission assigned
   - Turn green on repeated successes
   - Drop to red on failures/storms
   - Animate smoothly on transitions

3. **Training data**: Check training log output includes `goal_confidence_before` and `goal_confidence_after` fields.

## Key Files Changed

| File | Change |
|------|--------|
| `server/app/models.py` | Added `goal_confidence` to RoverAgentState, HaulerAgentState, RoverSummary |
| `server/app/world.py` | Initialize confidence, update in tick loop, include in observations/snapshot |
| `server/app/agent.py` | Capture confidence before/after in training data, apply updates after actions |
| `server/app/training_models.py` | Added goal_confidence fields to TurnWorldSnapshot, TrainingTurn |
| `ui/src/components/ConfidenceBar.vue` | New component (cloned from BatteryBar) |
| `ui/src/components/AgentPane.vue` | Added confidence bar rendering |
| `ui/src/components/AgentPanes.vue` | Added goalConfidence helper + prop passing |
