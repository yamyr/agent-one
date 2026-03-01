# Data Model: UI Polish Round 3

**Feature**: `004-ui-polish-round3`
**Date**: 2026-02-28

## Entities

### UIPreferences (localStorage)

Persisted client-side via `usePreferences.js` composable.

| Field | Type | Default | Storage Key |
|-------|------|---------|-------------|
| version | number | 1 | `mars_prefs_version` |
| zoom | number | 1.0 | `mars_zoom` |
| followAgent | string \| null | null | `mars_follow` |
| narrationEnabled | boolean | true | `mars_narration` |

**Validation Rules**:
- `zoom`: clamp to [ZOOM_MIN, ZOOM_MAX] on load (currently 0.7–2.2)
- `followAgent`: validate against `agentIds` on session start; reset to null if not found
- `narrationEnabled`: coerce to boolean
- If `version` doesn't match current, reset all preferences to defaults

**State Transitions**: None — flat key-value store, no lifecycle.

---

### ToastItem (in-memory)

Managed by `useToasts.js` composable.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| id | number | auto-increment | Unique toast identifier |
| message | string | required | Display text |
| type | 'info' \| 'success' \| 'warning' \| 'error' | 'info' | Visual style |
| count | number | 1 | Dedup counter (incremented on repeat) |
| createdAt | number | Date.now() | Timestamp for dedup window |
| timerId | number \| null | null | setTimeout ID for auto-dismiss |

**Validation Rules**:
- `message` must be non-empty string
- `count` ≥ 1
- Dedup window: 5000ms from `createdAt`

**State Transitions**:
1. **Created** → visible, timer starts
2. **Duplicated** → count incremented, timer reset
3. **Dismissed** → removed from array (manual or auto)

---

### KeyboardShortcut (static)

Used for help overlay rendering. Defined as a constant array.

| Field | Type | Description |
|-------|------|-------------|
| keys | string[] | Key labels (e.g., ['Space'], ['W', '↑']) |
| description | string | Human-readable action description |
| group | string | Category ('General', 'Camera', 'Agents') |

**Data** (static, no persistence):

| Group | Keys | Description |
|-------|------|-------------|
| General | Space | Toggle pause/resume |
| General | Escape | Close modal/overlay |
| General | ? | Show keyboard shortcuts |
| Camera | W / ↑ | Pan camera up |
| Camera | S / ↓ | Pan camera down |
| Camera | A / ← | Pan camera left |
| Camera | D / → | Pan camera right |
| Agents | 0 | Free camera mode |
| Agents | 1–9 | Follow agent by index |

---

### MiniMapLegendEntry (static)

Used for legend rendering. Derived from existing constants.

| Field | Type | Source |
|-------|------|--------|
| label | string | 'Rover', 'Drone', 'Station' or grade name |
| color | string | From `AGENT_COLORS` or `VEIN_COLORS` constants |
| shape | 'circle' \| 'triangle' \| 'square' \| 'diamond' | Matches WorldMap marker shapes |

## Relationships

```
App.vue
  ├── uses usePreferences() → reads/writes localStorage
  ├── uses useToasts() → manages ToastItem[]
  ├── renders KeyboardHelp.vue → reads SHORTCUTS constant
  └── passes preferences to WorldMap (zoom), MiniMap (legend data)

usePreferences.js
  └── reads/writes localStorage keys

useToasts.js
  └── manages ToastItem[] with dedup logic

MiniMap.vue
  └── renders MiniMapLegendEntry[] from constants
```
