# Tasks: WS Reconnect Preserves Event History

**Feature Branch**: `072-ws-reconnect-state`  
**Created**: 2026-03-01

## Tasks

- [x] T1: Add `let isFirstConnect = true` variable in `useWebSocket.js`
- [x] T2: Guard `events.value = []` with `if (isFirstConnect)` in `ws.onopen`
- [x] T3: Set `isFirstConnect = false` after first connection
- [x] T4: Update `Changelog.md` with fix entry
- [x] T5: Run `npx eslint . && npm run build` — verify pass
- [x] T6: Commit, push, create PR
