<script setup>
import { computed, ref, watch } from 'vue'
import { TILE_SIZE, MAP_W, MAP_H, VIEWPORT_W, VIEWPORT_H, STONE_COLORS, SOLAR_PANEL_COLOR, SOLAR_PANEL_DEPLETED_COLOR, agentColor, revealRadius } from '../constants.js'

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

// Track drag state
const dragging = ref(false)
const dragStart = ref({ x: 0, y: 0 })

// Follow selected agent: center camera on it when worldState updates
watch([() => props.worldState, () => props.followAgent], () => {
  if (!props.worldState || !props.followAgent) return
  const a = props.worldState.agents?.[props.followAgent]
  if (a) {
    camX.value = a.position[0] - Math.floor(VIEWPORT_W / 2)
    camY.value = a.position[1] - Math.floor(VIEWPORT_H / 2)
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

function stoneScreenX(s) {
  return (s.position[0] - camX.value) * TILE_SIZE + TILE_SIZE / 2 - 4
}

function stoneScreenY(s) {
  return (VIEWPORT_H - 1 - (s.position[1] - camY.value)) * TILE_SIZE + TILE_SIZE / 2 - 4
}

function stoneRotateCenter(s) {
  const cx = (s.position[0] - camX.value) * TILE_SIZE + TILE_SIZE / 2
  const cy = (VIEWPORT_H - 1 - (s.position[1] - camY.value)) * TILE_SIZE + TILE_SIZE / 2
  return `rotate(45, ${cx}, ${cy})`
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
    camX.value -= tileDx
    dragStart.value.x = e.clientX
    emit('unfollow')
  }
  if (Math.abs(dy) >= tilePixelH) {
    const tileDy = Math.round(dy / tilePixelH)
    camY.value += tileDy
    dragStart.value.y = e.clientY
    emit('unfollow')
  }
}

function onMouseUp() {
  dragging.value = false
}

// Expose camera for minimap
defineExpose({ camX, camY })
</script>

<template>
  <section class="world-map">
    <h2>
      Surface Map
      <span v-if="followAgent" class="cam-hint">(following {{ followAgent }})</span>
      <span v-else class="cam-hint">(free camera · drag to pan)</span>
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
      />

      <!-- stones -->
      <template v-for="(s, i) in (worldState.stones || [])" :key="'stone-'+i">
        <rect
          v-if="isStoneVisible(s)"
          :x="stoneScreenX(s)"
          :y="stoneScreenY(s)"
          width="8"
          height="8"
          :fill="STONE_COLORS[s.type] || '#666'"
          opacity="0.85"
          :transform="stoneRotateCenter(s)"
        />
      </template>

      <!-- solar panels -->
      <template v-for="(p, i) in (worldState.solar_panels || [])" :key="'panel-'+i">
        <g v-if="isPanelVisible(p)">
          <!-- panel base -->
          <rect
            :x="panelScreenX(p)"
            :y="panelScreenY(p)"
            :width="TILE_SIZE - 4"
            :height="TILE_SIZE - 4"
            :fill="p.depleted ? SOLAR_PANEL_DEPLETED_COLOR : SOLAR_PANEL_COLOR"
            :opacity="p.depleted ? 0.3 : 0.7"
            rx="2"
          />
          <!-- grid lines on panel -->
          <line
            :x1="panelScreenX(p) + (TILE_SIZE - 4) / 2"
            :y1="panelScreenY(p)"
            :x2="panelScreenX(p) + (TILE_SIZE - 4) / 2"
            :y2="panelScreenY(p) + TILE_SIZE - 4"
            :stroke="p.depleted ? '#333' : '#c8a020'"
            stroke-width="0.5"
          />
          <line
            :x1="panelScreenX(p)"
            :y1="panelScreenY(p) + (TILE_SIZE - 4) / 2"
            :x2="panelScreenX(p) + TILE_SIZE - 4"
            :y2="panelScreenY(p) + (TILE_SIZE - 4) / 2"
            :stroke="p.depleted ? '#333' : '#c8a020'"
            stroke-width="0.5"
          />
        </g>
      </template>

      <!-- station markers (square) -->
      <g
        v-for="id in stations"
        :key="'station-'+id"
        v-show="isAgentVisible(id)"
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
        :key="'rover-'+id"
        v-show="isAgentVisible(id)"
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
        :key="'drone-'+id"
        v-show="isAgentVisible(id)"
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
  border: 1px solid #1a1a24;
  border-radius: 4px;
  background: #0c0c14;
  min-width: 0;
}

.map-svg {
  width: 100%;
  height: auto;
  display: block;
}

.grid-tile {
  fill: #060609;
  stroke: #111118;
  stroke-width: 0.5;
}

.grid-tile.revealed {
  fill: #0e0e16;
  stroke: #1a1a24;
}

.rover-group {
  transition: transform 0.4s ease;
}

.rover-label {
  font-family: 'Courier New', monospace;
  font-size: 6px;
}

.cam-hint {
  font-size: 0.6rem;
  color: #444;
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
