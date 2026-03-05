<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import WorldMap from '../components/WorldMap.vue'
import MiniMap from '../components/MiniMap.vue'
import { VIEWPORT_W, VIEWPORT_H, agentColor } from '../constants.js'

const router = useRouter()

// ── Session picker state ──
const sessions = ref([])
const sessionsLoading = ref(true)
const sessionsError = ref(null)
const selectedSessionId = ref(null)
const sessionDetail = ref(null)

// ── Replay data ──
const snapshots = ref([])
const events = ref([])
const dataLoading = ref(false)
const dataError = ref(null)

// ── Playback state ──
const currentIndex = ref(0)
const playing = ref(false)
const speed = ref(1)
const speeds = [1, 2, 5, 10]
let playTimer = null

// ── Map refs ──
const worldMapRef = ref(null)
const followAgent = ref(null)
const camXVal = computed(() => worldMapRef.value?.camX ?? -10)
const camYVal = computed(() => worldMapRef.value?.camY ?? -10)
const visibleWVal = computed(() => worldMapRef.value?.visibleW ?? VIEWPORT_W)
const visibleHVal = computed(() => worldMapRef.value?.visibleH ?? VIEWPORT_H)

// ── Computed ──
const currentSnapshot = computed(() => {
  if (!snapshots.value.length) return null
  return snapshots.value[currentIndex.value] || null
})

const currentWorldState = computed(() => {
  return currentSnapshot.value?.world_state || null
})

const currentTick = computed(() => {
  return currentSnapshot.value?.tick ?? 0
})

const totalSnapshots = computed(() => snapshots.value.length)

const agentIds = computed(() => {
  if (!currentWorldState.value?.agents) return []
  return Object.keys(currentWorldState.value.agents)
})

const mobileAgents = computed(() => {
  if (!currentWorldState.value) return []
  return agentIds.value.filter(id => {
    const a = currentWorldState.value.agents[id]
    return a && a.type !== 'station'
  })
})

const currentEvents = computed(() => {
  if (!events.value.length || !currentSnapshot.value) return []
  const tick = currentSnapshot.value.tick
  const nextTick = currentIndex.value < snapshots.value.length - 1
    ? snapshots.value[currentIndex.value + 1].tick
    : tick + 1
  return events.value.filter(e => e.tick >= tick && e.tick < nextTick)
})

const allEventsUpToCurrent = computed(() => {
  if (!events.value.length || !currentSnapshot.value) return []
  const tick = currentSnapshot.value.tick
  return events.value.filter(e => e.tick <= tick).slice(-50)
})

const progressPercent = computed(() => {
  if (totalSnapshots.value <= 1) return 0
  return (currentIndex.value / (totalSnapshots.value - 1)) * 100
})

// ── Fetch sessions ──
async function fetchSessions() {
  sessionsLoading.value = true
  sessionsError.value = null
  try {
    const res = await fetch('/api/training/sessions?limit=50')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    sessions.value = await res.json()
  } catch (err) {
    sessionsError.value = err.message
    sessions.value = []
  } finally {
    sessionsLoading.value = false
  }
}

// ── Select session ──
async function selectSession(id) {
  stopPlayback()
  selectedSessionId.value = id
  currentIndex.value = 0
  snapshots.value = []
  events.value = []
  sessionDetail.value = null
  dataLoading.value = true
  dataError.value = null

  try {
    const [detailRes, snapshotsRes, eventsRes] = await Promise.all([
      fetch(`/api/training/sessions/${id}`),
      fetch(`/api/training/sessions/${id}/snapshots?limit=500`),
      fetch(`/api/training/sessions/${id}/events?limit=500`),
    ])

    if (!detailRes.ok) throw new Error(`Session detail: HTTP ${detailRes.status}`)
    if (!snapshotsRes.ok) throw new Error(`Snapshots: HTTP ${snapshotsRes.status}`)
    if (!eventsRes.ok) throw new Error(`Events: HTTP ${eventsRes.status}`)

    sessionDetail.value = await detailRes.json()
    snapshots.value = await snapshotsRes.json()
    events.value = await eventsRes.json()
  } catch (err) {
    dataError.value = err.message
  } finally {
    dataLoading.value = false
  }
}

