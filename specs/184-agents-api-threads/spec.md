# Feature Specification: Agents API — Persistent Conversation Threads + Training Logger

**Branch**: `184-agents-api-threads`
**Date**: 2026-03-05
**Status**: Agents API merged in #248 but shallow — no persistent threads, training logger not wired

---

## Problem Statement

The Agents API's key advantage over chat completions is stateful conversation threads. The current implementation calls `conversations.start()` every turn, discarding the `conversation_id` — creating orphaned conversations on Mistral's servers and negating the benefit of cross-turn memory. Additionally, the training logger is not wired up for the Agents API path (marked `# TODO` at line 113).

## User Stories

### US1 (P1): Persistent Conversation Threads
**As a** simulation operator, **I want** Agents API reasoners to maintain persistent conversation threads, **so that** the LLM has cross-turn memory and context continuity.

**Acceptance Criteria**:
- First turn calls `conversations.start()`, stores `conversation_id`
- Subsequent turns call `conversations.append(conversation_id=...)`
- All 3 reasoners (Rover, Drone, Station) maintain their own `conversation_id`
- On simulation reset, `conversation_id` is cleared for fresh threads

### US2 (P1): Training Logger Integration
**As a** training data analyst, **I want** Agents API turns to be logged via `training_logger.log_turn()`, **so that** training data is captured regardless of which backend is active.

**Acceptance Criteria**:
- Remove `# TODO: integrate training logger` comment
- Agents API loop classes log `TrainingTurn` records identically to chat_completions loops
- Training snapshots are logged at the same intervals

### US3 (P2): Config Toggle for Thread Persistence
**As a** developer, **I want** a config option to toggle thread persistence, **so that** I can disable it for debugging or cost control.

**Acceptance Criteria**:
- `agents_api_persist_threads: bool = True` in Settings
- When False, every turn calls `conversations.start()` (current behavior)
- When True, threads are persisted across turns

## Scope

### In Scope
- Store `_conversation_id` per reasoner instance
- Switch from `start()` to `append()` on subsequent turns
- Wire training_logger into Agents API loop classes
- Config toggle for thread persistence
- Tests for thread persistence and training logger

### Out of Scope
- Conversation history inspection/export
- Thread cleanup (deleting old conversations on Mistral servers)
- Streaming variants (`start_stream`, `append_stream`)
- Agent re-creation on instruction changes

## Files Affected
- `server/app/agents_api.py` — conversation_id storage, start/append logic
- `server/app/config.py` — agents_api_persist_threads setting
- `server/app/agent.py` — training logger in Agents API loop classes
