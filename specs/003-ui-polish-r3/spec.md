# Feature Specification: UI Polish Round 3 (UX, Perf, Accessibility)

**Feature Branch**: `feature/ui-polish-r3`
**Status**: Active
**Goal**: Refine user experience, improve rendering performance under load, and maximize accessibility.

## Scope

### Phase 1: Accessibility Baseline (Completed)
- ARIA roles/labels, focus-visible, reduced-motion.
- **Added bonus**: Rover carried-ore visuals.

### Phase 2: EventLog Virtualization (Completed)
- **Problem**: Long-running simulations generate thousands of DOM nodes in the EventLog.
- **Solution**: Windowing implemented in `EventLog.vue` (dynamic slicing).
- **Status**: Merged in `9e7647f`.

### Phase 3: MiniMap Legends (UX)
- **Problem**: Users may not know what dot colors mean.
- **Solution**: Collapsible legend overlay on MiniMap showing Agents (colors) and Veins (grades).

### Phase 4: Camera Inertia Tuning (UX)
- **Problem**: Linear lerp feels robotic.
- **Solution**: Adaptive lerp speed — fast when far, slow when close.

### Phase 5: Toast Deduplication (UX)
- **Problem**: Spammy events flood the toast stack.
- **Solution**: `useToasts` checks for duplicates.

### Phase 6: Loading Skeletons (UX)
- **Problem**: UI looks broken before WebSocket connects.
- **Solution**: Skeleton loaders.

### Phase 7: Persisted UI Preferences (UX)
- **Problem**: Refreshing resets state.
- **Solution**: `localStorage` hook.

### Phase 8: Command Palette / Help (UX)
- **Problem**: Hidden keyboard shortcuts.
- **Solution**: Help overlay.