function deselectSession() {
  stopPlayback()
  selectedSessionId.value = null
  sessionDetail.value = null
  snapshots.value = []
  events.value = []
  currentIndex.value = 0
}

// ── Playback controls ──
function togglePlay() {
  if (playing.value) {
    stopPlayback()
  } else {
    startPlayback()
  }
}

function startPlayback() {
  if (!snapshots.value.length) return
  if (currentIndex.value >= snapshots.value.length - 1) {
    currentIndex.value = 0
  }
  playing.value = true
  scheduleNextTick()
}

function stopPlayback() {
  playing.value = false
  if (playTimer) {
    clearTimeout(playTimer)
    playTimer = null
  }
}

function scheduleNextTick() {
  if (!playing.value) return
  const interval = 1000 / speed.value
  playTimer = setTimeout(() => {
    if (!playing.value) return
    if (currentIndex.value < snapshots.value.length - 1) {
      currentIndex.value++
      scheduleNextTick()
    } else {
      stopPlayback()
    }
  }, interval)
}

function setSpeed(s) {
  speed.value = s
  if (playing.value) {
    if (playTimer) clearTimeout(playTimer)
    scheduleNextTick()
  }
}

function seekTo(index) {
  stopPlayback()
  currentIndex.value = Math.max(0, Math.min(index, snapshots.value.length - 1))
}

function onProgressClick(event) {
  const rect = event.currentTarget.getBoundingClientRect()
  const x = event.clientX - rect.left
  const pct = x / rect.width
  const index = Math.round(pct * (snapshots.value.length - 1))
  seekTo(index)
}

function stepForward() {
  if (currentIndex.value < snapshots.value.length - 1) {
    stopPlayback()
    currentIndex.value++
  }
}

function stepBack() {
  if (currentIndex.value > 0) {
    stopPlayback()
    currentIndex.value--
  }
}

// ── Map interactions ──
function setFollowAgent(id) {
  followAgent.value = followAgent.value === id ? null : id
}

function onUnfollow() {
  followAgent.value = null
}

function onMinimapNavigate(x, y) {
  if (worldMapRef.value) {
    worldMapRef.value.navigateTo(x, y)
    followAgent.value = null
  }
}

