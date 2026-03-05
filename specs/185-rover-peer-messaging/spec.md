# Feature Specification: Rover Peer-to-Peer Messaging

**Branch**: `185-rover-peer-messaging`
**Date**: 2026-03-06
**Status**: Messaging infrastructure exists but only station → rover is used; rovers lack a tool to message peers

---

## Problem Statement

The Agents API and multi-agent coordination is the core thesis. Rovers currently can only notify the station — they cannot share discoveries, coordinate routes, or warn each other directly. Adding peer-to-peer messaging would produce emergent collaborative behavior that is visually compelling and architecturally meaningful.

## User Stories

### US1 (P1): Rover Peer-to-Peer Messaging Tool
**As a** rover agent, **I want** to send messages directly to other rovers, **so that** I can share discoveries, coordinate exploration, and avoid duplication.

**Acceptance Criteria**:
- New `notify_peer` tool available to all rovers: `notify_peer(target_id, message)`
- Tool costs same battery as `notify` (BATTERY_COST_NOTIFY)
- Message is delivered via `send_agent_message()` to target's inbox
- Target rover sees the message in its next observation cycle (INCOMING MESSAGES section)
- Tool validates target_id exists and is a rover (not station, not self)
- Broadcast a WebSocket event `name="peer_message"` with `{source, target, message}` for UI

### US2 (P1): Rover Prompt Encourages Peer Coordination
**As a** simulation operator, **I want** the rover system prompt to encourage peer coordination, **so that** rovers naturally share discoveries and collaborate.

**Acceptance Criteria**:
- Add PEER COMMUNICATION section to rover system prompt in `_build_context()`
- Guide LLM on when to use `notify_peer`: found rich vein, heading to known hotspot, low battery warning to nearby rover, area already cleared
- List available peer rover IDs in the prompt context
- Existing INCOMING MESSAGES section already handles display (no changes needed)

### US3 (P2): UI Communication Lines for Peer Messages
**As a** viewer, **I want** to see communication lines between rovers when they send peer messages, **so that** the collaborative behavior is visually apparent.

**Acceptance Criteria**:
- WorldMap.vue handles `name="peer_message"` events
- Draws a communication line between source and target rover
- New color for peer messages (distinct from existing relay/command/alert/notify colors)
- Line uses existing animation system (dashed line + traveling dot, 3s fade)

## Scope

### In Scope
- `notify_peer` rover tool with battery cost and validation
- WebSocket event broadcast for peer messages
- Rover prompt update with peer coordination guidance
- Peer rover IDs in observation context
- UI communication line for peer messages
- Tests for tool execution, message delivery, and prompt content

### Out of Scope
- Drone-to-drone or drone-to-rover messaging
- Message history UI panel
- Message prioritization or filtering
- Encrypted or private messages
- Message acknowledgment/receipt system

## Files Affected
- `server/app/world.py` — `_execute_notify_peer()` action handler
- `server/app/agent.py` — `NOTIFY_PEER_TOOL` definition, prompt update, tick handler
- `ui/src/components/WorldMap.vue` — peer_message event handling + comm line color
