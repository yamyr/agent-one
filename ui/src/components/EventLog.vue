<script setup>
import { agentColor } from '../constants.js'

defineProps({
  events: {
    type: Array,
    default: () => [],
  },
})

function formatPayload(event) {
  const p = event.payload
  if (!p) return ''

  switch (event.name) {
    case 'thinking':
      return p.text || ''
    case 'move':
      if (p.from && p.to)
        return `(${p.from[0]},${p.from[1]}) → (${p.to[0]},${p.to[1]})  bat ${Math.round((p.battery ?? 0) * 100)}%`
      return ''
    case 'analyze':
      if (p.stone)
        return `${p.stone.grade} vein at (${p.position[0]},${p.position[1]}) qty=${p.stone.quantity}`
      return ''
    case 'dig':
      if (p.stone)
        return `extracted ${p.stone.grade} at (${p.position[0]},${p.position[1]})`
      return ''
    case 'pickup':
      if (p.stone)
        return `picked up ${p.stone.grade} qty=${p.stone.quantity}  inv=${p.inventory_count}`
      return ''
    case 'analyze_ground':
      return `concentration ${p.concentration} at (${p.position[0]},${p.position[1]})`
    case 'scan':
      return `peak ${p.peak} at (${p.position[0]},${p.position[1]})`
    case 'charge_rover':
      return `battery → ${Math.round((p.battery ?? 0) * 100)}%`
    case 'alert':
      return p.message || ''
    case 'state':
      return '' // skip world snapshots
    case 'mission_success':
      return `✓ mission complete — ${p.collected_quantity ?? '?'} collected`
    case 'mission_aborted':
      return `✗ mission aborted — ${p.reason || '?'}`
    case 'assign_mission':
      return p.objective || ''
    case 'recall':
      return `recall ${p.rover_id || ''}${p.reason ? ' — ' + p.reason : ''}`
    default:
      return JSON.stringify(p, null, 2)
  }
}
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
      <span
        v-if="event.payload && formatPayload(event)"
        class="event-payload"
      >{{ formatPayload(event) }}</span>
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
  font-size: 0.7rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}
</style>
