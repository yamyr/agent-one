<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import MarsGrid from './components/MarsGrid.vue'
import RoverTelemetry from './components/RoverTelemetry.vue'
import EventLog from './components/EventLog.vue'

const connected = ref(false)
const observation = ref(null)
const stepEvents = ref([])
let ws = null

const tick = computed(() => observation.value?.tick ?? 0)
const status = computed(() => observation.value?.status ?? 'idle')
const rover = computed(() => observation.value?.rover ?? null)
const mission = computed(() => observation.value?.mission ?? null)
const station = computed(() => observation.value?.station ?? null)
const knownCells = computed(() => observation.value?.known_cells ?? [])
const roverPos = computed(() => rover.value?.position ?? [0, 0])
const stationPos = computed(() => station.value?.position ?? [0, 0])

function connect() {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${proto}//${window.location.host}/ws`)

  ws.onopen = () => { connected.value = true }

  ws.onmessage = (msg) => {
    const event = JSON.parse(msg.data)
    if (event.source === 'world' && event.name === 'state') {
      observation.value = event.payload
    } else if (event.name === 'step_result') {
      stepEvents.value.unshift(event.payload)
      if (stepEvents.value.length > 100) {
        stepEvents.value.length = 100
      }
    }
  }

  ws.onclose = () => {
    connected.value = false
    setTimeout(connect, 2000)
  }

  ws.onerror = () => { ws.close() }
}

onMounted(() => { connect() })
onUnmounted(() => { if (ws) ws.close() })
</script>

<template>
  <div class="app">
    <header>
      <h1>Mars Mission Control</h1>
      <div class="header-right">
        <span v-if="observation" class="tick-badge">TICK {{ tick }}</span>
        <span class="status" :class="{ online: connected }">
          {{ connected ? 'CONNECTED' : 'DISCONNECTED' }}
        </span>
      </div>
    </header>

    <div v-if="observation" class="main-layout">
      <section class="grid-section">
        <h2>Surface Map</h2>
        <MarsGrid
          :knownCells="knownCells"
          :roverPosition="roverPos"
          :stationPosition="stationPos"
        />
        <div class="legend">
          <span class="legend-item"><span class="swatch fog-swatch"></span> Unknown</span>
          <span class="legend-item"><span class="swatch revealed-swatch"></span> Explored</span>
          <span class="legend-item"><span class="swatch dug-swatch"></span> Excavated</span>
          <span class="legend-item"><span class="marker-sm rover-c">R</span> Rover</span>
          <span class="legend-item"><span class="marker-sm station-c">S</span> Station</span>
          <span class="legend-item"><span class="dot precious-dot"></span> Precious</span>
          <span class="legend-item"><span class="dot common-dot"></span> Common</span>
        </div>
      </section>

      <section class="side-panel">
        <RoverTelemetry
          :rover="rover"
          :mission="mission"
          :status="status"
          :tick="tick"
        />
        <EventLog :events="stepEvents" />
      </section>
    </div>

    <div v-else class="waiting">
      Waiting for simulation...
    </div>
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

.header-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.tick-badge {
  font-size: 0.75rem;
  color: #888;
  padding: 0.25rem 0.5rem;
  background: #111;
  border-radius: 3px;
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

/* Main Layout */
.main-layout {
  display: flex;
  gap: 1rem;
}

.grid-section {
  flex: 1;
  min-width: 0;
}

.side-panel {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* Legend */
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  margin-top: 0.5rem;
  font-size: 0.65rem;
  color: #666;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.swatch {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.fog-swatch { background: #0e0e14; border: 1px solid #222; }
.revealed-swatch { background: #1a1a28; }
.dug-swatch { background: #1e1610; }

.marker-sm {
  font-weight: bold;
  font-size: 0.65rem;
}

.rover-c { color: #e06030; }
.station-c { color: #44cc44; }

.dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.precious-dot { background: #d4a020; }
.common-dot { background: #666; }

/* Waiting */
.waiting {
  text-align: center;
  color: #444;
  padding: 4rem 1rem;
  font-size: 0.9rem;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #0a0a0f; }
::-webkit-scrollbar-thumb { background: #222; border-radius: 2px; }

/* Responsive */
@media (max-width: 900px) {
  .main-layout {
    flex-direction: column;
  }
  .side-panel {
    width: 100%;
  }
}

@media (max-width: 600px) {
  .app {
    padding: 0.5rem;
  }
  header {
    flex-direction: column;
    gap: 0.5rem;
    align-items: flex-start;
  }
  h1 {
    font-size: 1rem;
  }
  .side-panel {
    width: 100%;
  }
}
</style>
