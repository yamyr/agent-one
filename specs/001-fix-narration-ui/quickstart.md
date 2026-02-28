# Quickstart: Fix Narration Text Display & Voice Toggle

## Changes Required

### 1. Fix WebSocket event matching (useWebSocket.js)

Change narrator event routing from `event.type` to `event.name`:
- Line 41: `event.type === 'narration'` → `event.name === 'narration'`
- Line 43: `event.type === 'narration_chunk'` → `event.name === 'narration_chunk'`

### 2. Fix voice toggle initialization (App.vue)

- Line 14: Change `ref(true)` → `ref(false)`
- Add narration status fetch in `onWsConnect()` callback

### 3. Verify

```bash
cd server && rut tests/test_narrator.py   # all 30 tests pass
cd ui && npx eslint src/                   # zero warnings
cd ui && npm run build                     # clean build
```

## Files Touched

| File | Change |
| ---- | ------ |
| `ui/src/composables/useWebSocket.js` | Fix event name matching (2 lines) |
| `ui/src/App.vue` | Init toggle to false, fetch status on connect (3 lines) |
