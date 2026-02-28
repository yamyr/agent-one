# Round 3 — Phase 2 & Zoom Fix

## Task A: Fix Zoom-Out Tile Scaling
- [x] Make visible tile count dynamic based on zoom level
- [x] When zoomed out, render more tiles proportionally (`ceil(VIEWPORT_W / zoom)`)
- [x] Update camera centering, follow, pan, fog, and visibility checks for dynamic tile count
- [x] Update MiniMap viewport box to reflect actual visible tile count
- [x] Zoom re-centering on zoom change (center stays stable)
- [x] MiniMap navigation uses navigateTo() to prevent rubber-banding
- [x] Removed dead MAP_W/MAP_H constants

## Task B: EventLog Virtualization (Round 3 Phase 2)
- [x] Implement virtual scrolling for EventLog — only render visible events
- [x] Calculate visible window from scroll offset + container height
- [x] Use spacer elements (top/bottom) to maintain correct scrollbar behavior
- [x] Preserve enter transition for new events at top (UID-based, works at 200 cap)
- [x] Maintain auto-scroll to top behavior
- [x] Ensure accessibility (ARIA live region still works)
- [x] CSS containment for paint optimization

## Verification
- [x] Build passes (vite build)
- [x] Code review: all critical/warning issues fixed
- [x] Update Changelog.md
- [ ] Create PR and merge to main
