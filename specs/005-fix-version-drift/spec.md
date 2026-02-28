# Feature Specification: Fix Version Drift

**Feature Branch**: `005-fix-version-drift`  
**Created**: 2026-02-28  
**Status**: Draft  
**Input**: User description: "Fix version drift: main.py hardcodes version 0.1.0 while pyproject.toml declares 0.2.0. Sync the FastAPI app version to match the package version."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Version Consistency Across Package Metadata (Priority: P1)

As a developer or API consumer, I want the FastAPI application's reported version to match the version declared in `pyproject.toml`, so that health checks, API docs, and package metadata all report the same version number.

**Why this priority**: Version drift causes confusion in debugging, deployment verification, and API documentation. A mismatch between the package version and runtime version undermines trust in the release process.

**Independent Test**: Verify that the version string in `server/app/main.py` (FastAPI constructor) exactly matches the `version` field in `server/pyproject.toml`. The `/docs` endpoint and OpenAPI schema should report version `0.2.0`.

**Acceptance Scenarios**:

1. **Given** the FastAPI app is running, **When** a user accesses the OpenAPI schema (`/openapi.json`), **Then** the `info.version` field reads `0.2.0`.
2. **Given** `server/pyproject.toml` declares `version = "0.2.0"`, **When** a developer inspects `server/app/main.py`, **Then** the `version` parameter in `FastAPI(...)` also reads `"0.2.0"`.

---

### Edge Cases

- If `pyproject.toml` version changes in the future, the same drift could recur. Consider a single source of truth for version in a follow-up task (out of scope for this fix).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The FastAPI application MUST declare `version="0.2.0"` in its constructor to match the package version in `pyproject.toml`.
- **FR-002**: No other files or configuration MUST be modified — `pyproject.toml` is the source of truth and is already correct at `0.2.0`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The version string reported by the FastAPI app (`/openapi.json` → `info.version`) matches the version in `pyproject.toml` (`0.2.0`).
- **SC-002**: No regressions — existing tests continue to pass after the change.

## Assumptions

- `server/pyproject.toml` at `version = "0.2.0"` is the canonical source of truth.
- This is a one-line fix: changing `version="0.1.0"` to `version="0.2.0"` in `server/app/main.py`.
- Future version management (e.g., reading version from `pyproject.toml` at runtime) is out of scope.
