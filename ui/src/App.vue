<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'

const events = ref([])
const connected = ref(false)
const worldState = ref(null)
let ws = null

const GRID_SIZE = 20
const TILE_SIZE = 20
const MAP_W = GRID_SIZE * TILE_SIZE
const MAP_H = GRID_SIZE * TILE_SIZE

const STONE_COLORS = {
  'core': '#b8962a',
  'basalt': '#666666',
}

const AGENT_COLORS = {
  'rover-mock': '#6688cc',
  'rover-mistral': '#e06030',
}

function agentColor(id) {
  return AGENT_COLORS[id] || '#6c6'
}

const agentEvents = computed(() => {
  const byAgent = {}
  for (const e of events.value) {
    if (e.source === 'world') continue
    if (!byAgent[e.source]) byAgent[e.source] = []
    if (byAgent[e.source].length < 50) byAgent[e.source].push(e)
  }
  return byAgent
})

const agentIds = computed(() => {
  if (!worldState.value) return []
  return Object.keys(worldState.value.agents)
})

function batteryPct(id) {
  if (!worldState.value) return '?'
  const a = worldState.value.agents[id]
  return a ? Math.round(a.battery * 100) + '%' : '?'
}

function agentPosition(id) {
  if (!worldState.value) return '?'
  const a = worldState.value.agents[id]
  if (!a) return '?'
  return `(${a.position[0]}, ${a.position[1]})`
}

function roverTransform(id) {
  if (!worldState.value) return ''
  const a = worldState.value.agents[id]
  if (!a) return ''
  const cx = a.position[0] * TILE_SIZE + TILE_SIZE / 2
  const cy = a.position[1] * TILE_SIZE + TILE_SIZE / 2
  return `translate(${cx}, ${cy})`
}

function formatMoveEvent(payload) {
  const f = payload.from
  const t = payload.to
  return `(${f[0]},${f[1]}) → (${t[0]},${t[1]})`
}

// Generate tile data for v-for
const tiles = computed(() => {
  const arr = []
  for (let y = 0; y < GRID_SIZE; y++) {
    for (let x = 0; x < GRID_SIZE; x++) {
      arr.push({ x, y, key: `${x}-${y}` })
    }
  }
  return arr
})

function connect() {
  ws = new WebSocket(`ws://${window.location.host}/ws`)

  ws.onopen = () => {
    connected.value = true
  }

  ws.onmessage = (msg) => {
    const event = JSON.parse(msg.data)
    if (event.source === 'world' && event.name === 'state') {
      worldState.value = event.payload
    } else {
      events.value.unshift(event)
      if (events.value.length > 200) {
        events.value.length = 200
      }
    }
  }

  ws.onclose = () => {
    connected.value = false
    setTimeout(connect, 2000)
  }

  ws.onerror = () => {
    ws.close()
  }
}

onMounted(() => {
  connect()
})

onUnmounted(() => {
  if (ws) ws.close()
})
</script>

<template>
  <div class="app">
    <header>
      <h1>Mars Mission Control</h1>
      <span class="status" :class="{ online: connected }">
        {{ connected ? 'CONNECTED' : 'DISCONNECTED' }}
      </span>
    </header>

    <!-- Map + Agent Panes side by side -->
    <div class="top-row">
      <!-- 2D Grid Map -->
      <section class="world-map">
        <h2>Surface Map</h2>
        <svg v-if="worldState"
          :viewBox="`0 0 ${MAP_W} ${MAP_H}`"
          class="map-svg">
          <!-- grid tiles -->
          <rect v-for="t in tiles" :key="t.key"
            :x="t.x * TILE_SIZE" :y="t.y * TILE_SIZE"
            :width="TILE_SIZE" :height="TILE_SIZE"
            class="grid-tile" />

          <!-- stones -->
          <rect v-for="(s, i) in (worldState.stones || [])" :key="'stone-'+i"
            :x="s.position[0] * TILE_SIZE + TILE_SIZE/2 - 4"
            :y="s.position[1] * TILE_SIZE + TILE_SIZE/2 - 4"
            width="8" height="8"
            :fill="STONE_COLORS[s.type] || '#666'"
            opacity="0.85"
            :transform="`rotate(45, ${s.position[0] * TILE_SIZE + TILE_SIZE/2}, ${s.position[1] * TILE_SIZE + TILE_SIZE/2})`" />

          <!-- rover dots -->
          <g v-for="id in agentIds" :key="'rover-'+id"
            :transform="roverTransform(id)" class="rover-group">
            <circle r="7" :fill="agentColor(id)" opacity="0.9">
              <animate attributeName="r" values="7;8;7" dur="2s" repeatCount="indefinite" />
            </circle>
            <!-- glow -->
            <circle r="12" fill="none" :stroke="agentColor(id)" stroke-width="1" opacity="0.25">
              <animate attributeName="r" values="12;16;12" dur="2s" repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.25;0.08;0.25" dur="2s" repeatCount="indefinite" />
            </circle>
            <!-- label -->
            <text y="18" text-anchor="middle" :fill="agentColor(id)" class="rover-label">{{ id }}</text>
          </g>
        </svg>
        <div v-else class="empty">Waiting for world state...</div>
      </section>

      <!-- Agent Panes -->
      <section class="agent-panes">
        <div v-for="id in agentIds" :key="id" class="agent-pane">
          <div class="agent-header">
            <span class="agent-name" :style="{ color: agentColor(id) }">{{ id }}</span>
            <span class="agent-stats">
              {{ agentPosition(id) }} &middot; bat {{ batteryPct(id) }}
            </span>
          </div>
          <div class="agent-log">
            <div v-if="!agentEvents[id] || agentEvents[id].length === 0" class="empty">
              No events yet
            </div>
            <div v-for="(e, i) in (agentEvents[id] || [])" :key="i" class="agent-event">
              <span class="ae-type" :class="e.type">{{ e.type }}</span>
              <span class="ae-name">{{ e.name }}</span>
              <span v-if="e.name === 'thinking'" class="ae-text">{{ e.payload.text }}</span>
              <span v-else-if="e.name === 'move'" class="ae-text">{{ formatMoveEvent(e.payload) }}</span>
              <span v-else-if="e.payload" class="ae-text">{{ JSON.stringify(e.payload) }}</span>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- Event Log -->
    <section class="event-log">
      <h2>Event Log</h2>
      <div v-if="events.length === 0" class="empty">
        Waiting for mission events...
      </div>
      <div v-for="(event, i) in events" :key="i" class="event">
        <span class="event-source" :style="{ color: agentColor(event.source) }">{{ event.source }}</span>
        <span class="event-type">{{ event.type }}</span>
        <span class="event-name">{{ event.name }}</span>
        <pre v-if="event.payload" class="event-payload">{{ JSON.stringify(event.payload, null, 2) }}</pre>
      </div>
    </section>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  background: #0a0a0f;
  color: #c8c8d0;
  font-family: 'Courier New', monospace;
}

