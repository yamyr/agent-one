export const GRID_SIZE = 20
export const TILE_SIZE = 20
export const VIEWPORT_W = 20
export const VIEWPORT_H = 20

export const ROVER_REVEAL_RADIUS = 3
export const DRONE_REVEAL_RADIUS = 6
export const REVEAL_RADIUS = ROVER_REVEAL_RADIUS  // legacy alias

export const VEIN_COLORS = {
  'pristine': '#e6c619',
  'rich': '#c4a012',
  'high': '#d4760a',
  'medium': '#8a8a8a',
  'low': '#5a5a5a',
  'unknown': '#4a4a6a',
}

export const VEIN_SIZES = {
  'pristine': 14,
  'rich': 12,
  'high': 10,
  'medium': 8,
  'low': 6,
  'unknown': 6,
}

export const AGENT_COLORS = {
  'station': '#44cc88',
  'rover-mistral': '#e06030',
  'drone-mistral': '#cc44cc',
}

export const SOLAR_PANEL_COLOR = '#f0c040'
export const SOLAR_PANEL_DEPLETED_COLOR = '#555555'

export function agentColor(id) {
  return AGENT_COLORS[id] || '#6c6'
}

export function revealRadius(id) {
  if (id && id.startsWith('drone')) return DRONE_REVEAL_RADIUS
  return ROVER_REVEAL_RADIUS
}

export function formatMoveEvent(payload) {
  const f = payload.from
  const t = payload.to
  return `(${f[0]},${f[1]}) \u2192 (${t[0]},${t[1]})`
}
