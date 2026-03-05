# Feature 187: SPEC.md and README.md Refresh for v0.8.0

## Problem Statement

SPEC.md and README.md are severely outdated (~32% and ~40% coverage respectively). Multiple features added since v0.6.0 are undocumented: Agents API backend, goal confidence tracking, human-in-the-loop, peer messaging, hauler agent, narrator system, training data pipeline, storm system, upgrade system, and gas collection.

## User Stories

### US1 (P1): SPEC.md Refresh

**As a** developer joining the project,
**I want** SPEC.md to comprehensively document all simulation features,
**so that** I can understand the system architecture and capabilities without reading source code.

**Acceptance Criteria:**
- All 11 feature areas documented (agents API, goal confidence, human-in-the-loop, peer messaging, hauler, narrator, training pipeline, storms, drone enhancements, upgrades, gas collection)
- Tool tables updated with all current rover/drone/station/hauler tools
- World model section updated with ice, gas, geysers, structures, obstacles
- Configuration section documenting all `Settings` fields
- Agent loop section updated with training data recording and goal confidence

### US2 (P1): README.md Refresh

**As a** new user or contributor,
**I want** README.md to provide accurate getting-started information and architecture overview,
**so that** I can set up and understand the project quickly.

**Acceptance Criteria:**
- Architecture diagram updated with narrator, training pipeline, hauler, voice command
- Agent descriptions updated with new capabilities
- Configuration table includes all environment variables
- API endpoints listed
- Project structure reflects current file layout

## Non-Goals

- No code changes (docs only)
- No new features or tests
- No UI documentation (beyond what README already covers)

## Technical Approach

1. Read current source files to verify feature implementations
2. Update SPEC.md sections in-place, adding new sections as needed
3. Update README.md with current architecture and configuration
4. Verify accuracy against source code