.app {
  max-width: 1100px;
  margin: 0 auto;
  padding: 1rem;
}

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 0;
  border-bottom: 1px solid #222;
  margin-bottom: 1rem;
}

h1 {
  font-size: 1.2rem;
  color: #e06030;
}

h2 {
  font-size: 0.85rem;
  color: #555;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 0.5rem;
}

.status {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: 3px;
  background: #331111;
  color: #cc4444;
}

.status.online {
  background: #113311;
  color: #44cc44;
}

.empty {
  color: #444;
  padding: 1rem;
  text-align: center;
  font-size: 0.8rem;
}

/* ── Top Row: Map + Agent Panes ── */

.top-row {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

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
  fill: #0e0e16;
  stroke: #1a1a24;
  stroke-width: 0.5;
}

.rover-group {
  transition: transform 0.4s ease;
}

.rover-label {
  font-family: 'Courier New', monospace;
  font-size: 6px;
}

/* ── Agent Panes ── */

.agent-panes {
  flex: 2;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 0;
}

.agent-pane {
  border: 1px solid #1a1a24;
  border-radius: 4px;
  background: #0c0c14;
  height: 200px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.agent-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.4rem 0.6rem;
  border-bottom: 1px solid #1a1a24;
  flex-shrink: 0;
}

.agent-name {
  font-size: 0.8rem;
  font-weight: bold;
}

.agent-stats {
  font-size: 0.7rem;
  color: #666;
}

.agent-log {
  flex: 1;
  overflow-y: auto;
  padding: 0.25rem;
}

.agent-event {
  padding: 0.2rem 0.35rem;
  font-size: 0.75rem;
  border-bottom: 1px solid #111118;
  display: flex;
  gap: 0.4rem;
  align-items: baseline;
}

.ae-type {
  font-size: 0.65rem;
  color: #555;
  flex-shrink: 0;
}

.ae-type.action {
  color: #c86040;
}

.ae-name {
  color: #ccaa44;
  flex-shrink: 0;
}

.ae-text {
  color: #888;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Event Log ── */

.event-log {
  border: 1px solid #1a1a24;
  border-radius: 4px;
  background: #0c0c14;
  padding: 0.75rem;
  max-height: 420px;
  overflow-y: auto;
}

.event {
  padding: 0.35rem 0;
  border-bottom: 1px solid #111118;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: baseline;
}

.event-source {
  font-weight: bold;
  min-width: 100px;
  font-size: 0.8rem;
}

.event-type {
  color: #888;
  font-size: 0.75rem;
}

.event-name {
  color: #ccaa44;
  font-size: 0.8rem;
}

.event-payload {
  width: 100%;
  font-size: 0.7rem;
  color: #555;
  padding: 0.15rem 0 0 100px;
  white-space: pre-wrap;
}

/* scrollbar */
::-webkit-scrollbar {
  width: 4px;
}
::-webkit-scrollbar-track {
  background: #0a0a0f;
}
::-webkit-scrollbar-thumb {
  background: #222;
  border-radius: 2px;
}
</style>
