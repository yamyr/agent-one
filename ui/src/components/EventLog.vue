<script setup>
defineProps({
  events: { type: Array, default: () => [] },
})

function eventClass(event) {
  if (!event.accepted) return 'ev-failed'
  const names = (event.events || []).map(e => e.name)
  if (names.includes('stone_extracted') || names.includes('stone_picked')) return 'ev-gold'
  if (names.includes('mission_success')) return 'ev-success'
  if (names.includes('mission_failed')) return 'ev-failed'
  return 'ev-ok'
}

function formatAction(action) {
  if (!action) return '?'
  if (action.kind === 'move') return `move → [${action.to}]`
  return action.kind
}

function formatSubEvents(events) {
  if (!events || events.length === 0) return ''
  return events.map(e => e.name).join(', ')
}
</script>

<template>
  <div class="event-log">
    <h3>Event Log</h3>
    <div v-if="events.length === 0" class="empty">
      Waiting for events...
    </div>
    <div
      v-for="(ev, i) in events"
      :key="i"
      class="event-entry"
      :class="eventClass(ev)"
    >
      <span class="tick">[{{ ev.tick }}]</span>
      <span class="action">{{ formatAction(ev.action) }}</span>
      <span class="result">{{ ev.accepted ? 'OK' : 'REJECTED' }}</span>
      <span v-if="formatSubEvents(ev.events)" class="sub-events">
        {{ formatSubEvents(ev.events) }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.event-log {
  padding: 0.75rem;
  border: 1px solid #1a1a24;
  border-radius: 4px;
  background: #0c0c14;
  max-height: 300px;
  overflow-y: auto;
}

h3 {
  font-size: 0.75rem;
  color: #555;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 0.5rem;
}

.empty {
  color: #444;
  font-size: 0.8rem;
  text-align: center;
  padding: 0.5rem;
}

.event-entry {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  align-items: baseline;
  padding: 0.2rem 0;
  border-bottom: 1px solid #111118;
  font-size: 0.75rem;
}

.tick {
  color: #555;
  flex-shrink: 0;
}

.action {
  color: #c8c8d0;
  flex-shrink: 0;
}

.result {
  font-size: 0.65rem;
  padding: 0 0.3rem;
  border-radius: 2px;
}

.ev-ok .result { color: #44cc44; }
.ev-failed .result { color: #cc4444; }
.ev-gold .result { color: #d4a020; }
.ev-success .result { color: #66ee66; }

.sub-events {
  color: #666;
  font-size: 0.65rem;
}
</style>
