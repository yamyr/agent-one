export const GRID_SIZE = 20
export const TILE_SIZE = 20
export const VIEWPORT_W = 20
export const VIEWPORT_H = 20
export const MAP_W = VIEWPORT_W * TILE_SIZE
export const MAP_H = VIEWPORT_H * TILE_SIZE

export const ROVER_REVEAL_RADIUS = 3
export const DRONE_REVEAL_RADIUS = 6
export const REVEAL_RADIUS = ROVER_REVEAL_RADIUS  // legacy alias

export const STONE_COLORS = {
  'core': '#b8962a',
  'basalt': '#666666',
  'unknown': '#4a4a6a',
}

export const SOLAR_PANEL_COLOR = '#f0c040'
export const SOLAR_PANEL_DEPLETED_COLOR = '#555555'

export const AGENT_COLORS = {
  'station': '#44cc88',
  'rover-mock': '#6688cc',
  'rover-mistral': '#e06030',
  'drone-mistral': '#cc44cc',
}

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
