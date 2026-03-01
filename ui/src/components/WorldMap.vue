<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { TILE_SIZE, VIEWPORT_W, VIEWPORT_H, VEIN_COLORS, VEIN_SIZES, SOLAR_PANEL_COLOR, SOLAR_PANEL_DEPLETED_COLOR, STRUCTURE_COLORS, STRUCTURE_LABELS, OBSTACLE_COLORS, agentColor, revealRadius } from '../constants.js'
import { usePreferences } from '../composables/usePreferences.js'
import { useRevealedSet } from '../composables/useRevealedSet.js'

const props = defineProps({
  worldState: {
    type: Object,
    default: null,
  },
  agentIds: {
    type: Array,
    default: () => [],
  },
  followAgent: {
    type: String,
    default: null,
  },
  events: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['select-agent', 'unfollow'])

// Camera state: top-left tile of viewport
const camX = ref(-Math.floor(VIEWPORT_W / 2))
const camY = ref(-Math.floor(VIEWPORT_H / 2))

// Smooth camera: targets that camX/camY interpolate toward
const targetCamX = ref(camX.value)
const targetCamY = ref(camY.value)
let rafId = null
const { prefs } = usePreferences()
const ZOOM_MIN = 0.7
const ZOOM_MAX = 2.2
const ZOOM_STEP = 0.1

// Communication line system
const commLines = ref([])
const COMM_LINE_DURATION = 3000
const COMM_COLORS = {
  relay: '#44ccaa',
  command: '#cc8844',
  alert: '#cc4444',
  notify: '#4488cc',
}
let commRafId = null
let lastEventCount = 0

function getAgentScreenPos(agentId) {
  if (!props.worldState) return null
  const a = props.worldState.agents?.[agentId]
  if (!a) return null
  return worldToScreen(a.position[0], a.position[1])
}

function addCommLine(fromAgent, toAgent, type = 'relay') {
  const fromPos = getAgentScreenPos(fromAgent)
  const toPos = toAgent ? getAgentScreenPos(toAgent) : null
  if (!fromPos) return
  if (toAgent && !toPos) return

  if (!toAgent) {
    // Broadcast: draw lines to all other agents
    for (const id of props.agentIds) {
      if (id === fromAgent) continue
      const pos = getAgentScreenPos(id)
      if (!pos) continue
      commLines.value.push({
        fromAgent,
        toAgent: id,
        color: COMM_COLORS[type] || '#888',
        opacity: 1.0,
        createdAt: Date.now(),
        type,
      })
    }
    return
  }

  commLines.value.push({
    fromAgent,
    toAgent,
    color: COMM_COLORS[type] || '#888',
    opacity: 1.0,
    createdAt: Date.now(),
    type,
  })
}

function updateCommLines() {
  const now = Date.now()
  commLines.value = commLines.value
    .filter(line => now - line.createdAt < COMM_LINE_DURATION)
    .map(line => ({
      ...line,
      opacity: Math.max(0, 1 - (now - line.createdAt) / COMM_LINE_DURATION),
    }))
  commRafId = requestAnimationFrame(updateCommLines)
}

const visibleCommLines = computed(() => {
  if (!props.worldState) return []
  return commLines.value.map(line => {
    const from = getAgentScreenPos(line.fromAgent)
    const to = getAgentScreenPos(line.toAgent)
    if (!from || !to) return null
    return { ...line, fromSx: from.sx, fromSy: from.sy, toSx: to.sx, toSy: to.sy }
  }).filter(Boolean)
})

watch(() => props.events.length, (newLen) => {
  if (newLen <= lastEventCount) { lastEventCount = newLen; return }
  const newEvents = props.events.slice(lastEventCount)
  lastEventCount = newLen
  for (const ev of newEvents) {
    if (ev.name === 'intel_relay') {
      addCommLine(ev.source, ev.payload?.to, 'relay')
    } else if (ev.name === 'assign_mission') {
      addCommLine('station', ev.payload?.agent_id || ev.payload?.rover_id, 'command')
    } else if (ev.name === 'recall') {
      addCommLine('station', ev.payload?.rover_id, 'command')
    } else if (ev.name === 'notify') {
      addCommLine(ev.source, 'station', 'notify')
    } else if (ev.name === 'alert') {
      addCommLine(ev.source || 'station', null, 'alert')
    }
  }
})

// Dynamic viewport dimensions: more tiles when zoomed out, fewer when zoomed in
const visibleW = computed(() => Math.ceil(VIEWPORT_W / prefs.zoom))
const visibleH = computed(() => Math.ceil(VIEWPORT_H / prefs.zoom))
const dynamicMapW = computed(() => visibleW.value * TILE_SIZE)
const dynamicMapH = computed(() => visibleH.value * TILE_SIZE)

function cameraLoop() {
  const dx = targetCamX.value - camX.value
  const dy = targetCamY.value - camY.value
  const dist = Math.sqrt(dx * dx + dy * dy)

  if (dist > 0.01) {
    // Adaptive speed: slower start/end (0.1), faster when far (up to 0.3)
    const speed = Math.min(0.3, 0.1 + dist * 0.02)
    camX.value += dx * speed
    camY.value += dy * speed

    // Snap when very close
    if (Math.abs(dx) < 0.05) camX.value = targetCamX.value
    if (Math.abs(dy) < 0.05) camY.value = targetCamY.value
    rafId = requestAnimationFrame(cameraLoop)
  } else {
    rafId = null  // idle — stop consuming CPU until target changes
  }
}

// Start the loop once on mount; it will self-stop when idle
onMounted(() => {
  rafId = requestAnimationFrame(cameraLoop)
  commRafId = requestAnimationFrame(updateCommLines)
})
onUnmounted(() => {
  if (rafId) cancelAnimationFrame(rafId)
  if (commRafId) cancelAnimationFrame(commRafId)
})

// Restart the animation loop when the camera target moves and the loop is idle
function ensureCameraLoop() {
  if (!rafId) rafId = requestAnimationFrame(cameraLoop)
}

// Track drag state
const dragging = ref(false)
const dragStart = ref({ x: 0, y: 0 })

// Follow selected agent: update target (smooth interpolation via rAF)
watch([() => props.worldState, () => props.followAgent], () => {
  if (!props.worldState || !props.followAgent) return
  const a = props.worldState.agents?.[props.followAgent]
  if (a) {
    targetCamX.value = a.position[0] - Math.floor(visibleW.value / 2)
    targetCamY.value = a.position[1] - Math.floor(visibleH.value / 2)
    ensureCameraLoop()
  }
})

const tiles = computed(() => {
  const arr = []
  const vw = visibleW.value
  const vh = visibleH.value
  for (let dy = 0; dy < vh; dy++) {
    for (let dx = 0; dx < vw; dx++) {
      const x = Math.floor(camX.value) + dx
      const y = Math.floor(camY.value) + vh - 1 - dy  // flip Y for SVG
      arr.push({ x, y, sx: dx * TILE_SIZE, sy: dy * TILE_SIZE, key: `${x}-${y}` })
    }
  }
  return arr
})

const rovers = computed(() => {
  if (!props.agentIds) return []
  return props.agentIds.filter(id => {
    if (!props.worldState) return true
    const a = props.worldState.agents[id]
    return !a || a.type === 'rover'
  })
})

const drones = computed(() => {
  if (!props.agentIds) return []
  return props.agentIds.filter(id => {
    if (!props.worldState) return false
    const a = props.worldState.agents[id]
    return a && a.type === 'drone'
  })
})

const stations = computed(() => {
  if (!props.agentIds) return []
  return props.agentIds.filter(id => {
    if (!props.worldState) return false
    const a = props.worldState.agents[id]
    return a && a.type === 'station'
  })
})

const { isRevealed } = useRevealedSet(() => props.worldState)

// Grade weights for concentration radius (mirrors server logic)
const GRADE_ORDER = ['low', 'medium', 'high', 'rich', 'pristine']

// Pre-computed stone lookup: spatial hash for O(1) per-tile concentration
const SPATIAL_CELL = 20  // bucket size ≥ max influence radius (18)
const stoneIndex = computed(() => {
  const idx = new Map()  // key: 'cx,cy' → stone[]
  if (!props.worldState) return idx
  for (const s of (props.worldState.stones || [])) {
    const [sx, sy] = s.position
    const ck = `${Math.floor(sx / SPATIAL_CELL)},${Math.floor(sy / SPATIAL_CELL)}`
    let bucket = idx.get(ck)
    if (!bucket) { bucket = []; idx.set(ck, bucket) }
    bucket.push(s)
  }
  return idx
})

function tileConcentration(x, y) {
  const idx = stoneIndex.value
  if (idx.size === 0) return 0
  const cx = Math.floor(x / SPATIAL_CELL)
  const cy = Math.floor(y / SPATIAL_CELL)
  let max = 0
  // Check the 3×3 neighbourhood of spatial cells
  for (let dcx = -1; dcx <= 1; dcx++) {
    for (let dcy = -1; dcy <= 1; dcy++) {
      const bucket = idx.get(`${cx + dcx},${cy + dcy}`)
      if (!bucket) continue
      for (const s of bucket) {
        const [sx, sy] = s.position
        const d = Math.abs(x - sx) + Math.abs(y - sy)
        if (d === 0) return 1
        const gi = GRADE_ORDER.indexOf(s.grade !== 'unknown' ? s.grade : 'low')
        const radius = 10 + (gi >= 0 ? gi : 0) * 2
        const c = Math.max(0, 1 - d / radius)
        if (c > max) max = c
      }
    }
  }
  return max
}

function tileFill(t) {
  if (!isRevealed(t.x, t.y)) return null // CSS class handles unrevealed
  const c = tileConcentration(t.x, t.y)
  if (c <= 0.05) return null // use CSS default for near-zero
  // Interpolate from revealed base (#0e0e16) toward warm amber (#443010)
  const r = Math.round(14 + c * 54)  // 0e → 44
  const g = Math.round(14 + c * 34)  // 0e → 30
  const b = Math.round(22 + c * -6)  // 16 → 10
  return `rgb(${r},${g},${b})`
}

function worldToScreen(wx, wy) {
  const sx = (wx - camX.value) * TILE_SIZE + TILE_SIZE / 2
  const sy = (visibleH.value - 1 - (wy - camY.value)) * TILE_SIZE + TILE_SIZE / 2
  return { sx, sy }
}

function agentTransform(id) {
  if (!props.worldState) return ''
  const a = props.worldState.agents[id]
  if (!a) return ''
  const { sx, sy } = worldToScreen(a.position[0], a.position[1])
  return `translate(${sx}, ${sy})`
}

function isAgentVisible(id) {
  if (!props.worldState) return false
  const a = props.worldState.agents[id]
  if (!a) return false
  const [wx, wy] = a.position
  return wx >= camX.value && wx < camX.value + visibleW.value &&
         wy >= camY.value && wy < camY.value + visibleH.value
}

function isStoneVisible(s) {
  const [wx, wy] = s.position
  return wx >= camX.value && wx < camX.value + visibleW.value &&
         wy >= camY.value && wy < camY.value + visibleH.value
}

function veinGrade(s) {
  return s.grade || 'unknown'
}

function veinSize(s) {
  return VEIN_SIZES[veinGrade(s)] || 6
}

function stoneScreenX(s) {
  const half = veinSize(s) / 2
  return (s.position[0] - camX.value) * TILE_SIZE + TILE_SIZE / 2 - half
}

function stoneScreenY(s) {
  const half = veinSize(s) / 2
  return (visibleH.value - 1 - (s.position[1] - camY.value)) * TILE_SIZE + TILE_SIZE / 2 - half
}

function stoneRotateCenter(s) {
  const cx = (s.position[0] - camX.value) * TILE_SIZE + TILE_SIZE / 2
  const cy = (visibleH.value - 1 - (s.position[1] - camY.value)) * TILE_SIZE + TILE_SIZE / 2
  return `rotate(45, ${cx}, ${cy})`
}

function veinHasGlow(s) {
  const g = veinGrade(s)
  return g === 'rich' || g === 'pristine'
}

function isPanelVisible(p) {
  const [wx, wy] = p.position
  return wx >= camX.value && wx < camX.value + visibleW.value &&
         wy >= camY.value && wy < camY.value + visibleH.value
}

function panelScreenX(p) {
  return (p.position[0] - camX.value) * TILE_SIZE + 2
}

function panelScreenY(p) {
  return (visibleH.value - 1 - (p.position[1] - camY.value)) * TILE_SIZE + 2
}

// Obstacle rendering — pre-compute screen positions for efficiency
const visibleObstacles = computed(() => {
  if (!props.worldState) return []
  return (props.worldState.obstacles || [])
    .filter((o) => {
      const [wx, wy] = o.position
      return (
        wx >= camX.value &&
        wx < camX.value + visibleW.value &&
        wy >= camY.value &&
        wy < camY.value + visibleH.value
      )
    })
    .map((o) => {
      const { sx, sy } = worldToScreen(o.position[0], o.position[1])
      return { ...o, sx, sy }
    })
})

function obstacleColor(o) {
  if (o.kind === 'mountain') return OBSTACLE_COLORS.mountain
  if (o.kind === 'geyser') return OBSTACLE_COLORS['geyser_' + (o.state || 'idle')] || OBSTACLE_COLORS.geyser_idle
  return '#666'
}

function obstacleTooltip(o) {
  if (o.kind === 'mountain') return `Ice Mountain at (${o.position[0]}, ${o.position[1]}) — impassable`
  if (o.kind === 'geyser') return `Air Geyser at (${o.position[0]}, ${o.position[1]}) — ${o.state || 'idle'}`
  return `${o.kind} at (${o.position[0]}, ${o.position[1]})`
}

// Drag-to-pan
function onMouseDown(e) {
  dragging.value = true
  dragStart.value = { x: e.clientX, y: e.clientY }
}

function onMouseMove(e) {
  if (!dragging.value) return
  const dx = e.clientX - dragStart.value.x
  const dy = e.clientY - dragStart.value.y
  const svg = e.currentTarget
  const rect = svg.getBoundingClientRect()
  const tilePixelW = rect.width / visibleW.value
  const tilePixelH = rect.height / visibleH.value
  if (Math.abs(dx) >= tilePixelW) {
    const tileDx = Math.round(dx / tilePixelW)
    // Drag is instant — move both target and camera directly
    targetCamX.value -= tileDx
    camX.value = targetCamX.value
    dragStart.value.x = e.clientX
    emit('unfollow')
  }
  if (Math.abs(dy) >= tilePixelH) {
    const tileDy = Math.round(dy / tilePixelH)
    targetCamY.value += tileDy
    camY.value = targetCamY.value
    dragStart.value.y = e.clientY
    emit('unfollow')
  }
}

function onMouseUp() {
  dragging.value = false
}

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v))
}

