# Feature Specification: Update ROADMAP.md Checkboxes

**Feature Branch**: `074-roadmap-update`  
**Created**: 2026-03-01  
**Status**: Draft  
**Input**: GitHub Issue #74 — ROADMAP.md checkboxes out of date

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reflect Current Implementation State (Priority: P1)

As a developer reading the roadmap, I want the checkboxes to accurately reflect what has been implemented, so I can quickly see project progress and remaining work.

**Why this priority**: Inaccurate roadmap creates confusion about project status.

**Independent Test**: Compare each checkbox against actual codebase. All checked items should have corresponding implementations.

**Acceptance Scenarios**:

1. **Given** protocol.py and base_agent.py exist, **When** M0 checkboxes are updated, **Then** those items show `[x]`
2. **Given** DroneReasoner exists with scan/map tools, **When** M3 checkboxes are updated, **Then** drone items show `[x]`
3. **Given** narrator.py with ElevenLabs TTS exists, **When** Voice stretch is updated, **Then** TTS item shows `[x]`
4. **Given** Python 3.14+ and uv are used, **When** Dependencies are updated, **Then** table reflects current versions

### Edge Cases

- Only mark items that are genuinely implemented
- Dependencies section uses table format — edit in-place

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: M0 protocol types and BaseAgent items MUST be checked
- **FR-002**: M3 drone agent, drone tools, all-agents-active items MUST be checked
- **FR-003**: Voice stretch TTS item MUST be checked
- **FR-004**: Dependencies MUST show Python 3.14+ and `uv sync`

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 8 specified checkbox/text changes applied to ROADMAP.md
