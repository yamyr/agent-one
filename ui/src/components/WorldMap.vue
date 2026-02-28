<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { TILE_SIZE, MAP_W, MAP_H, VIEWPORT_W, VIEWPORT_H, VEIN_COLORS, VEIN_SIZES, SOLAR_PANEL_COLOR, SOLAR_PANEL_DEPLETED_COLOR, agentColor, revealRadius } from '../constants.js'

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
})

const emit = defineEmits(['select-agent', 'unfollow'])

// Camera state: top-left tile of viewport
const camX = ref(-Math.floor(VIEWPORT_W / 2))
const camY = ref(-Math.floor(VIEWPORT_H / 2))

// Smooth camera: targets that camX/camY interpolate toward
const targetCamX = ref(camX.value)
const targetCamY = ref(camY.value)
const LERP_SPEED = 0.15 // fraction per frame (higher = snappier)
let rafId = null

function cameraLoop() {
  const dx = targetCamX.value - camX.value
  const dy = targetCamY.value - camY.value
  if (Math.abs(dx) > 0.01 || Math.abs(dy) > 0.01) {
    camX.value += dx * LERP_SPEED
    camY.value += dy * LERP_SPEED
    // Snap when very close
    if (Math.abs(dx) < 0.05) camX.value = targetCamX.value
    if (Math.abs(dy) < 0.05) camY.value = targetCamY.value
  }
  rafId = requestAnimationFrame(cameraLoop)
}

onMounted(() => { rafId = requestAnimationFrame(cameraLoop) })
onUnmounted(() => { if (rafId) cancelAnimationFrame(rafId) })

// Track drag state
const dragging = ref(false)
const dragStart = ref({ x: 0, y: 0 })

// Follow selected agent: update target (smooth interpolation via rAF)
watch([() => props.worldState, () => props.followAgent], () => {
  if (!props.worldState || !props.followAgent) return
  const a = props.worldState.agents?.[props.followAgent]
  if (a) {
    targetCamX.value = a.position[0] - Math.floor(VIEWPORT_W / 2)
    targetCamY.value = a.position[1] - Math.floor(VIEWPORT_H / 2)
  }
}, { deep: true })

const tiles = computed(() => {
  const arr = []
  for (let dy = 0; dy < VIEWPORT_H; dy++) {
    for (let dx = 0; dx < VIEWPORT_W; dx++) {
      const x = camX.value + dx
      const y = camY.value + VIEWPORT_H - 1 - dy  // flip Y for SVG
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

const revealedSet = computed(() => {
  const set = new Set()
  if (!props.worldState) return set
  for (const agent of Object.values(props.worldState.agents)) {
    for (const cell of (agent.revealed || [])) {
      set.add(`${cell[0]},${cell[1]}`)
    }
  }
  return set
})

function isRevealed(x, y) {
  return revealedSet.value.has(`${x},${y}`)
}

// Grade weights for concentration radius (mirrors server logic)
const GRADE_ORDER = ['low', 'medium', 'high', 'rich', 'pristine']

function tileConcentration(x, y) {
  if (!props.worldState) return 0
  const stones = props.worldState.stones || []
  let max = 0
  for (const s of stones) {
    const [sx, sy] = s.position
    const d = Math.abs(x - sx) + Math.abs(y - sy)
    if (d === 0) return 1
    const gi = GRADE_ORDER.indexOf(s.grade !== 'unknown' ? s.grade : 'low')
    const radius = 10 + (gi >= 0 ? gi : 0) * 2
    const c = Math.max(0, 1 - d / radius)
    if (c > max) max = c
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
  const sy = (VIEWPORT_H - 1 - (wy - camY.value)) * TILE_SIZE + TILE_SIZE / 2
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
  return wx >= camX.value && wx < camX.value + VIEWPORT_W &&
         wy >= camY.value && wy < camY.value + VIEWPORT_H
}

function isStoneVisible(s) {
  const [wx, wy] = s.position
  return wx >= camX.value && wx < camX.value + VIEWPORT_W &&
         wy >= camY.value && wy < camY.value + VIEWPORT_H
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
  return (VIEWPORT_H - 1 - (s.position[1] - camY.value)) * TILE_SIZE + TILE_SIZE / 2 - half
}

function stoneRotateCenter(s) {
  const cx = (s.position[0] - camX.value) * TILE_SIZE + TILE_SIZE / 2
  const cy = (VIEWPORT_H - 1 - (s.position[1] - camY.value)) * TILE_SIZE + TILE_SIZE / 2
  return `rotate(45, ${cx}, ${cy})`
}

function veinHasGlow(s) {
  const g = veinGrade(s)
  return g === 'rich' || g === 'pristine'
}

function isPanelVisible(p) {
  const [wx, wy] = p.position
  return wx >= camX.value && wx < camX.value + VIEWPORT_W &&
         wy >= camY.value && wy < camY.value + VIEWPORT_H
}

function panelScreenX(p) {
  return (p.position[0] - camX.value) * TILE_SIZE + 2
}

function panelScreenY(p) {
  return (VIEWPORT_H - 1 - (p.position[1] - camY.value)) * TILE_SIZE + 2
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
  const tilePixelW = rect.width / VIEWPORT_W
  const tilePixelH = rect.height / VIEWPORT_H
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

function panCamera(dx, dy) {
  targetCamX.value += dx
  targetCamY.value += dy
}

// Expose camera for minimap & keyboard shortcuts
defineExpose({ camX, camY, panCamera })
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
    <svg
      v-if="worldState"
      :viewBox="`0 0 ${MAP_W} ${MAP_H}`"
      class="map-svg"
      @mousedown.prevent="onMouseDown"
      @mousemove="onMouseMove"
      @mouseup="onMouseUp"
      @mouseleave="onMouseUp"
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

      <!-- SVG filter for vein glow -->
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
          :fill="VEIN_COLORS[veinGrade(s)] || '#666'"
          :opacity="veinHasGlow(s) ? 0.95 : 0.85"
          :transform="stoneRotateCenter(s)"
          :filter="veinHasGlow(s) ? 'url(#vein-glow)' : undefined"
        />
      </template>

      <!-- solar panels -->
      <template
        v-for="(p, i) in (worldState.solar_panels || [])"
        :key="'panel-'+i"
      >
        <g v-if="isPanelVisible(p)">
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
            :stroke="p.depleted ? '#333' : '#aa8020'"
            stroke-width="0.5"
          />
          <line
            :x1="panelScreenX(p)"
            :y1="panelScreenY(p) + (TILE_SIZE - 4) / 2"
            :x2="panelScreenX(p) + TILE_SIZE - 4"
            :y2="panelScreenY(p) + (TILE_SIZE - 4) / 2"
            :stroke="p.depleted ? '#333' : '#aa8020'"
            stroke-width="0.5"
          />
        </g>
      </template>

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
      class="empty"
    >
      Waiting for world state...
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

.cam-hint {
  font-size: 0.6rem;
  color: var(--text-dimmer);
  font-weight: normal;
  text-transform: none;
  letter-spacing: 0;
}

.map-svg {
  cursor: grab;
}
.map-svg:active {
  cursor: grabbing;
}
</style>