function zoomIn() {
  prefs.zoom = clamp(Number((prefs.zoom + ZOOM_STEP).toFixed(2)), ZOOM_MIN, ZOOM_MAX)
}

function zoomOut() {
  prefs.zoom = clamp(Number((prefs.zoom - ZOOM_STEP).toFixed(2)), ZOOM_MIN, ZOOM_MAX)
}

function resetZoom() {
  prefs.zoom = 1
}

function onWheel(e) {
  e.preventDefault()
  if (e.deltaY < 0) zoomIn()
  else zoomOut()
}

// Re-center camera when zoom changes so the viewport expands/contracts around center
watch(() => prefs.zoom, (newZ, oldZ) => {
  const oldW = Math.ceil(VIEWPORT_W / oldZ)
  const oldH = Math.ceil(VIEWPORT_H / oldZ)
  const newW = Math.ceil(VIEWPORT_W / newZ)
  const newH = Math.ceil(VIEWPORT_H / newZ)
  const dx = Math.floor((oldW - newW) / 2)
  const dy = Math.floor((oldH - newH) / 2)
  targetCamX.value += dx
  targetCamY.value += dy
  camX.value = targetCamX.value
  camY.value = targetCamY.value
})

const mapViewBox = computed(() => {
  return `0 0 ${dynamicMapW.value} ${dynamicMapH.value}`
})

