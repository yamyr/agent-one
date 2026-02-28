<script setup>
import { agentColor } from '../constants.js'

defineProps({
  events: {
    type: Array,
    default: () => [],
  },
})
</script>

<template>
  <section class="event-log">
    <h2>Event Log</h2>
    <div
      v-if="events.length === 0"
      class="empty"
    >
      Waiting for mission events...
    </div>
    <div
      v-for="(event, i) in events"
      :key="i"
      class="event"
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
      <span class="event-name">{{ event.name }}</span>
      <pre
        v-if="event.payload"
        class="event-payload"
      >{{ JSON.stringify(event.payload, null, 2) }}</pre>
    </div>
  </section>
</template>

<style scoped>
.event-log {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  padding: 0.75rem;
  max-height: 420px;
  overflow-y: auto;
}

.event {
  padding: 0.35rem 0;
  border-bottom: 1px solid var(--border-dim);
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: baseline;
}

.event-tick {
  color: var(--text-muted);
  font-size: 0.7rem;
  min-width: 35px;
}

.event-source {
  font-weight: bold;
  min-width: 100px;
  font-size: 0.8rem;
}

.event-type {
  color: var(--text-secondary);
  font-size: 0.75rem;
}

.event-name {
  color: var(--accent-gold);
  font-size: 0.8rem;
}

.event-payload {
  width: 100%;
  font-size: 0.7rem;
  color: var(--text-muted);
  padding: 0.15rem 0 0 100px;
  white-space: pre-wrap;
}
</style>
