<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { agentColor } from '../constants.js'

const props = defineProps({
  events: {
    type: Array,
    default: () => [],
  },
})

const ROW_HEIGHT = 32
const BUFFER = 5

const container = ref(null)
const scrollTop = ref(0)
const containerHeight = ref(420)
const pinnedToTop = ref(true)
const newEventKeys = ref(new Set())

let lastSeenUid = 0

function onScroll() {
  const el = container.value
  if (!el) return
  scrollTop.value = el.scrollTop
  // Pinned to top when scrollTop is near 0 (within 5px tolerance)
  pinnedToTop.value = el.scrollTop < 5
}

const startIdx = computed(() => {
  const idx = Math.floor(scrollTop.value / ROW_HEIGHT) - BUFFER
  return Math.max(0, idx)
})

const endIdx = computed(() => {
  const visibleCount = Math.ceil(containerHeight.value / ROW_HEIGHT)
  const idx = Math.floor(scrollTop.value / ROW_HEIGHT) + visibleCount + BUFFER
  return Math.min(props.events.length, idx)
})

const visibleEvents = computed(() => props.events.slice(startIdx.value, endIdx.value))

const topSpacerHeight = computed(() => startIdx.value * ROW_HEIGHT)
const bottomSpacerHeight = computed(() => (props.events.length - endIdx.value) * ROW_HEIGHT)

// Track new events for enter animation using newest event's _uid
watch(
  () => props.events[0]?._uid ?? 0,
  (newestUid) => {
    if (newestUid > lastSeenUid && lastSeenUid > 0) {
      // Collect all new event keys since last seen
      const keys = new Set()
      for (const e of props.events) {
        const uid = e._uid ?? 0
        if (uid <= lastSeenUid) break
        keys.add(uid)
      }
      newEventKeys.value = keys

      // Clear animation class after transition completes
      setTimeout(() => {
        newEventKeys.value = new Set()
      }, 350)

      // Auto-scroll to top if pinned
      if (pinnedToTop.value) {
        nextTick(() => {
          if (container.value) {
            container.value.scrollTop = 0
          }
        })
      }
    }
    lastSeenUid = newestUid
  },
)

function updateContainerHeight() {
  if (container.value) {
    containerHeight.value = container.value.clientHeight
  }
}

let resizeObserver = null

onMounted(() => {
  updateContainerHeight()
  lastSeenUid = props.events[0]?._uid ?? 0
  if (container.value) {
    resizeObserver = new ResizeObserver(updateContainerHeight)
    resizeObserver.observe(container.value)
  }
})

onBeforeUnmount(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
})

function isNewEvent(event) {
  const key = event._uid ?? 0
  return newEventKeys.value.has(key)
}

function eventNameClass(event) {
  switch (event.name) {
    case 'mission_success':
      return 'event-name-success'
    case 'mission_aborted':
    case 'mission_failed':
    case 'alert':
      return 'event-name-error'
    case 'analyze':
    case 'dig':
      return 'event-name-resource'
    case 'move':
    case 'scan':
      return 'event-name-map'
    case 'thinking':
      return 'event-name-think'
    default:
      return 'event-name-default'
  }
}

function formatPayload(event) {
  const p = event.payload
  if (!p) return ''

  switch (event.name) {
    case 'thinking':
      return p.text || ''
    case 'move':
      if (p.from && p.to)
        return `(${p.from[0]},${p.from[1]}) \u2192 (${p.to[0]},${p.to[1]})  bat ${Math.round((p.battery ?? 0) * 100)}%`
      return ''
    case 'analyze':
      if (p.stone)
        return `${p.stone.grade} vein at (${p.position[0]},${p.position[1]}) qty=${p.stone.quantity}`
      return ''
    case 'dig':
      if (p.stone)
        return `dug ${p.stone.grade} qty=${p.stone.quantity} at (${p.position[0]},${p.position[1]})  inv=${p.inventory_count}`
      return ''
    case 'scan':
      return `peak ${p.peak} at (${p.position[0]},${p.position[1]})`
    case 'charge_rover':
      return `${p.agent_id || 'agent'} charged ${Math.round((p.battery_before ?? 0) * 100)}% \u2192 ${Math.round((p.battery_after ?? p.battery ?? 0) * 100)}%`
    case 'alert':
      return p.message || ''
    case 'state':
      return '' // skip world snapshots
    case 'mission_success':
      return `\u2713 mission complete \u2014 ${p.collected_quantity ?? '?'} collected`
    case 'mission_aborted':
      return `\u2717 mission aborted \u2014 ${p.reason || '?'}`
    case 'assign_mission':
      return p.objective || ''
    case 'recall':
      return `recall ${p.rover_id || ''}${p.reason ? ' \u2014 ' + p.reason : ''}`
    default:
      return JSON.stringify(p, null, 2)
  }
}
</script>