// Agent trail data: last N visited positions per mobile agent
const TRAIL_LENGTH = 20

const agentTrails = computed(() => {
  if (!props.worldState) return []
  const trails = []
  for (const id of props.agentIds) {
    const a = props.worldState.agents[id]
    if (!a || a.type === 'station') continue
    const visited = a.visited || []
    if (visited.length < 2) continue
    // Take last TRAIL_LENGTH positions (most recent at end)
    const recent = visited.slice(-TRAIL_LENGTH)
    trails.push({ id, positions: recent, color: agentColor(id) })
  }
  return trails
})

function trailSegments(trail) {
  const segs = []
  const positions = trail.positions
  const total = positions.length
  for (let i = 0; i < total - 1; i++) {
    const from = worldToScreen(positions[i][0], positions[i][1])
    const to = worldToScreen(positions[i + 1][0], positions[i + 1][1])
    // Opacity fades: oldest = 0.05, newest = 0.4
    const t = i / (total - 1)
    const opacity = 0.05 + t * 0.35
    segs.push({
      key: `${trail.id}-${i}`,
      x1: from.sx,
      y1: from.sy,
      x2: to.sx,
      y2: to.sy,
      opacity,
    })
  }
  return segs
}

// Tooltip helpers
function agentTooltip(id) {
  if (!props.worldState) return id
  const a = props.worldState.agents[id]
  if (!a) return id
  const pos = `(${a.position[0]}, ${a.position[1]})`
  const bat = Math.round((a.battery ?? 1) * 100)
  const type = a.type || 'rover'
  return `${id} [${type}]\nPosition: ${pos}\nBattery: ${bat}%\nTiles visited: ${(a.visited || []).length}`
}