// ── Formatting helpers ──
function formatDate(dateStr) {
  if (!dateStr) return '--'
  const d = new Date(dateStr)
  return d.toLocaleString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatDuration(seconds) {
  if (!seconds) return '--'
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}m ${s}s`
}

function statusClass(status) {
  if (status === 'success') return 'status-success'
  if (status === 'failed' || status === 'aborted') return 'status-error'
  return 'status-running'
}

function eventIcon(name) {
  const icons = {
    thinking: 'T',
    mission_success: 'S',
    mission_failed: 'F',
    alert: '!',
    assign_mission: 'M',
    recall: 'R',
    charge_agent: 'C',
    intel_relay: 'I',
    world_event: 'W',
  }
  return icons[name] || '*'
}

// ── Lifecycle ──
onMounted(() => {
  fetchSessions()
})

onUnmounted(() => {
  stopPlayback()
})
</script>

<template>
  <div class="replay-page">
    <!-- Header -->
    <header class="replay-header">
      <div class="replay-header__left">
        <router-link to="/" class="back-link" aria-label="Back to home">
          &larr;
        </router-link>
        <h1>Session Replay</h1>
      </div>
      <div class="replay-header__right">
        <router-link to="/app" class="nav-link">Live Simulation</router-link>
      </div>
    </header>

    <!-- Session Picker (shown when no session selected) -->
    <section v-if="!selectedSessionId" class="session-picker">
      <h2>Training Sessions</h2>

      <div v-if="sessionsLoading" class="loading-state">
        Loading sessions...
      </div>

      <div v-else-if="sessionsError" class="error-state">
        Failed to load sessions: {{ sessionsError }}
        <button class="retry-btn" @click="fetchSessions">Retry</button>
      </div>

      <div v-else-if="!sessions.length" class="empty-state">
        No training sessions found. Run a simulation with
        <code>TRAINING_DATA_ENABLED=true</code> to record sessions.
      </div>

      <div v-else class="session-list">
        <button
          v-for="s in sessions"
          :key="s.id"
          class="session-card"
          @click="selectSession(s.id)"
        >
          <div class="session-card__header">
            <span :class="['session-status', statusClass(s.status)]">
              {{ s.status }}
            </span>
            <span class="session-date">{{ formatDate(s.started_at) }}</span>
          </div>
          <div class="session-card__body">
            <span class="session-id">{{ s.id.slice(0, 8) }}...</span>
            <span v-if="s.duration_seconds" class="session-duration">
              {{ formatDuration(s.duration_seconds) }}
            </span>
            <span v-if="s.config?.active_agents" class="session-agents">
              {{ s.config.active_agents.length }} agents
            </span>
          </div>
        </button>
      </div>
    </section>

    <!-- Replay View (shown when session selected) -->
    <section v-else class="replay-view">
      <!-- Session info bar -->
      <div class="session-info">
        <button class="back-btn" @click="deselectSession" aria-label="Back to session list">
          &larr; Sessions
        </button>
        <div v-if="sessionDetail" class="session-meta">
          <span :class="['session-status', statusClass(sessionDetail.session?.status)]">
            {{ sessionDetail.session?.status }}
          </span>
          <span class="session-date">{{ formatDate(sessionDetail.session?.started_at) }}</span>
          <span v-if="sessionDetail.stats" class="session-stat">
            {{ sessionDetail.stats.snapshots }} snapshots
          </span>
          <span v-if="sessionDetail.stats" class="session-stat">
            {{ sessionDetail.stats.events }} events
          </span>
          <span v-if="sessionDetail.stats" class="session-stat">
            {{ sessionDetail.stats.turns }} turns
          </span>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="dataLoading" class="loading-state">
        Loading replay data...
      </div>

      <!-- Error -->
      <div v-else-if="dataError" class="error-state">
        Failed to load replay data: {{ dataError }}
      </div>

      <!-- No snapshots -->
      <div v-else-if="!snapshots.length" class="empty-state">
        No world snapshots recorded for this session.
      </div>

      <!-- Playback -->
      <template v-else>
        <!-- Playback Controls -->
        <div class="playback-controls">
          <div class="playback-buttons">
            <button class="ctrl-btn" @click="stepBack" :disabled="currentIndex <= 0" aria-label="Step back">
              &laquo;
            </button>
            <button class="ctrl-btn play-btn" @click="togglePlay" :aria-label="playing ? 'Pause' : 'Play'">
              {{ playing ? 'PAUSE' : 'PLAY' }}
            </button>
            <button class="ctrl-btn" @click="stepForward" :disabled="currentIndex >= totalSnapshots - 1" aria-label="Step forward">
              &raquo;
            </button>
          </div>

          <div class="speed-selector">
            <span class="speed-label">Speed:</span>
            <button
              v-for="s in speeds"
              :key="s"
              :class="['speed-btn', { active: speed === s }]"
              @click="setSpeed(s)"
            >
              {{ s }}x
            </button>
          </div>

          <div class="tick-info">
            <span class="tick-label">Tick {{ currentTick }}</span>
            <span class="tick-count">{{ currentIndex + 1 }} / {{ totalSnapshots }}</span>
          </div>
        </div>

        <!-- Progress Bar -->
        <div class="progress-bar" @click="onProgressClick" role="slider"
             :aria-valuenow="currentIndex" :aria-valuemin="0" :aria-valuemax="totalSnapshots - 1"
             aria-label="Replay progress">
          <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
          <div class="progress-thumb" :style="{ left: progressPercent + '%' }"></div>
        </div>

        <!-- Main content -->
        <div class="replay-content">
          <div class="replay-left">
            <!-- Follow bar -->
            <div v-if="mobileAgents.length" class="follow-bar">
              <span class="follow-label">Follow:</span>
              <button
                v-for="id in mobileAgents"
                :key="id"
                :class="['follow-btn', { active: followAgent === id }]"
                :style="{
                  borderColor: agentColor(id),
                  color: followAgent === id ? 'var(--bg-primary)' : agentColor(id),
                  backgroundColor: followAgent === id ? agentColor(id) : 'transparent'
                }"
                @click="setFollowAgent(id)"
              >
                {{ id }}
              </button>
              <button
                :class="['follow-btn', { active: !followAgent }]"
                :style="{
                  borderColor: 'var(--accent-free)',
                  color: !followAgent ? 'var(--bg-primary)' : 'var(--accent-free)',
                  backgroundColor: !followAgent ? 'var(--accent-free)' : 'transparent'
                }"
                @click="followAgent = null"
              >
                Free
              </button>
            </div>

            <!-- World Map -->
            <WorldMap
              ref="worldMapRef"
              :world-state="currentWorldState"
              :agent-ids="agentIds"
              :follow-agent="followAgent"
              :events="currentEvents"
              @unfollow="onUnfollow"
            />

            <!-- MiniMap -->
            <MiniMap
              :world-state="currentWorldState"
              :agent-ids="agentIds"
              :cam-x="camXVal"
              :cam-y="camYVal"
              :viewport-w="visibleWVal"
              :viewport-h="visibleHVal"
              @navigate="onMinimapNavigate"
            />
          </div>

          <!-- Event log -->
          <aside class="replay-events">
            <h2>Events</h2>
            <div v-if="!allEventsUpToCurrent.length" class="empty-events">
              No events yet
            </div>
            <div v-else class="event-list">
              <div
                v-for="(ev, i) in allEventsUpToCurrent"
                :key="i"
                :class="['event-item', { 'event-current': ev.tick === currentTick }]"
              >
                <span class="event-tick">T{{ ev.tick }}</span>
                <span class="event-icon">{{ eventIcon(ev.event_name) }}</span>
                <span class="event-name">{{ ev.event_name }}</span>
                <span v-if="ev.source" class="event-source">{{ ev.source }}</span>
              </div>
            </div>
          </aside>
        </div>
      </template>
    </section>
  </div>
</template>

<style scoped>
.replay-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 1rem;
}

/* ── Header ── */
.replay-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 0;
  border-bottom: 1px solid var(--border-separator);
  margin-bottom: 1rem;
}

.replay-header__left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.replay-header h1 {
  font-size: 1.2rem;
  color: var(--accent-blue);
}

.back-link {
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 1.2rem;
  padding: 0.2rem 0.4rem;
  border-radius: var(--radius-sm);
  transition: color 0.15s;
}

.back-link:hover {
  color: var(--text-primary);
}

.nav-link {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--accent-orange);
  text-decoration: none;
  padding: 0.25rem 0.6rem;
  border: 1px solid var(--accent-orange);
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.nav-link:hover {
  background: var(--accent-orange);
  color: var(--bg-primary);
}

/* ── Session Picker ── */
.session-picker h2 {
  margin-bottom: 1rem;
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.session-card {
  display: block;
  width: 100%;
  text-align: left;
  padding: 0.75rem 1rem;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-mono);
  transition: border-color 0.15s, background 0.15s;
}

.session-card:hover {
  border-color: var(--accent-blue);
  background: var(--bg-elevated);
}

.session-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.35rem;
}

.session-card__body {
  display: flex;
  gap: 1rem;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.session-status {
  font-size: 0.65rem;
  padding: 0.1rem 0.4rem;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
  font-weight: bold;
  letter-spacing: 0.05em;
}

.status-success {
  background: var(--bg-status-ok);
  color: var(--accent-green);
}

.status-error {
  background: var(--bg-status-error);
  color: var(--accent-red);
}

.status-running {
  background: var(--bg-status-info);
  color: var(--accent-blue);
}

.session-date {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.session-id {
  color: var(--text-dimmer);
}

.session-duration,
.session-agents {
  color: var(--text-muted);
}

/* ── Session Info Bar ── */
.session-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
}

.back-btn {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  padding: 0.2rem 0.5rem;
  border: 1px solid var(--text-muted);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-secondary);
  cursor: pointer;
  transition: border-color 0.15s;
}

.back-btn:hover {
  border-color: var(--text-primary);
  color: var(--text-primary);
}

.session-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.session-stat {
  font-size: 0.7rem;
  color: var(--text-muted);
}

/* ── Playback Controls ── */
.playback-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.5rem 0;
  flex-wrap: wrap;
}

.playback-buttons {
  display: flex;
  gap: 0.3rem;
}

.ctrl-btn {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--text-muted);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.ctrl-btn:hover:not(:disabled) {
  border-color: var(--text-primary);
  color: var(--text-primary);
}

.ctrl-btn:disabled {
  opacity: 0.3;
  cursor: default;
}

.play-btn {
  min-width: 4rem;
  border-color: var(--accent-blue);
  color: var(--accent-blue);
}

.play-btn:hover {
  background: var(--accent-blue);
  color: var(--bg-primary);
}

.speed-selector {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.speed-label {
  font-size: 0.65rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.speed-btn {
  font-family: var(--font-mono);
  font-size: 0.6rem;
  padding: 0.15rem 0.35rem;
  border: 1px solid var(--text-dimmer);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.speed-btn:hover {
  border-color: var(--text-secondary);
}

.speed-btn.active {
  border-color: var(--accent-amber);
  color: var(--accent-amber);
  background: var(--bg-status-warn);
  font-weight: bold;
}

.tick-info {
  display: flex;
  gap: 0.5rem;
  font-size: 0.7rem;
  margin-left: auto;
}

.tick-label {
  color: var(--accent-amber);
  font-weight: bold;
}

.tick-count {
  color: var(--text-muted);
}

/* ── Progress Bar ── */
.progress-bar {
  position: relative;
  width: 100%;
  height: 6px;
  background: var(--bg-input);
  border-radius: 3px;
  cursor: pointer;
  margin-bottom: 0.75rem;
}

.progress-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: var(--accent-blue);
  border-radius: 3px;
  transition: width 0.1s;
}

.progress-thumb {
  position: absolute;
  top: 50%;
  width: 12px;
  height: 12px;
  background: var(--accent-blue);
  border: 2px solid var(--bg-primary);
  border-radius: 50%;
  transform: translate(-50%, -50%);
  transition: left 0.1s;
}

/* ── Replay Content ── */
.replay-content {
  display: flex;
  gap: 0.5rem;
}

.replay-left {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 3;
  min-width: 0;
}

/* ── Events Panel ── */
.replay-events {
  flex: 1;
  min-width: 180px;
  max-width: 260px;
  padding: 0.5rem;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  max-height: 600px;
  overflow-y: auto;
}

.replay-events h2 {
  margin-bottom: 0.5rem;
}

.event-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.event-item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.2rem 0.3rem;
  font-size: 0.65rem;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
}

.event-item.event-current {
  background: var(--bg-status-info);
  color: var(--accent-blue);
}

.event-tick {
  color: var(--text-dimmer);
  min-width: 2.5rem;
}

.event-icon {
  font-weight: bold;
  color: var(--accent-amber);
  min-width: 1rem;
  text-align: center;
}

.event-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.event-source {
  color: var(--text-dimmer);
  font-size: 0.6rem;
}

.empty-events {
  color: var(--text-dimmer);
  font-size: 0.75rem;
  text-align: center;
  padding: 1rem;
}

/* ── States ── */
.loading-state,
.empty-state,
.error-state {
  padding: 2rem;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.85rem;
}

.error-state {
  color: var(--accent-red);
}

.retry-btn {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  padding: 0.25rem 0.5rem;
  margin-top: 0.5rem;
  border: 1px solid var(--accent-red);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--accent-red);
  cursor: pointer;
}

.retry-btn:hover {
  background: var(--bg-status-error);
}

code {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  background: var(--bg-input);
  padding: 0.1rem 0.3rem;
  border-radius: var(--radius-sm);
}

/* ── Responsive: Tablet (<=768px) ── */
@media (max-width: 768px) {
  .replay-page {
    padding: 0.5rem;
  }

  .replay-header {
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .replay-header h1 {
    font-size: 1rem;
  }

  .replay-content {
    flex-direction: column;
  }

  .replay-events {
    max-width: none;
    max-height: 300px;
  }

  .playback-controls {
    gap: 0.5rem;
  }
}

/* ── Responsive: Mobile (<=480px) ── */
@media (max-width: 480px) {
  .replay-page {
    padding: 0.25rem;
  }

  .replay-header h1 {
    font-size: 0.85rem;
  }

  .playback-buttons {
    gap: 0.2rem;
  }

  .ctrl-btn {
    font-size: 0.6rem;
    padding: 0.2rem 0.35rem;
  }

  .speed-btn {
    font-size: 0.55rem;
  }

  .session-card {
    padding: 0.5rem 0.75rem;
  }

  .session-card__body {
    flex-wrap: wrap;
    gap: 0.5rem;
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
