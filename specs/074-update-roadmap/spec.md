# Feature Specification: Update ROADMAP.md Checkboxes

**Feature Branch**: `074-update-roadmap`  
**Created**: 2026-03-01  
**Status**: Complete  
**Input**: GitHub Issue #74 — ROADMAP.md milestone checkboxes are severely outdated

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Accurate Milestone Tracking (Priority: P1)

As a developer reading the roadmap, I want the checkboxes to accurately reflect what has been implemented, so I can quickly see project progress and remaining work.

**Why this priority**: Inaccurate roadmap creates confusion about project status and wastes time investigating what's actually done.

**Independent Test**: Compare each checkbox against actual codebase files. All checked items must have corresponding implementations.

**Acceptance Scenarios**:

1. **Given** `protocol.py` and `base_agent.py` exist, **When** viewing M0, **Then** both items show `[x]`
2. **Given** `DroneAgent` class exists with scan/move tools, **When** viewing M3, **Then** all drone items show `[x]`
3. **Given** `_best_drone_hotspot()` pipes scan data to rover, **When** viewing M3 action piping, **Then** items 48-50 show `[x]`
4. **Given** `narrator.py` with ElevenLabs TTS exists, **When** viewing Voice stretch, **Then** TTS item shows `[x]`
5. **Given** Python 3.14+ and `uv sync` are used, **When** viewing Dependencies, **Then** table reflects current tooling

### Edge Cases

- Only mark items that are verifiably implemented in the codebase
- Drone tool names must match actual implementation (`scan`, `move`), not spec placeholders (`scan_area`, `map_route`)
- Dependencies table uses Markdown table format — edit in-place, preserve alignment

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: M0 protocol types and BaseAgent checkbox items MUST be checked
- **FR-002**: M3 drone agent, drone tools (corrected names), action piping, and all-agents-active items MUST be checked
- **FR-003**: Voice stretch TTS item MUST be checked
- **FR-004**: Dependencies table MUST show `Python 3.14+ | uv sync` and `mistralai SDK | uv sync`
- **FR-005**: Drone tool names MUST be corrected from `scan_area(zones)`, `map_route(from, to)` to `scan` (concentration map), `move` (tile navigation)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 11 checkbox/text changes applied to ROADMAP.md and verified against codebase
- **SC-002**: Changelog.md updated with documentation entry under [Unreleased]
- **SC-003**: PR passes review with no inaccurate checkbox states