function stoneTooltip(s) {
  const grade = s.grade || 'unknown'
  const qty = s.quantity ?? '?'
  const pos = `(${s.position[0]}, ${s.position[1]})`
  return `${grade.toUpperCase()} vein\nPosition: ${pos}\nQuantity: ${qty}`
}

function panelTooltip(p) {
  const pos = `(${p.position[0]}, ${p.position[1]})`
  return `Solar Panel ${p.depleted ? '(depleted)' : '(active)'}\nPosition: ${pos}`
}

function isStructureVisible(s) {
  const [wx, wy] = s.position
  return wx >= camX.value && wx < camX.value + visibleW.value &&
         wy >= camY.value && wy < camY.value + visibleH.value
}

function structureScreenX(s) {
  return (s.position[0] - camX.value) * TILE_SIZE + 2
}

function structureScreenY(s) {
  return (visibleH.value - 1 - (s.position[1] - camY.value)) * TILE_SIZE + 2
}

function structureTooltip(s) {
  const label = STRUCTURE_LABELS[s.type] || s.type
  const status = s.explored ? 'Explored' : 'Unexplored'
  const pos = `(${s.position[0]}, ${s.position[1]})`
  return `${label} (${status})\nPosition: ${pos}`
}

function structureColor(s) {
  const base = STRUCTURE_COLORS[s.type] || '#888888'
  return base
}

