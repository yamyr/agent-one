<script setup>
import { computed } from 'vue'
import { GRID_SIZE, TILE_SIZE, MAP_W, MAP_H, STONE_COLORS, agentColor } from '../constants.js'

const props = defineProps({
  worldState: Object,
  agentIds: Array,
})

const emit = defineEmits(['select-agent'])

const tiles = computed(() => {
  const arr = []
  for (let y = 0; y < GRID_SIZE; y++) {
    for (let x = 0; x < GRID_SIZE; x++) {
      arr.push({ x, y, key: `${x}-${y}` })
    }
  }
  return arr
})

const rovers = computed(() => {
  if (!props.agentIds) return []
  return props.agentIds.filter(id => {
    if (!props.worldState) return true
    const a = props.worldState.agents[id]
    return !a || a.type !== 'station'
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

function agentTransform(id) {
  if (!props.worldState) return ''
  const a = props.worldState.agents[id]
  if (!a) return ''
  const cx = a.position[0] * TILE_SIZE + TILE_SIZE / 2
  const cy = a.position[1] * TILE_SIZE + TILE_SIZE / 2
  return `translate(${cx}, ${cy})`
}
</script>

<template>
  <section class="world-map">
    <h2>Surface Map</h2>
    <svg v-if="worldState"
      :viewBox="`0 0 ${MAP_W} ${MAP_H}`"
      class="map-svg">
      <!-- grid tiles -->
      <rect v-for="t in tiles" :key="t.key"
        :x="t.x * TILE_SIZE" :y="t.y * TILE_SIZE"
        :width="TILE_SIZE" :height="TILE_SIZE"
        :class="isRevealed(t.x, t.y) ? 'grid-tile revealed' : 'grid-tile'" />

      <!-- stones -->
      <rect v-for="(s, i) in (worldState.stones || [])" :key="'stone-'+i"
        :x="s.position[0] * TILE_SIZE + TILE_SIZE/2 - 4"
        :y="s.position[1] * TILE_SIZE + TILE_SIZE/2 - 4"
        width="8" height="8"
        :fill="STONE_COLORS[s.type] || '#666'"
        opacity="0.85"
        :transform="`rotate(45, ${s.position[0] * TILE_SIZE + TILE_SIZE/2}, ${s.position[1] * TILE_SIZE + TILE_SIZE/2})`" />

      <!-- station markers (square) -->
      <g v-for="id in stations" :key="'station-'+id"
        :transform="agentTransform(id)" class="rover-group" style="cursor:pointer"
        @click="emit('select-agent', id)">
        <rect x="-7" y="-7" width="14" height="14" rx="2" :fill="agentColor(id)" opacity="0.9">
          <animate attributeName="width" values="14;16;14" dur="2s" repeatCount="indefinite" />
          <animate attributeName="height" values="14;16;14" dur="2s" repeatCount="indefinite" />
          <animate attributeName="x" values="-7;-8;-7" dur="2s" repeatCount="indefinite" />
          <animate attributeName="y" values="-7;-8;-7" dur="2s" repeatCount="indefinite" />
        </rect>
        <rect x="-12" y="-12" width="24" height="24" rx="3" fill="none" :stroke="agentColor(id)" stroke-width="1" opacity="0.25">
          <animate attributeName="opacity" values="0.25;0.08;0.25" dur="2s" repeatCount="indefinite" />
        </rect>
        <text y="20" text-anchor="middle" :fill="agentColor(id)" class="rover-label">{{ id }}</text>
      </g>

      <!-- rover dots (circle) -->
      <g v-for="id in rovers" :key="'rover-'+id"
        :transform="agentTransform(id)" class="rover-group" style="cursor:pointer"
        @click="emit('select-agent', id)">
        <circle r="7" :fill="agentColor(id)" opacity="0.9">
          <animate attributeName="r" values="7;8;7" dur="2s" repeatCount="indefinite" />
        </circle>
        <circle r="12" fill="none" :stroke="agentColor(id)" stroke-width="1" opacity="0.25">
          <animate attributeName="r" values="12;16;12" dur="2s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.25;0.08;0.25" dur="2s" repeatCount="indefinite" />
        </circle>
        <text y="18" text-anchor="middle" :fill="agentColor(id)" class="rover-label">{{ id }}</text>
      </g>
    </svg>
    <div v-else class="empty">Waiting for world state...</div>
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
</style>
