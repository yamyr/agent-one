<script setup>
import { ref } from 'vue'
import { useWebSocket } from './composables/useWebSocket.js'
import AppHeader from './components/AppHeader.vue'
import WorldMap from './components/WorldMap.vue'
import AgentPanes from './components/AgentPanes.vue'
import MissionBar from './components/MissionBar.vue'
import EventLog from './components/EventLog.vue'
import AgentDetailModal from './components/AgentDetailModal.vue'

const selectedAgent = ref(null)
const paused = ref(false)

function onWsConnect() {
  paused.value = false
  fetch('/api/simulation/reset', { method: 'POST' })
}

const { events, connected, worldState, agentIds, agentEvents } = useWebSocket({ onConnect: onWsConnect })

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
</script>

<template>
  <div class="app">
    <AppHeader :connected="connected" :paused="paused" @toggle-pause="togglePause" />

    <MissionBar :mission="worldState ? worldState.mission : null" />

    <div class="top-row">
      <WorldMap :worldState="worldState" :agentIds="agentIds" @select-agent="selectAgent" />
      <AgentPanes :worldState="worldState" :agentIds="agentIds" :agentEvents="agentEvents" @select-agent="selectAgent" />
    </div>

    <EventLog :events="events" />

    <AgentDetailModal
      v-if="selectedAgent"
      :agent="agentData(selectedAgent)"
      :agentId="selectedAgent"
      @close="closeAgent" />
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