function structureOpacity(s) {
  return s.explored ? 0.85 : 0.45
}

function roverInventory(id) {
  if (!props.worldState) return []
  const a = props.worldState.agents[id]
  if (!a || a.type !== 'rover') return []
  return a.inventory || []
}

function carriedOreMarkers(id) {
  const inv = roverInventory(id)
  if (!inv.length) return []
  return inv.slice(0, 3).map((stone, i) => ({
    key: `${id}-ore-${i}`,
    x: 8 + i * 3.8,
    y: -7 + i * 1.8,
    color: VEIN_COLORS[stone.grade || 'unknown'] || VEIN_COLORS.unknown,
  }))
}

// Fog-of-war: compute screen positions for each mobile agent's clear zone
const fogAgents = computed(() => {
  if (!props.worldState) return []
  const agents = []
  for (const id of props.agentIds) {
    const a = props.worldState.agents[id]
    if (!a || a.type === 'station') continue
    const { sx, sy } = worldToScreen(a.position[0], a.position[1])
    const r = revealRadius(id) * TILE_SIZE
    agents.push({ id, cx: sx, cy: sy, r: r + TILE_SIZE }) // +1 tile feather
  }
  return agents
})

function panCamera(dx, dy) {
  targetCamX.value += dx
  targetCamY.value += dy
  ensureCameraLoop()
}

// Expose camera and dynamic viewport for minimap & keyboard shortcuts
function navigateTo(x, y) {
  targetCamX.value = x
  targetCamY.value = y
  camX.value = x
  camY.value = y
}

defineExpose({ camX, camY, visibleW, visibleH, panCamera, navigateTo })
</script>

