<script setup>
import { formatMoveEvent } from '../constants.js'

defineProps({
  agentId: String,
  position: String,
  battery: String,
  events: Array,
  color: String,
})

const emit = defineEmits(['select-agent'])
</script>

<template>
  <div class="agent-pane">
    <div class="agent-header" style="cursor:pointer" @click="emit('select-agent', agentId)">
      <span class="agent-name" :style="{ color }">{{ agentId }}</span>
      <span class="agent-stats">
        {{ position }} &middot; bat {{ battery }}
      </span>
    </div>
    <div class="agent-log">
      <div v-if="!events || events.length === 0" class="empty">
        No events yet
      </div>
      <div v-for="(e, i) in (events || [])" :key="i" class="agent-event">
        <span class="ae-type" :class="e.type">{{ e.type }}</span>
        <span class="ae-name">{{ e.name }}</span>
        <span v-if="e.name === 'thinking'" class="ae-text">{{ e.payload.text }}</span>
        <span v-else-if="e.name === 'move'" class="ae-text">{{ formatMoveEvent(e.payload) }}</span>
        <span v-else-if="e.payload" class="ae-text">{{ JSON.stringify(e.payload) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.agent-pane {
  border: 1px solid #1a1a24;
  border-radius: 4px;
  background: #0c0c14;
  height: 200px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.agent-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.4rem 0.6rem;
  border-bottom: 1px solid #1a1a24;
  flex-shrink: 0;
}

.agent-name {
  font-size: 0.8rem;
  font-weight: bold;
}

.agent-stats {
  font-size: 0.7rem;
  color: #666;
}

.agent-log {
  flex: 1;
  overflow-y: auto;
  padding: 0.25rem;
}

.agent-event {
  padding: 0.2rem 0.35rem;
  font-size: 0.75rem;
  border-bottom: 1px solid #111118;
  display: flex;
  gap: 0.4rem;
  align-items: baseline;
}

.ae-type {
  font-size: 0.65rem;
  color: #555;
  flex-shrink: 0;
}

.ae-type.action {
  color: #c86040;
}

.ae-name {
  color: #ccaa44;
  flex-shrink: 0;
}

.ae-text {
  color: #888;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
