# Research: Rover Peer-to-Peer Messaging

**Feature**: Rover Peer-to-Peer Messaging
**Date**: 2026-03-06
**Branch**: `185-rover-peer-messaging`

---

## R1: Can rovers already receive messages?

**Decision**: Yes — the infrastructure already exists. `get_unread_messages(agent_id)` at world.py:958 works for any agent. Rover `_build_context()` at agent.py:811 already renders incoming messages in an "INCOMING MESSAGES" section. No changes needed on the receiving side.

**Rationale**: The message system was designed generically. `send_agent_message(from_id, to_id, message)` appends to a global `AGENT_MESSAGES` list with no type restrictions. The rover prompt already displays incoming messages. Only the sending tool is missing.

**Alternatives Considered**:
- **New inbox system**: Rejected. Existing AGENT_MESSAGES list works perfectly.
- **Separate peer inbox**: Rejected. Over-engineering — one inbox handles all message types.

---

## R2: How should notify_peer be implemented?

**Decision**: Add a new `notify_peer` action that calls `send_agent_message()` and broadcasts a WebSocket event. Implement as `_execute_notify_peer()` in world.py, with tool definition and tick handling in agent.py.

**Rationale**: Follows the exact same pattern as `notify` (tool definition → execute_action dispatch → _execute_X function → tick handler broadcasts event). The only difference: notify saves to station memory; notify_peer calls send_agent_message() to deliver to target's inbox.

**Alternatives Considered**:
- **Extend existing notify tool with optional target**: Rejected. Muddies the semantics — notify is station-specific, peer messaging is conceptually different.
- **Use send_agent_message() directly without a tool**: Rejected. Rovers need an LLM-callable tool to trigger messaging.

---

## R3: What battery cost for peer messaging?

**Decision**: Same as `notify` — `BATTERY_COST_NOTIFY` (2 fuel units, ~0.57% battery). Reuse the existing constant.

**Rationale**: Radio transmission cost should be consistent regardless of target. Creating a separate cost constant adds complexity for no benefit. The prompt already explains the cost.

**Alternatives Considered**:
- **Free (no battery cost)**: Rejected. Would encourage message spam, unrealistic.
- **Distance-based cost**: Rejected. Over-engineering for a hackathon project.
- **Higher cost than notify**: Rejected. No physical justification — radio is radio.

---

## R4: How should the UI visualize peer messages?

**Decision**: Add `peer_message` to the existing `COMM_COLORS` map in WorldMap.vue with a new color (e.g., `#cc44cc` — magenta/purple) and handle the event in the existing watcher. No structural changes needed.

**Rationale**: The communication line system already handles arbitrary event types via `addCommLine(source, target, color)`. Adding a new event name + color is a 3-line change. Purple/magenta distinguishes peer messages from existing blue (notify), cyan (relay), orange (command), red (alert).

**Alternatives Considered**:
- **Reuse notify color (blue)**: Rejected. Loses visual distinction between station-bound and peer messages.
- **Animated particle system**: Rejected. Over-engineering — existing dashed line + dot is sufficient.
- **Persistent lines**: Rejected. Existing 3-second fade is the right UX.

---

## R5: What validation should notify_peer enforce?

**Decision**: Validate that (1) target_id exists in world agents, (2) target is not the sender, (3) target is a rover type (not station or drone). Return error dict if validation fails.

**Rationale**: Prevents nonsensical messages (self-messaging, messaging non-existent agents). Station has its own communication tools. Drone-to-rover messaging is out of scope.

**Alternatives Considered**:
- **No validation (send to anyone)**: Rejected. Would let rovers message station (duplicating notify) or themselves.
- **Proximity-based restriction**: Rejected. Radio works at any distance in the simulation.
- **Allow drone targets**: Rejected. Out of scope per spec. Can be added later.

---

## R6: How should peer rover IDs be surfaced in the prompt?

**Decision**: Add a "PEER COMMUNICATION" section to `_build_context()` that lists other active rover agent IDs and encourages coordination. Place after the existing RADIO section.

**Rationale**: The LLM needs to know valid target IDs to call `notify_peer(target_id, message)`. Listing peers in the prompt enables the model to choose the right target. Encouraging specific use cases (share discoveries, warn about hazards, coordinate sectors) guides emergent behavior.

**Alternatives Considered**:
- **Include in tool description only**: Rejected. Tool description is static; rover IDs are dynamic.
- **Separate observation model field**: Rejected. Prompt section is simpler and consistent with existing patterns (RADIO, HAZARDS, etc.).