<template>
  <section
    class="event-log"
    role="log"
    aria-live="polite"
    aria-relevant="additions"
  >
    <h2>Event Log</h2>
    <div
      v-if="events.length === 0"
      class="skeleton-container"
    >
      <div
        v-for="w in [100, 85, 95, 70, 90, 80]"
        :key="w"
        class="skeleton-row"
        :style="{ width: w + '%' }"
      />
    </div>
    <div
      v-else
      ref="container"
      class="event-scroll-container"
      @scroll.passive="onScroll"
    >
      <div
        :style="{ height: topSpacerHeight + 'px' }"
        aria-hidden="true"
      />
      <div
        v-for="(event, i) in visibleEvents"
        :key="event._uid ?? (startIdx + i)"
        :class="['event', { 'event-enter': isNewEvent(event) }]"
        :style="{ height: ROW_HEIGHT + 'px' }"
      >
        <span
          v-if="event.tick != null"
          class="event-tick"
        >#{{ event.tick }}</span>
        <span
          class="event-source"
          :style="{ color: agentColor(event.source) }"
        >{{ event.source }}</span>
        <span class="event-type">{{ event.type }}</span>
        <span :class="['event-name', eventNameClass(event)]">{{ event.name }}</span>
        <span
          v-if="event.payload && formatPayload(event)"
          class="event-payload"
        >{{ formatPayload(event) }}</span>
      </div>
      <div
        :style="{ height: bottomSpacerHeight + 'px' }"
        aria-hidden="true"
      />
    </div>
  </section>
</template>

<style scoped>
.event-log {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  padding: 0.75rem;
}

.event-scroll-container {
  max-height: 420px;
  overflow-y: auto;
  contain: content;
}

.event {
  padding: 0.35rem 0;
  border-bottom: 1px solid var(--border-dim);
  display: flex;
  flex-wrap: nowrap;
  gap: 0.5rem;
  align-items: baseline;
  box-sizing: border-box;
  overflow: hidden;
}

.event-tick {
  color: var(--text-muted);
  font-size: 0.7rem;
  min-width: 35px;
  flex-shrink: 0;
}

.event-source {
  font-weight: bold;
  min-width: 100px;
  font-size: 0.8rem;
  flex-shrink: 0;
}

.event-type {
  color: var(--text-secondary);
  font-size: 0.75rem;
  flex-shrink: 0;
}

.event-name {
  color: var(--accent-gold);
  font-size: 0.8rem;
  flex-shrink: 0;
}

.event-name-default { color: var(--accent-gold); }
.event-name-success { color: var(--accent-green); }
.event-name-error { color: var(--accent-red); }
.event-name-resource { color: var(--accent-amber); }
.event-name-map { color: var(--accent-blue); }
.event-name-think { color: var(--accent-teal); }

.event-payload {
  font-size: 0.7rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

/* -- Skeleton loading state -- */
.skeleton-container {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.5rem 0;
}

.skeleton-row {
  height: 10px;
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  animation: pulse 1.5s infinite ease-in-out;
}

.skeleton-row:nth-child(2) { animation-delay: 0.15s; }
.skeleton-row:nth-child(3) { animation-delay: 0.3s; }
.skeleton-row:nth-child(4) { animation-delay: 0.45s; }
.skeleton-row:nth-child(5) { animation-delay: 0.6s; }
.skeleton-row:nth-child(6) { animation-delay: 0.75s; }

@keyframes pulse {
  0% { opacity: 0.3; }
  50% { opacity: 0.6; }
  100% { opacity: 0.3; }
}

/* -- Enter animation for new events -- */
.event-enter {
  animation: event-slide-in 0.3s ease both;
}

@keyframes event-slide-in {
  from {
    opacity: 0;
    transform: translateX(-12px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
</style>