<template>
  <section class="world-map">
    <h2>
      Surface Map
      <span
        v-if="followAgent"
        class="cam-hint"
      >(following {{ followAgent }})</span>
      <span
        v-else
        class="cam-hint"
      >(free camera · drag to pan)</span>
    </h2>
    <div class="map-controls">
      <button
        class="zoom-btn"
        title="Zoom out"
        type="button"
        aria-label="Zoom out map"
        @click="zoomOut"
      >
        −
      </button>
      <span class="zoom-label">{{ Math.round(prefs.zoom * 100) }}%</span>
      <button
        class="zoom-btn"
        title="Zoom in"
        type="button"
        aria-label="Zoom in map"
        @click="zoomIn"
      >
        +
      </button>
      <button
        class="zoom-btn reset"
        title="Reset zoom"
        type="button"
        aria-label="Reset map zoom"
        @click="resetZoom"
      >
        Reset
      </button>
    </div>
    <svg
      v-if="worldState"
      :viewBox="mapViewBox"
      class="map-svg"
      role="img"
      aria-label="Interactive world map. Drag or use keyboard arrows/WASD to pan, mouse wheel to zoom."
      @mousedown.prevent="onMouseDown"
      @mousemove="onMouseMove"
      @mouseup="onMouseUp"
      @mouseleave="onMouseUp"
      @wheel="onWheel"
    >
      <!-- grid tiles -->
      <rect
        v-for="t in tiles"
        :key="t.key"
        :x="t.sx"
        :y="t.sy"
        :width="TILE_SIZE"
        :height="TILE_SIZE"
        :class="isRevealed(t.x, t.y) ? 'grid-tile revealed' : 'grid-tile'"
        :fill="tileFill(t) || undefined"
      />

      <!-- SVG defs: filters, gradients, masks -->
      <defs>
        <filter
          id="vein-glow"
          x="-50%"
          y="-50%"
          width="200%"
          height="200%"
        >
          <feGaussianBlur
            in="SourceGraphic"
            stdDeviation="2"
            result="blur"
          />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        <!-- Fog-of-war: radial gradient for clear zones -->
        <radialGradient id="fog-clear-grad">
          <stop
            offset="0%"
            stop-color="black"
          />
          <stop
            offset="55%"
            stop-color="black"
          />
          <stop
            offset="100%"
            stop-color="black"
            stop-opacity="0"
          />
        </radialGradient>

        <!-- Fog mask: white = fog visible, agent circles punch soft holes -->
        <mask id="fog-mask">
          <rect
            x="0"
            y="0"
            :width="dynamicMapW"
            :height="dynamicMapH"
            fill="white"
          />
          <circle
            v-for="fa in fogAgents"
            :key="'fog-'+fa.id"
            :cx="fa.cx"
            :cy="fa.cy"
            :r="fa.r"
            fill="url(#fog-clear-grad)"
          />
        </mask>
      </defs>

      <!-- veins (stones) -->
      <template
        v-for="(s, i) in (worldState.stones || [])"
        :key="'stone-'+i"
      >
        <rect
          v-if="isStoneVisible(s)"
          :x="stoneScreenX(s)"
          :y="stoneScreenY(s)"
          :width="veinSize(s)"
          :height="veinSize(s)"
          :fill="VEIN_COLORS[veinGrade(s)] || 'var(--text-tertiary)'"
          :opacity="veinHasGlow(s) ? 0.95 : 0.85"
          :transform="stoneRotateCenter(s)"
          :filter="veinHasGlow(s) ? 'url(#vein-glow)' : undefined"
        >
          <title>{{ stoneTooltip(s) }}</title>
        </rect>
      </template>

      <!-- abandoned structures -->
      <template
        v-for="(s, i) in (worldState.structures || [])"
        :key="'struct-'+i"
      >
        <g v-if="isStructureVisible(s)">
          <title>{{ structureTooltip(s) }}</title>
          <!-- Buildings: sharp rectangles -->
          <rect
            v-if="s.category === 'building'"
            :x="structureScreenX(s)"
            :y="structureScreenY(s)"
            :width="TILE_SIZE - 4"
            :height="TILE_SIZE - 4"
            :fill="structureColor(s)"
            :opacity="structureOpacity(s)"
            rx="1"
            stroke="rgba(255,255,255,0.3)"
            stroke-width="0.5"
          />
          <!-- Vehicles: rounded shapes -->
          <rect
            v-else
            :x="structureScreenX(s)"
            :y="structureScreenY(s)"
            :width="TILE_SIZE - 4"
            :height="TILE_SIZE - 4"
            :fill="structureColor(s)"
            :opacity="structureOpacity(s)"
            rx="4"
            stroke="rgba(255,255,255,0.2)"
            stroke-width="0.5"
          />
          <!-- Unexplored indicator: ? mark -->
          <text
            v-if="!s.explored"
            :x="structureScreenX(s) + (TILE_SIZE - 4) / 2"
            :y="structureScreenY(s) + (TILE_SIZE - 4) / 2 + 3"
            text-anchor="middle"
            fill="rgba(255,255,255,0.6)"
            font-size="8"
            font-family="monospace"
          >?</text>
        </g>
      </template>
      <!-- obstacles (mountains + geysers) -->
      <template
        v-for="(o, i) in visibleObstacles"
        :key="'obs-' + i"
      >
        <!-- mountains: triangle -->
        <polygon
          v-if="o.kind === 'mountain'"
          :points="`${o.sx},${o.sy - 7} ${o.sx - 7},${o.sy + 5} ${o.sx + 7},${o.sy + 5}`"
          :fill="obstacleColor(o)"
          opacity="0.85"
        >
          <title>{{ obstacleTooltip(o) }}</title>
        </polygon>
        <!-- geysers: circle with animation when erupting -->
        <circle
          v-else-if="o.kind === 'geyser'"
          :cx="o.sx"
          :cy="o.sy"
          :r="o.state === 'erupting' ? 7 : o.state === 'warning' ? 5 : 4"
          :fill="obstacleColor(o)"
          :opacity="o.state === 'erupting' ? 0.95 : 0.7"
          :class="{ 'geyser-pulse': o.state === 'erupting' }"
        >
          <title>{{ obstacleTooltip(o) }}</title>
        </circle>
      </template>

      <!-- solar panels -->
      <template
        v-for="(p, i) in (worldState.solar_panels || [])"
        :key="'panel-'+i"
      >
        <g v-if="isPanelVisible(p)">
          <title>{{ panelTooltip(p) }}</title>
          <rect
            :x="panelScreenX(p)"
            :y="panelScreenY(p)"
            :width="TILE_SIZE - 4"
            :height="TILE_SIZE - 4"
            :fill="p.depleted ? SOLAR_PANEL_DEPLETED_COLOR : SOLAR_PANEL_COLOR"
            opacity="0.7"
            rx="1"
          />
          <line
            :x1="panelScreenX(p) + (TILE_SIZE - 4) / 2"
            :y1="panelScreenY(p)"
            :x2="panelScreenX(p) + (TILE_SIZE - 4) / 2"
            :y2="panelScreenY(p) + TILE_SIZE - 4"
            :stroke="p.depleted ? 'var(--text-dim)' : 'var(--accent-panel-stroke)'"
            stroke-width="0.5"
          />
          <line
            :x1="panelScreenX(p)"
            :y1="panelScreenY(p) + (TILE_SIZE - 4) / 2"
            :x2="panelScreenX(p) + TILE_SIZE - 4"
            :y2="panelScreenY(p) + (TILE_SIZE - 4) / 2"
            :stroke="p.depleted ? 'var(--text-dim)' : 'var(--accent-panel-stroke)'"
            stroke-width="0.5"
          />
        </g>
      </template>

      <!-- fog-of-war overlay -->
      <rect
        x="0"
        y="0"
        :width="dynamicMapW"
        :height="dynamicMapH"
        fill="var(--bg-primary)"
        opacity="0.6"
        mask="url(#fog-mask)"
        class="fog-overlay"
      />

      <!-- agent movement trails -->
      <template
        v-for="trail in agentTrails"
        :key="'trail-'+trail.id"
      >
        <line
          v-for="seg in trailSegments(trail)"
          :key="seg.key"
          :x1="seg.x1"
          :y1="seg.y1"
          :x2="seg.x2"
          :y2="seg.y2"
          :stroke="trail.color"
          :stroke-opacity="seg.opacity"
          stroke-width="1.5"
          stroke-linecap="round"
        />
      </template>

      <!-- communication lines between agents -->
      <g class="comm-lines">
        <line
          v-for="(line, i) in visibleCommLines"
          :key="'comm-'+i"
          :x1="line.fromSx"
          :y1="line.fromSy"
          :x2="line.toSx"
          :y2="line.toSy"
          :stroke="line.color"
          :stroke-opacity="line.opacity"
          stroke-width="1.5"
          stroke-dasharray="4 4"
          class="comm-line-animate"
        />
        <circle
          v-for="(line, i) in visibleCommLines"
          :key="'comm-dot-'+i"
          r="2.5"
          :fill="line.color"
          :opacity="line.opacity"
        >
          <animateMotion
            dur="0.8s"
            repeatCount="1"
            fill="freeze"
            :path="`M${line.fromSx},${line.fromSy} L${line.toSx},${line.toSy}`"
          />
        </circle>
      </g>

      <!-- station markers (square) -->
      <g
        v-for="id in stations"
        v-show="isAgentVisible(id)"
        :key="'station-'+id"
        :transform="agentTransform(id)"
        class="rover-group"
        style="cursor:pointer"
        @click="emit('select-agent', id)"
      >
        <title>{{ agentTooltip(id) }}</title>
        <rect
          x="-7"
          y="-7"
          width="14"
          height="14"
          rx="2"
          :fill="agentColor(id)"
          opacity="0.9"
        >
          <animate
            attributeName="width"
            values="14;16;14"
            dur="2s"
            repeatCount="indefinite"
          />
          <animate
            attributeName="height"
            values="14;16;14"
            dur="2s"
            repeatCount="indefinite"
          />
          <animate
            attributeName="x"
            values="-7;-8;-7"
            dur="2s"
            repeatCount="indefinite"
          />
          <animate
            attributeName="y"
            values="-7;-8;-7"
            dur="2s"
            repeatCount="indefinite"
          />
        </rect>
        <rect
          x="-12"
          y="-12"
          width="24"
          height="24"
          rx="3"
          fill="none"
          :stroke="agentColor(id)"
          stroke-width="1"
          opacity="0.25"
        >
          <animate
            attributeName="opacity"
            values="0.25;0.08;0.25"
            dur="2s"
            repeatCount="indefinite"
          />
        </rect>
        <text
          y="20"
          text-anchor="middle"
          :fill="agentColor(id)"
          class="rover-label"
        >{{ id }}</text>
      </g>

      <!-- rover dots (circle) -->
      <g
        v-for="id in rovers"
        v-show="isAgentVisible(id)"
        :key="'rover-'+id"
        :transform="agentTransform(id)"
        class="rover-group"
        style="cursor:pointer"
        @click="emit('select-agent', id)"
      >
        <title>{{ agentTooltip(id) }}</title>
        <circle
          r="7"
          :fill="agentColor(id)"
          opacity="0.9"
        >
          <animate
            attributeName="r"
            values="7;8;7"
            dur="2s"
            repeatCount="indefinite"
          />
        </circle>
        <rect
          v-for="m in carriedOreMarkers(id)"
          :key="m.key"
          :x="m.x"
          :y="m.y"
          width="3"
          height="3"
          :fill="m.color"
          stroke="var(--bg-primary)"
          stroke-width="0.4"
          transform="rotate(45)"
          class="ore-marker"
        />
        <circle
          r="12"
          fill="none"
          :stroke="agentColor(id)"
          stroke-width="1"
          opacity="0.25"
        >
          <animate
            attributeName="r"
            values="12;16;12"
            dur="2s"
            repeatCount="indefinite"
          />
          <animate
            attributeName="opacity"
            values="0.25;0.08;0.25"
            dur="2s"
            repeatCount="indefinite"
          />
        </circle>
        <!-- visibility radius -->
        <circle
          :r="revealRadius(id) * TILE_SIZE"
          fill="none"
          :stroke="agentColor(id)"
          stroke-width="1"
          opacity="0.3"
          stroke-dasharray="4 3"
        />
        <text
          y="18"
          text-anchor="middle"
          :fill="agentColor(id)"
          class="rover-label"
        >{{ id }}</text>
      </g>

      <!-- drone markers (triangle) -->
      <g
        v-for="id in drones"
        v-show="isAgentVisible(id)"
        :key="'drone-'+id"
        :transform="agentTransform(id)"
        class="rover-group"
        style="cursor:pointer"
        @click="emit('select-agent', id)"
      >
        <title>{{ agentTooltip(id) }}</title>
        <polygon
          points="0,-9 8,6 -8,6"
          :fill="agentColor(id)"
          opacity="0.9"
        >
          <animate
            attributeName="opacity"
            values="0.9;0.6;0.9"
            dur="1.5s"
            repeatCount="indefinite"
          />
        </polygon>
        <polygon
          points="0,-14 13,10 -13,10"
          fill="none"
          :stroke="agentColor(id)"
          stroke-width="1"
          opacity="0.25"
        >
          <animate
            attributeName="opacity"
            values="0.25;0.08;0.25"
            dur="1.5s"
            repeatCount="indefinite"
          />
        </polygon>
        <!-- visibility radius -->
        <circle
          :r="revealRadius(id) * TILE_SIZE"
          fill="none"
          :stroke="agentColor(id)"
          stroke-width="1"
          opacity="0.2"
          stroke-dasharray="6 4"
        />
        <text
          y="20"
          text-anchor="middle"
          :fill="agentColor(id)"
          class="rover-label"
        >{{ id }}</text>
      </g>
    </svg>
    <div
      v-else
      class="map-skeleton"
    >
      <div class="skeleton-grid">
        <div
          v-for="i in 100"
          :key="i"
          class="skeleton-tile"
        />
      </div>
      <div class="skeleton-message">
        Connecting to satellite feed...
      </div>
    </div>
  </section>
