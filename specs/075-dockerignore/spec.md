# Feature Specification: Add .dockerignore

**Feature Branch**: `075-dockerignore`  
**Created**: 2026-03-01  
**Status**: Draft  
**Input**: GitHub Issue #75 — add .dockerignore for optimized Docker builds

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reduce Docker Build Context (Priority: P1)

As a developer building Docker images, I want unnecessary files excluded from the build context so that builds are faster and images are smaller.

**Why this priority**: Without `.dockerignore`, the entire repo (including `.git`, `node_modules`, tests, specs, IDE files) is sent to the Docker daemon, slowing builds and bloating layers.

**Independent Test**: Create `.dockerignore` at repo root with standard exclusions. Optionally verify with `docker build`.

**Acceptance Scenarios**:

1. **Given** no `.dockerignore` exists, **When** I create one with standard entries, **Then** Docker build context excludes `.git`, `node_modules`, `__pycache__`, etc.
2. **Given** `.dockerignore` exists, **When** I run `docker build`, **Then** build succeeds without unnecessary files in context

### Edge Cases

- `README.md` must NOT be ignored (negation rule `!README.md`)
- `.env` files must be ignored to prevent secrets leaking into images

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `.dockerignore` MUST exist at repo root
- **FR-002**: `.dockerignore` MUST exclude: `.git`, `.env*`, `__pycache__`, `node_modules`, `.vite`, `dist`, IDE files, tests, specs, docs (except README.md)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `.dockerignore` file exists at repo root with all specified entries
- **SC-002**: `README.md` is not excluded (negation rule)
