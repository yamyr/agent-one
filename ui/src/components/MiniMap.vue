<script setup>
import { computed } from 'vue'
import { VIEWPORT_W, VIEWPORT_H, agentColor } from '../constants.js'

const props = defineProps({
  worldState: {
    type: Object,
    default: null,
  },
  agentIds: {
    type: Array,
    default: () => [],
  },
  camX: { type: Number, default: 0 },
  camY: { type: Number, default: 0 },
})

const emit = defineEmits(['navigate'])

const MINI_TILE = 3 // pixels per tile on minimap
const PADDING = 2   // extra tiles around bounds

const bounds = computed(() => {
  if (!props.worldState?.bounds) {
    return { min_x: -10, max_x: 10, min_y: -10, max_y: 10 }
  }
  const b = props.worldState.bounds
  return {
    min_x: Math.min(b.min_x, props.camX) - PADDING,
    max_x: Math.max(b.max_x, props.camX + VIEWPORT_W) + PADDING,
    min_y: Math.min(b.min_y, props.camY) - PADDING,
    max_y: Math.max(b.max_y, props.camY + VIEWPORT_H) + PADDING,
  }
})

const mapW = computed(() => (bounds.value.max_x - bounds.value.min_x + 1) * MINI_TILE)
const mapH = computed(() => (bounds.value.max_y - bounds.value.min_y + 1) * MINI_TILE)

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

const revealedTiles = computed(() => {
  const tiles = []
  for (const key of revealedSet.value) {
    const [x, y] = key.split(',').map(Number)
    if (x >= bounds.value.min_x && x <= bounds.value.max_x &&
        y >= bounds.value.min_y && y <= bounds.value.max_y) {
      tiles.push({
        sx: (x - bounds.value.min_x) * MINI_TILE,
        sy: (bounds.value.max_y - y) * MINI_TILE,
        key,
      })
    }
  }
  return tiles
})

const agents = computed(() => {
  if (!props.worldState) return []
  return props.agentIds
    .filter(id => props.worldState.agents[id] && props.worldState.agents[id].type !== 'station')
    .map(id => {
      const a = props.worldState.agents[id]
      return {
        id,
        cx: (a.position[0] - bounds.value.min_x) * MINI_TILE + MINI_TILE / 2,
        cy: (bounds.value.max_y - a.position[1]) * MINI_TILE + MINI_TILE / 2,
        color: agentColor(id),
      }
    })
})

// Viewport rectangle on minimap
const viewRect = computed(() => ({
  x: (props.camX - bounds.value.min_x) * MINI_TILE,
  y: (bounds.value.max_y - (props.camY + VIEWPORT_H - 1)) * MINI_TILE,
  w: VIEWPORT_W * MINI_TILE,
  h: VIEWPORT_H * MINI_TILE,
}))

function onClick(e) {
  const svg = e.currentTarget
  const rect = svg.getBoundingClientRect()
  const mx = (e.clientX - rect.left) / rect.width * mapW.value
  const my = (e.clientY - rect.top) / rect.height * mapH.value
  const worldX = Math.round(mx / MINI_TILE + bounds.value.min_x - VIEWPORT_W / 2)
  const worldY = Math.round(bounds.value.max_y - my / MINI_TILE - VIEWPORT_H / 2)
  emit('navigate', worldX, worldY)
}
</script>

<template>
  <section class="minimap">
    <h2>Overview</h2>
    <svg
      v-if="worldState"
      :viewBox="`0 0 ${mapW} ${mapH}`"
      class="minimap-svg"
      @click="onClick"
    >
      <!-- Background -->
      <rect
        x="0"
        y="0"
        :width="mapW"
        :height="mapH"
        fill="#060609"
      />

      <!-- Revealed tiles -->
      <rect
        v-for="t in revealedTiles"
        :key="t.key"
        :x="t.sx"
        :y="t.sy"
        :width="MINI_TILE"
        :height="MINI_TILE"
        fill="#1a1a28"
      />

      <!-- Agent dots -->
      <circle
        v-for="a in agents"
        :key="a.id"
        :cx="a.cx"
        :cy="a.cy"
        :r="Math.max(2, MINI_TILE * 0.8)"
        :fill="a.color"
        opacity="0.9"
      />

      <!-- Viewport rectangle -->
      <rect
        :x="viewRect.x"
        :y="viewRect.y"
        :width="viewRect.w"
        :height="viewRect.h"
        fill="none"
        stroke="#668"
        stroke-width="1"
        opacity="0.7"
      />
    </svg>
    <div
      v-else
      class="empty"
    >
      No data
    </div>
  </section>
</template>

<style scoped>
.minimap {
  padding: 0.5rem;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-card);
}

.minimap-svg {
  width: 100%;
  max-height: 120px;
  display: block;
  cursor: crosshair;
}

@media (max-width: 480px) {
  .minimap {
    display: none;
  }
}
</style>