</template>

<style scoped>
.world-map {
  flex: 3;
  padding: 0.75rem;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  min-width: 0;
}

.map-svg {
  width: 100%;
  height: auto;
  display: block;
}

.grid-tile {
  fill: var(--bg-tile);
  stroke: var(--border-dim);
  stroke-width: 0.5;
}

.grid-tile.revealed {
  fill: var(--bg-revealed);
  stroke: var(--border-subtle);
}

.rover-group {
  transition: transform 0.4s ease;
}

.rover-label {
  font-family: var(--font-mono);
  font-size: 6px;
}

.ore-marker {
  opacity: 0.95;
}

@keyframes comm-dash {
  to { stroke-dashoffset: -8; }
}

.comm-line-animate {
  animation: comm-dash 0.6s linear infinite;
}

.cam-hint {
  font-size: 0.6rem;
  color: var(--text-dimmer);
  font-weight: normal;
  text-transform: none;
  letter-spacing: 0;
}

.map-controls {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  margin-bottom: 0.35rem;
}

.zoom-btn {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  padding: 0.12rem 0.35rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--text-muted);
  background: var(--bg-input);
  color: var(--text-secondary);
  cursor: pointer;
}

.zoom-btn:hover {
  border-color: var(--text-secondary);
  color: var(--text-primary);
}

