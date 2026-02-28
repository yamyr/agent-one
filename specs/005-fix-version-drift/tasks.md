# Tasks: Fix Version Drift

**Input**: Design documents from `/specs/005-fix-version-drift/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Not requested for this fix.

**Organization**: Single user story — one-line version string correction.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No setup required — existing project, single file change.

*(No tasks)*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational work needed.

*(No tasks)*

---

## Phase 3: User Story 1 - Version Consistency (Priority: P1) 🎯 MVP

**Goal**: Sync FastAPI app version in `server/app/main.py` to match `server/pyproject.toml` (`0.2.0`).

**Independent Test**: Check that `server/app/main.py` line 62 reads `version="0.2.0"` and the OpenAPI schema reports `0.2.0`.

### Implementation for User Story 1

- [x] T001 [US1] Change `version="0.1.0"` to `version="0.2.0"` in `server/app/main.py` line 62

**Checkpoint**: Version string matches `pyproject.toml`. OpenAPI schema reports `0.2.0`.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Changelog and documentation updates.

- [x] T002 [P] Update `Changelog.md` with version drift fix entry
- [x] T003 Verify existing tests still pass after the change

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 3 (US1)**: No dependencies — can start immediately
- **Phase 4 (Polish)**: Depends on T001 completion

### Parallel Opportunities

- T002 (Changelog) can run in parallel with T001 since they touch different files

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete T001: Fix version string
2. **VALIDATE**: Confirm `main.py` version matches `pyproject.toml`
3. Complete T002: Update Changelog
4. Complete T003: Run tests
5. Commit and create PR

---

## Notes

- Single-line fix: `version="0.1.0"` → `version="0.2.0"` in `server/app/main.py`
- `server/pyproject.toml` is NOT modified — it's already correct
- Total tasks: 3
- Task count per user story: US1=1, Polish=2
