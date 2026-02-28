<script setup>
import { computed } from 'vue'
import BatteryBar from './BatteryBar.vue'

const props = defineProps({
  agentId: {
    type: String,
    required: true,
  },
  model: {
    type: String,
    default: '',
  },
  position: {
    type: String,
    default: '',
  },
  battery: {
    type: String,
    default: '',
  },
  batteryLevel: {
    type: Number,
    default: 0,
  },
  inventorySummary: {
    type: String,
    default: '',
  },
  mission: {
    type: String,
    default: '',
  },
  events: {
    type: Array,
    default: () => [],
  },
  color: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['select-agent'])

// Merge consecutive thinking+action pairs into single rows
const mergedEvents = computed(() => {
  const raw = props.events || []
  const result = []
  for (let i = 0; i < raw.length; i++) {
    const e = raw[i]
    if (e.name === 'thinking') {
      const next = raw[i + 1]
      if (next && next.name !== 'thinking') {
        result.push({ ...next, reason: e.payload?.text || '' })
        i++
      }
      // Drop orphan thinking events (no following action)
      continue
    }
    result.push({ ...e, reason: '' })
  }
  return result
})

function eventText(e) {
  if (e.name === 'move' && e.payload?.from) {
    return `(${e.payload.from[0]},${e.payload.from[1]}) → (${e.payload.to[0]},${e.payload.to[1]})`
  }
  return e.payload?.result || ''
}

</script>

<template>
  <div class="agent-pane">
    <div
      class="agent-header"
      role="button"
      tabindex="0"
      :aria-label="`View details for ${agentId}`"
      style="cursor:pointer"
      @click="emit('select-agent', agentId)"
      @keydown.enter="emit('select-agent', agentId)"
      @keydown.space.prevent="emit('select-agent', agentId)"
    >
      <div class="agent-row-1">
        <span
          class="agent-name"
          :style="{ color }"
        >{{ agentId }}</span>
        <span
          v-if="model"
          class="agent-model"
        >{{ model }}</span>
      </div>
      <div class="agent-row-2">
        {{ position }}
        <span
          v-if="inventorySummary"
          class="agent-inv"
        >&middot; {{ inventorySummary }}</span>
        &middot; <BatteryBar :level="batteryLevel" />
      </div>
    </div>
    <div
      v-if="mission"
      class="agent-mission"
    >
      {{ mission }}
    </div>
    <div class="agent-log">
      <div
        v-if="mergedEvents.length === 0"
        class="empty"
      >
        No activity yet
      </div>
      <template
        v-for="(e, i) in mergedEvents"
        :key="'e-'+i"
      >
        <div
          v-if="e.name === 'task_update'"
          class="ae-task-pill"
        >
          {{ e.payload?.task || '' }}
        </div>
        <div
          v-else
          class="agent-event"
        >
          <span class="ae-type action">{{ e.name }}</span>
          <span class="ae-text action-text">{{ eventText(e) }}</span>
          <span
            v-if="e.reason"
            class="ae-reason"
          >{{ e.reason }}</span>
          <div
            v-if="e.reason"
            class="ae-tooltip"
          >
            {{ e.reason }}
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.agent-pane {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  height: 200px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.agent-header {
  padding: 0.3rem 0.6rem;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.agent-row-1 {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.agent-row-2 {
  font-size: 0.7rem;
  color: var(--text-tertiary);
  margin-top: 0.15rem;
}

.agent-name {
  font-size: 0.8rem;
  font-weight: bold;
}

.agent-model {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.agent-inv {
  color: var(--accent-amber-dark);
}

.agent-mission {
  padding: 0.25rem 0.6rem;
  font-size: 0.7rem;
  color: var(--accent-mission);
  border-bottom: 1px solid var(--border-subtle);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 0;
}

.agent-log {
  flex: 1;
  overflow-y: auto;
  padding: 0.25rem;
}

.agent-event {
  padding: 0.2rem 0.35rem;
  font-size: 0.75rem;
  border-bottom: 1px solid var(--border-dim);
  display: flex;
  gap: 0.4rem;
  align-items: baseline;
  position: relative;
}

.ae-type {
  font-size: 0.65rem;
  color: var(--text-muted);
  flex-shrink: 0;
}

.ae-type.action {
  color: var(--accent-action);
}

.ae-name {
  color: var(--accent-gold);
  flex-shrink: 0;
}

.ae-text {
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ae-text.action-text {
  color: var(--accent-memory);
}

.ae-reason {
  font-size: 0.65rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 1;
  min-width: 0;
}

.ae-tooltip {
  display: none;
  position: absolute;
  left: 0;
  top: 100%;
  z-index: 10;
  max-width: 320px;
  padding: 0.4rem 0.6rem;
  font-size: 0.65rem;
  line-height: 1.4;
  color: var(--text-primary);
  background: var(--bg-elevated);
  border: 1px solid var(--border-medium);
  border-radius: var(--radius-sm);
  white-space: pre-wrap;
  word-break: break-word;
  pointer-events: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
}

.agent-event:hover .ae-tooltip {
  display: block;
}

.ae-task-pill {
  font-size: 0.65rem;
  color: var(--accent-task);
  background: rgba(224, 160, 64, 0.08);
  border: 1px solid rgba(224, 160, 64, 0.25);
  border-radius: 9999px;
  padding: 0.15rem 0.6rem;
  margin: 0.2rem 0.1rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (max-width: 768px) {
  .agent-pane {
    height: 160px;
  }
}

@media (max-width: 480px) {
  .agent-pane {
    height: 140px;
  }

  .agent-name {
    font-size: 0.7rem;
  }

  .agent-stats {
    font-size: 0.6rem;
  }
}
</style>
