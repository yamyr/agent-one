# Implementation Plan: WS Reconnect Preserves Event History

**Feature Branch**: `072-ws-reconnect-state`  
**Created**: 2026-03-01

## Overview

Add a `isFirstConnect` flag to `useWebSocket.js` so that `events` are only cleared on the initial connection, not on reconnects. `worldState` continues to be cleared on every connect since the server repopulates it.

## Affected Files

| File | Action | Description |
|------|--------|-------------|
| `ui/src/composables/useWebSocket.js` | Modify | Add `isFirstConnect` flag, conditional event clearing |
| `Changelog.md` | Modify | Add fix entry under [Unreleased] |

## Implementation Steps

1. Add `let isFirstConnect = true` after the existing `let eventUid = 0` line
2. In `ws.onopen`, wrap `events.value = []` with `if (isFirstConnect)` guard
3. Set `isFirstConnect = false` after the guard block
4. Keep `worldState.value = null` unconditional (server repopulates)
5. Update Changelog.md
6. Verify with ESLint and build
