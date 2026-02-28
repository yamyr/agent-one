<script setup>
import { ref, computed } from 'vue'
import { useWebSocket } from './composables/useWebSocket.js'
import { agentColor } from './constants.js'
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
const followAgent = ref(null)  // which agent the camera follows (null = free camera)
const camXVal = computed(() => worldMapRef.value?.camX ?? -10)
const camYVal = computed(() => worldMapRef.value?.camY ?? -10)

const mobileAgents = computed(() => {
  if (!agentIds.value) return []
  return agentIds.value.filter(id => {
    if (!worldState.value) return false
    const a = worldState.value.agents[id]
    return a && a.type !== 'station'
  })
})


async function onWsConnect() {
  paused.value = false
  fetch('/api/simulation/reset', { method: 'POST' })
  try {
    const res = await fetch('/api/narration/status')
    if (res.ok) {
      const data = await res.json()
      narrationEnabled.value = data.enabled
    }
  } catch {
    // Server may not be ready yet — keep default
  }
}

async function toggleNarration() {
  const res = await fetch('/api/narration/toggle', { method: 'POST' })
  const data = await res.json()
  narrationEnabled.value = data.enabled
}

async function abortMission() {
  await fetch('/api/mission/abort', { method: 'POST' })
}

async function resetSimulation() {
  const res = await fetch('/api/simulation/reset', { method: 'POST' })
  if (res.ok) {
    paused.value = false
    events.value = []
  }
}

const { events, connected, worldState, agentIds, agentEvents, narration, narrationChunk } = useWebSocket({ onConnect: onWsConnect })

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
    followAgent.value = null
  }
}

function setFollowAgent(id) {
  followAgent.value = followAgent.value === id ? null : id
}

function onUnfollow() {
  followAgent.value = null
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
      :narration-chunk="narrationChunk"
      :narration-enabled="narrationEnabled"
      @toggle-narration="toggleNarration"
    />

    <MissionBar
      :mission="worldState ? worldState.mission : null"
      @abort="abortMission"
    />

    <div class="top-row">
      <div class="left-col">
        <!-- Entity follow selector -->
        <div class="follow-bar">
          <span class="follow-label">Follow:</span>
          <button
            v-for="id in mobileAgents"
            :key="id"
            :class="['follow-btn', { active: followAgent === id }]"
            :style="{ borderColor: agentColor(id), color: followAgent === id ? '#0a0a0f' : agentColor(id), backgroundColor: followAgent === id ? agentColor(id) : 'transparent' }"
            @click="setFollowAgent(id)"
          >{{ id }}</button>
          <button
            :class="['follow-btn', { active: !followAgent }]"
            :style="{ borderColor: '#555', color: !followAgent ? '#0a0a0f' : '#555', backgroundColor: !followAgent ? '#555' : 'transparent' }"
            @click="followAgent = null"
          >Free</button>
        </div>
        <WorldMap
          ref="worldMapRef"
          :world-state="worldState"
          :agent-ids="agentIds"
          :follow-agent="followAgent"
          @select-agent="selectAgent"
          @unfollow="onUnfollow"
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

.follow-bar {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.follow-label {
  font-size: 0.7rem;
  color: #555;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.follow-btn {
  font-family: 'Courier New', monospace;
  font-size: 0.65rem;
  padding: 0.15rem 0.4rem;
  border: 1px solid;
  border-radius: 3px;
  background: transparent;
  cursor: pointer;
  transition: all 0.15s;
}

.follow-btn:hover {
  opacity: 0.8;
}

.follow-btn.active {
  font-weight: bold;
}
</style>
