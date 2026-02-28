# Implementation Plan: Replace Logging f-strings

**Feature Branch**: `073-logging-fstrings`  
**Created**: 2026-03-01

## Overview

Replace 2 f-string logging calls in `server/app/broadcast.py` with lazy `%`-style formatting per Python logging best practices.

## Affected Files

| File | Action | Description |
|------|--------|-------------|
| `server/app/broadcast.py` | Modify | Replace 2 f-string logger.info calls with % formatting |
| `Changelog.md` | Modify | Add style entry under [Unreleased] |

## Implementation Steps

1. Line 22: `logger.info(f"Client connected ({len(self._connections)} total)")` → `logger.info("Client connected (%d total)", len(self._connections))`
2. Line 26: `logger.info(f"Client disconnected ({len(self._connections)} total)")` → `logger.info("Client disconnected (%d total)", len(self._connections))`
3. Update Changelog.md
4. Verify with ruff and tests
