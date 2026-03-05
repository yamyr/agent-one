# Quickstart: Simulation Replay UI

## Prerequisites

1. SurrealDB running on port 4002 with training data enabled
2. At least one training session recorded (run simulation with `TRAINING_DATA_ENABLED=true`)

## Setup

### Backend
```bash
cd server
echo "TRAINING_DATA_ENABLED=true" >> .env  # if not already set
uv sync
./run
```

### Frontend
```bash
cd ui
npm install
npm run dev
```

## Usage

1. Navigate to `http://localhost:4089/replay`
2. Available training sessions appear in the session picker
3. Click a session to load its snapshots
4. Use playback controls:
   - Play/Pause: auto-advance through snapshots
   - Speed: 1x, 2x, 5x, 10x
   - Scrubber: click/drag to jump to any snapshot
5. The world map renders each snapshot's world state
6. Events panel shows events for the current tick range

## API Endpoints

All existing, no new endpoints needed:

```
GET /api/training/sessions                          # list sessions
GET /api/training/sessions/{id}                     # session detail + stats
GET /api/training/sessions/{id}/snapshots           # world snapshots
GET /api/training/sessions/{id}/events              # events
```

## Testing

```bash
cd server && uv run pytest tests/test_training_logger.py -v
cd server && uv run pytest tests/test_replay_api.py -v
cd ui && npm run build
```