.zoom-btn.reset {
  margin-left: 0.2rem;
}

.zoom-label {
  font-size: 0.65rem;
  color: var(--text-muted);
  min-width: 2.4rem;
  text-align: center;
}

.map-svg {
  cursor: grab;
}
.map-svg:active {
  cursor: grabbing;
}

.dust-particle {
  animation: dust-drift linear infinite;
}

@keyframes dust-drift {
  0% { transform: translate(0, 0); opacity: 0; }
  20% { opacity: 0.6; }
  80% { opacity: 0.4; }
  100% { transform: translate(40px, -30px); opacity: 0; }
}

.map-skeleton {
  width: 100%;
  aspect-ratio: 1;
  background: var(--bg-primary);
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  grid-template-rows: repeat(10, 1fr);
  width: 100%;
  height: 100%;
  opacity: 0.1;
}

.skeleton-tile {
  border: 1px solid var(--accent-blue);
  animation: pulse-grid 2s infinite;
}

.skeleton-message {
  position: absolute;
  color: var(--accent-blue);
  font-family: var(--font-mono);
  font-size: 0.8rem;
  background: rgba(10, 10, 15, 0.8);
  padding: 0.5rem 1rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--accent-blue);
  animation: pulse-text 1.5s infinite alternate;
}

@keyframes pulse-grid {
  0%, 100% { opacity: 0.1; }
  50% { opacity: 0.3; }
}

@keyframes pulse-text {
  from { opacity: 0.7; }
  to { opacity: 1; }
}

@keyframes geyser-pulse-anim {
  0%, 100% { r: 7; opacity: 0.95; }
  50% { r: 9; opacity: 0.7; }
}
.geyser-pulse {
  animation: geyser-pulse-anim 0.6s ease-in-out infinite;
}
</style>
