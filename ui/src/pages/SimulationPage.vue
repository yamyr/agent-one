<script setup>
import { ref, computed } from 'vue'
import { useWebSocket } from '../composables/useWebSocket.js'
import { useKeyboard } from '../composables/useKeyboard.js'
import { useToasts } from '../composables/useToasts.js'
import { VIEWPORT_W, VIEWPORT_H, agentColor } from '../constants.js'
import AppHeader from '../components/AppHeader.vue'
import WorldMap from '../components/WorldMap.vue'
import MiniMap from '../components/MiniMap.vue'
import AgentPanes from '../components/AgentPanes.vue'
import MissionBar from '../components/MissionBar.vue'
import EventLog from '../components/EventLog.vue'
import AgentDetailModal from '../components/AgentDetailModal.vue'
import NarrationPlayer from '../components/NarrationPlayer.vue'
import StatsBar from '../components/StatsBar.vue'
import ToastOverlay from '../components/ToastOverlay.vue'
import HelpModal from '../components/HelpModal.vue'

const selectedAgent = ref(null)
const helpVisible = ref(false)
const paused = ref(false)
const narrationEnabled = ref(true)
const worldMapRef = ref(null)
const followAgent = ref(null)  // which agent the camera follows (null = free camera)
const camXVal = computed(() => worldMapRef.value?.camX ?? -10)
const camYVal = computed(() => worldMapRef.value?.camY ?? -10)
const visibleWVal = computed(() => worldMapRef.value?.visibleW ?? VIEWPORT_W)
const visibleHVal = computed(() => worldMapRef.value?.visibleH ?? VIEWPORT_H)

const mobileAgents = computed(() => {
  if (!agentIds.value) return []
  return agentIds.value.filter(id => {
    if (!worldState.value) return false
    const a = worldState.value.agents[id]
    return a && a.type !== 'station'
  })
})


async function onWsConnect(isFirst) {
  paused.value = false
  if (isFirst) {
    fetch('/api/simulation/reset', { method: 'POST' }).catch(() => {})
  }
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
  try {
    const res = await fetch('/api/narration/toggle', { method: 'POST' })
    if (res.ok) {
      const data = await res.json()
      narrationEnabled.value = data.enabled
    }
  } catch {
    // Network error — keep current state
  }
}

async function abortMission() {
  try {
    await fetch('/api/mission/abort', { method: 'POST' })
  } catch {
    // Network error — silently ignore
  }
}

async function resetSimulation() {
  try {
    const res = await fetch('/api/simulation/reset', { method: 'POST' })
    if (res.ok) {
      paused.value = false
      events.value = []
    }
  } catch {
    // Network error — silently ignore
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
  try {
    const endpoint = paused.value ? '/api/simulation/resume' : '/api/simulation/pause'
    const res = await fetch(endpoint, { method: 'POST' })
    if (res.ok) {
      const data = await res.json()
      paused.value = data.paused
    }
  } catch {
    // Network error — keep current state
  }
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
    worldMapRef.value.navigateTo(x, y)
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
  onCloseModal: () => {
    if (selectedAgent.value) selectedAgent.value = null
    else if (helpVisible.value) helpVisible.value = false
  },
  onToggleHelp: () => { helpVisible.value = !helpVisible.value },
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
          :viewport-w="visibleWVal"
          :viewport-h="visibleHVal"
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

    <HelpModal
      :visible="helpVisible"
      @close="helpVisible = false"
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

<style scoped>
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

  .follow-bar {
    gap: 0.2rem;
  }

  .follow-btn {
    font-size: 0.55rem;
    padding: 0.1rem 0.3rem;
  }
}
</style>
