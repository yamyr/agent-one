<script setup>
import { ref, computed } from 'vue'
import { useWebSocket } from './composables/useWebSocket.js'
import { useKeyboard } from './composables/useKeyboard.js'
import { useToasts } from './composables/useToasts.js'
import { agentColor } from './constants.js'
import AppHeader from './components/AppHeader.vue'
import WorldMap from './components/WorldMap.vue'
import MiniMap from './components/MiniMap.vue'
import AgentPanes from './components/AgentPanes.vue'
import MissionBar from './components/MissionBar.vue'
import EventLog from './components/EventLog.vue'
import AgentDetailModal from './components/AgentDetailModal.vue'
import NarrationPlayer from './components/NarrationPlayer.vue'
import StatsBar from './components/StatsBar.vue'
import ToastOverlay from './components/ToastOverlay.vue'

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

const { toasts, addToast, dismiss: dismissToast } = useToasts()

function onSimEvent(event) {
  switch (event.name) {
    case 'mission_success':
      addToast(`Mission complete — ${event.payload?.collected_quantity ?? '?'} collected`, { type: 'success', duration: 6000 })
      break
    case 'mission_aborted':
      addToast(`Mission aborted — ${event.payload?.reason || 'unknown'}`, { type: 'error', duration: 6000 })
      break
    case 'alert':
      addToast(`${event.source}: ${event.payload?.message || 'Alert'}`, { type: 'warning' })
      break
    case 'analyze':
      if (event.payload?.stone)
        addToast(`${event.source}: found ${event.payload.stone.grade} vein`, { type: 'info' })
      break
    default:
      break
  }
}

const { events, connected, worldState, agentIds, agentEvents, narration, narrationChunk } = useWebSocket({ onConnect: onWsConnect, onEvent: onSimEvent })

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

// Keyboard shortcuts
useKeyboard({
  onTogglePause: () => togglePause(),
  onPanCamera: (dx, dy) => {
    if (worldMapRef.value) {
      worldMapRef.value.panCamera(dx, dy)
      followAgent.value = null
    }
  },
  onFollowAgent: (idx) => {
    if (mobileAgents.value[idx]) {
      setFollowAgent(mobileAgents.value[idx])
    }
  },
  onFreeCamera: () => { followAgent.value = null },
  onCloseModal: () => { selectedAgent.value = null },
})
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

    <StatsBar
      :world-state="worldState"
      :agent-ids="agentIds"
      :event-count="events.length"
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
            :style="{ borderColor: agentColor(id), color: followAgent === id ? 'var(--bg-primary)' : agentColor(id), backgroundColor: followAgent === id ? agentColor(id) : 'transparent' }"
            :aria-label="`Follow ${id}`"
            @click="setFollowAgent(id)"
          >
            {{ id }}
          </button>
          <button
            :class="['follow-btn', { active: !followAgent }]"
            :style="{ borderColor: 'var(--accent-free)', color: !followAgent ? 'var(--bg-primary)' : 'var(--accent-free)', backgroundColor: !followAgent ? 'var(--accent-free)' : 'transparent' }"
            aria-label="Switch to free camera"
            @click="followAgent = null"
          >
            Free
          </button>
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

    <ToastOverlay
      :toasts="toasts"
      @dismiss="dismissToast"
    />

    <Transition name="modal">
      <AgentDetailModal
        v-if="selectedAgent"
        :agent="agentData(selectedAgent)"
        :agent-id="selectedAgent"
        @close="closeAgent"
      />
    </Transition>
  </div>
</template>

<style>
:root {
  /* Backgrounds */
  --bg-primary: #0a0a0f;
  --bg-card: #0c0c14;
  --bg-elevated: #12121a;
  --bg-input: #1a1a24;
  --bg-tile: #060609;
  --bg-revealed: #0e0e16;

  /* Borders */
  --border-subtle: #1a1a24;
  --border-medium: #2a2a38;
  --border-dim: #111118;
  --border-separator: #222;

  /* Text */
  --text-primary: #c8c8d0;
  --text-muted: #555;
  --text-dim: #333;
  --text-dimmer: #444;
  --text-secondary: #888;
  --text-tertiary: #666;

  /* Accents */
  --accent-orange: #e06030;
  --accent-gold: #ccaa44;
  --accent-amber: #cc8844;
  --accent-amber-light: #eebb66;
  --accent-amber-dark: #b8962a;
  --accent-green: #44cc44;
  --accent-green-soft: #88cc88;
  --accent-red: #cc4444;
  --accent-red-light: #ee6666;
  --accent-teal: #44ccaa;
  --accent-blue: #6688cc;
  --accent-action: #c86040;
  --accent-task: #e0a040;
  --accent-memory: #7a9a7a;
  --accent-mission: #8a8a6a;
  --accent-think: #668;
  --accent-unknown: #4a4a6a;
  --accent-unknown-border: #2a2a3a;
  --accent-free: #555;
  --accent-panel-stroke: #aa8020;

  /* Status backgrounds */
  --bg-status-ok: #113311;
  --bg-status-error: #331111;
  --bg-status-info: #1a1a30;
  --bg-status-warn: #2a1a0a;
  --bg-status-narration: #2a1a30;
  --bg-minimap: #060609;
  --bg-minimap-revealed: #1a1a28;

  /* Typography */
  --font-mono: 'JetBrains Mono', monospace;

  /* Radii */
  --radius-sm: 3px;
  --radius-md: 4px;
  --radius-lg: 6px;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: var(--font-mono);
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
  color: var(--text-dimmer);
  padding: 1rem;
  text-align: center;
  font-size: 0.8rem;
}

h2 {
  font-size: 0.85rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 0.5rem;
}

/* scrollbar */
::-webkit-scrollbar {
  width: 4px;
}
::-webkit-scrollbar-track {
  background: var(--bg-primary);
}
::-webkit-scrollbar-thumb {
  background: var(--border-separator);
  border-radius: 2px;
}

/* ── Modal transition ── */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.25s ease;
}

.modal-enter-active .modal,
.modal-leave-active .modal {
  transition: transform 0.25s ease, opacity 0.25s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal {
  transform: translateY(16px) scale(0.97);
  opacity: 0;
}

.modal-leave-to .modal {
  transform: translateY(8px) scale(0.98);
  opacity: 0;
}

.follow-bar {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.follow-label {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.follow-btn {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  padding: 0.15rem 0.4rem;
  border: 1px solid;
  border-radius: var(--radius-sm);
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

:focus-visible {
  outline: 2px solid var(--accent-blue);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}

/* ── Responsive: Tablet (≤768px) ── */
@media (max-width: 768px) {
  .app {
    padding: 0.5rem;
  }

  .top-row {
    flex-direction: column;
  }

  .left-col {
    flex: none;
  }
}

/* ── Responsive: Mobile (≤480px) ── */
@media (max-width: 480px) {
  .app {
    padding: 0.25rem;
  }

  h2 {
    font-size: 0.75rem;
  }

  .follow-bar {
    gap: 0.2rem;
  }

  .follow-btn {
    font-size: 0.55rem;
    padding: 0.1rem 0.3rem;
  }
}
</style>
