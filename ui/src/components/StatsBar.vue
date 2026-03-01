<script setup>
import { computed, ref, watch, onUnmounted } from 'vue'
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
  eventCount: {
    type: Number,
    default: 0,
  },
  paused: {
    type: Boolean,
    default: false,
  },
})

const tick = computed(() => props.worldState?.tick ?? 0)

const { revealedCount } = useRevealedSet(() => props.worldState)

const mobileCount = computed(() => {
  if (!props.worldState) return 0
  return Object.values(props.worldState.agents || {}).filter(a => a.type !== 'station').length
})

const totalStones = computed(() => {
  if (!props.worldState) return 0
  return (props.worldState.stones || []).length
})

const collectedQty = computed(() => {
  if (!props.worldState?.mission) return 0
  return props.worldState.mission.collected_quantity || props.worldState.mission.collected_count || 0
})

const targetQty = computed(() => {
  if (!props.worldState?.mission) return 0
  return props.worldState.mission.target_quantity || props.worldState.mission.target_count || 0
})

// ── Timer with smooth interpolation ──
const displaySeconds = ref(0)
let timerHandle = null
let lastSyncTime = 0
let lastSyncValue = 0

watch(
  () => props.worldState?.elapsed_seconds,
  (serverVal) => {
    if (serverVal != null) {
      lastSyncTime = performance.now()
      lastSyncValue = serverVal
      displaySeconds.value = serverVal
    }
  },
)

function startTimer() {
  if (timerHandle) return
  timerHandle = setInterval(() => {
    if (props.paused || !lastSyncTime) return
    const elapsed = (performance.now() - lastSyncTime) / 1000
    displaySeconds.value = lastSyncValue + elapsed
  }, 200)
}

function stopTimer() {
  if (timerHandle) {
    clearInterval(timerHandle)
    timerHandle = null
  }
}

watch(() => props.paused, (isPaused) => {
  if (isPaused) {
    stopTimer()
  } else {
    lastSyncTime = performance.now()
    lastSyncValue = displaySeconds.value
    startTimer()
  }
})

// Start timer on mount if not paused
startTimer()
onUnmounted(() => stopTimer())

const timerDisplay = computed(() => {
  const total = Math.floor(displaySeconds.value)
  const mins = Math.floor(total / 60)
  const secs = total % 60
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
})
</script>

<template>
  <div class="stats-bar">
    <template v-if="worldState">
      <span class="stat">
        <span class="stat-label">Time</span>
        <span class="stat-value timer">{{ timerDisplay }}</span>
      </span>
      <span class="stat-sep" />
      <span class="stat">
        <span class="stat-label">Tick</span>
        <span class="stat-value">#{{ tick }}</span>
      </span>
      <span class="stat-sep" />
      <span class="stat">
        <span class="stat-label">Revealed</span>
        <span class="stat-value">{{ revealedCount }} tiles</span>
      </span>
      <span class="stat-sep" />
      <span class="stat">
        <span class="stat-label">Agents</span>
        <span class="stat-value">{{ mobileCount }}</span>
      </span>
      <span class="stat-sep" />
      <span class="stat">
        <span class="stat-label">Veins</span>
        <span class="stat-value">{{ totalStones }}</span>
      </span>
      <span class="stat-sep" />
      <span class="stat">
        <span class="stat-label">Collected</span>
        <span class="stat-value collected">{{ collectedQty }}<template v-if="targetQty"> / {{ targetQty }}</template></span>
      </span>
      <span class="stat-sep" />
      <span class="stat">
        <span class="stat-label">Events</span>
        <span class="stat-value">{{ eventCount }}</span>
      </span>
    </template>
    <div
      v-else
      class="skeleton-stats"
    >
      <div
        v-for="i in 7"
        :key="i"
        class="skeleton-item"
      />
    </div>
  </div>
</template>

<style scoped>
.stats-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.3rem 0.75rem;
  margin-bottom: 0.5rem;
  border: 1px solid var(--border-dim);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  font-size: 0.65rem;
  flex-wrap: wrap;
}

.stat {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.stat-label {
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.stat-value {
  color: var(--text-secondary);
  font-weight: bold;
}

.stat-value.collected {
  color: var(--accent-amber);
}

.stat-value.timer {
  font-family: var(--font-mono, 'Courier New', monospace);
  color: var(--accent-cyan, #00e5ff);
  letter-spacing: 0.05em;
}

.stat-sep {
  width: 1px;
  height: 0.7rem;
  background: var(--border-dim);
}

@media (max-width: 480px) {
  .stats-bar {
    gap: 0.3rem;
    font-size: 0.55rem;
    padding: 0.2rem 0.5rem;
  }

  .stat-sep {
    display: none;
  }
}

.skeleton-stats {
  display: flex;
  gap: 1rem;
  width: 100%;
}

.skeleton-item {
  height: 10px;
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  flex: 1;
  animation: pulse 1.5s infinite ease-in-out;
}

@keyframes pulse {
  0% { opacity: 0.3; }
  50% { opacity: 0.6; }
  100% { opacity: 0.3; }
}
</style>
