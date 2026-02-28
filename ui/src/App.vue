<script setup>
import { ref, computed } from 'vue'
import { useWebSocket } from './composables/useWebSocket.js'
import AppHeader from './components/AppHeader.vue'
import WorldMap from './components/WorldMap.vue'
import MiniMap from './components/MiniMap.vue'
import AgentPanes from './components/AgentPanes.vue'
import MissionBar from './components/MissionBar.vue'
import EventLog from './components/EventLog.vue'
import AgentDetailModal from './components/AgentDetailModal.vue'
import NarrationPlayer from './components/NarrationPlayer.vue'

const selectedAgent = ref(null)
const paused = ref(false)
const narrationEnabled = ref(true)
const worldMapRef = ref(null)
const camXVal = computed(() => worldMapRef.value?.camX ?? -10)
const camYVal = computed(() => worldMapRef.value?.camY ?? -10)


function onWsConnect() {
  paused.value = false
  fetch('/api/simulation/reset', { method: 'POST' })
}

async function toggleNarration() {
  const res = await fetch('/api/narration/toggle', { method: 'POST' })
  const data = await res.json()
  narrationEnabled.value = data.enabled
}

async function resetSimulation() {
  const res = await fetch('/api/simulation/reset', { method: 'POST' })
  if (res.ok) {
    paused.value = false
    events.value = []
  }
}

const { events, connected, worldState, agentIds, agentEvents, narration } = useWebSocket({ onConnect: onWsConnect })

async function togglePause() {
  const endpoint = paused.value ? '/api/simulation/resume' : '/api/simulation/pause'
  const res = await fetch(endpoint, { method: 'POST' })
  const data = await res.json()
  paused.value = data.paused
}

function selectAgent(id) {
  selectedAgent.value = id
}

function closeAgent() {
  selectedAgent.value = null
}

function agentData(id) {
  if (!worldState.value) return null
  return worldState.value.agents[id] || null
}

function onMinimapNavigate(x, y) {
  if (worldMapRef.value) {
    worldMapRef.value.camX = x
    worldMapRef.value.camY = y
    worldMapRef.value.autoFollow = false
  }
}
</script>

<template>
  <div class="app">
    <AppHeader
      :connected="connected"
      :paused="paused"
      @toggle-pause="togglePause"
      @reset="resetSimulation"
    />

    <NarrationPlayer
      :narration="narration"
      :narration-enabled="narrationEnabled"
      @toggle-narration="toggleNarration"
    />

    <MissionBar :mission="worldState ? worldState.mission : null" />

    <div class="top-row">
      <div class="left-col">
        <WorldMap
          ref="worldMapRef"
          :world-state="worldState"
          :agent-ids="agentIds"
          @select-agent="selectAgent"
        />
        <MiniMap
          :world-state="worldState"
          :agent-ids="agentIds"
          :cam-x="camXVal"
          :cam-y="camYVal"
          @navigate="onMinimapNavigate"
        />
        <EventLog :events="events" />
      </div>
      <AgentPanes
        :world-state="worldState"
        :agent-ids="agentIds"
        :agent-events="agentEvents"
        @select-agent="selectAgent"
      />
    </div>

    <AgentDetailModal
      v-if="selectedAgent"
      :agent="agentData(selectedAgent)"
      :agent-id="selectedAgent"
      @close="closeAgent"
    />
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

.top-row {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.left-col {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 3;
  min-width: 0;
}

.empty {
  color: #444;
  padding: 1rem;
  text-align: center;
  font-size: 0.8rem;
}

h2 {
  font-size: 0.85rem;
  color: #555;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 0.5rem;
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
