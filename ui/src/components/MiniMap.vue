<script setup>
import { computed } from 'vue'
import MapLegend from './MapLegend.vue'
import { VIEWPORT_W, VIEWPORT_H, VEIN_COLORS, agentColor } from '../constants.js'
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
  camX: { type: Number, default: 0 },
  camY: { type: Number, default: 0 },
  viewportW: { type: Number, default: VIEWPORT_W },
  viewportH: { type: Number, default: VIEWPORT_H },
})

const veins = computed(() => {
  if (!props.worldState) return []
  return (props.worldState.stones || [])
    .filter(s => revealedSet.value.has(`${s.position[0]},${s.position[1]}`))
    .map((s, i) => ({
      key: `vein-${i}-${s.position[0]}-${s.position[1]}`,
      cx: (s.position[0] - bounds.value.min_x) * MINI_TILE + MINI_TILE / 2,
      cy: (bounds.value.max_y - s.position[1]) * MINI_TILE + MINI_TILE / 2,
      color: VEIN_COLORS[s.grade || 'unknown'] || VEIN_COLORS.unknown,
    }))
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
    max_x: Math.max(b.max_x, props.camX + props.viewportW) + PADDING,
    min_y: Math.min(b.min_y, props.camY) - PADDING,
    max_y: Math.max(b.max_y, props.camY + props.viewportH) + PADDING,
  }
})

const mapW = computed(() => (bounds.value.max_x - bounds.value.min_x + 1) * MINI_TILE)
const mapH = computed(() => (bounds.value.max_y - bounds.value.min_y + 1) * MINI_TILE)

const { revealedSet } = useRevealedSet(() => props.worldState)

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
  y: (bounds.value.max_y - (props.camY + props.viewportH - 1)) * MINI_TILE,
  w: props.viewportW * MINI_TILE,
  h: props.viewportH * MINI_TILE,
}))

function onClick(e) {
  const svg = e.currentTarget
  const rect = svg.getBoundingClientRect()
  const mx = (e.clientX - rect.left) / rect.width * mapW.value
  const my = (e.clientY - rect.top) / rect.height * mapH.value
  const worldX = Math.round(mx / MINI_TILE + bounds.value.min_x - props.viewportW / 2)
  const worldY = Math.round(bounds.value.max_y - my / MINI_TILE - props.viewportH / 2)
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
        fill="var(--bg-minimap)"
      />

      <!-- Revealed tiles -->
      <rect
        v-for="t in revealedTiles"
        :key="t.key"
        :x="t.sx"
        :y="t.sy"
        :width="MINI_TILE"
        :height="MINI_TILE"
        fill="var(--bg-minimap-revealed)"
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

      <!-- Vein indicators -->
      <circle
        v-for="v in veins"
        :key="v.key"
        :cx="v.cx"
        :cy="v.cy"
        r="1"
        :fill="v.color"
        opacity="0.95"
      />

      <!-- Viewport rectangle -->
      <rect
        :x="viewRect.x"
        :y="viewRect.y"
        :width="viewRect.w"
        :height="viewRect.h"
        fill="none"
        stroke="var(--accent-think)"
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
    <MapLegend />
  </section>
</template>

<style scoped>
.minimap {
  padding: 0.5rem;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  position: relative;
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
