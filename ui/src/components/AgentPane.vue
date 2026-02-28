<script setup>
import BatteryBar from './BatteryBar.vue'
import { useI18n } from '../composables/useI18n.js'

defineProps({
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
  memory: {
    type: Array,
    default: () => [],
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
const { t } = useI18n()
</script>

<template>
  <div class="agent-pane">
    <div
      class="agent-header"
      style="cursor:pointer"
      @click="emit('select-agent', agentId)"
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
        v-if="(!memory || memory.length === 0) && (!events || events.length === 0)"
        class="empty"
      >
        {{ t('agentpane.no_activity') }}
      </div>
      <!-- Memory (recent actions from world state) -->
      <div
        v-for="(m, i) in (memory || [])"
        :key="'m-'+i"
        class="memory-entry"
      >
        {{ m }}
      </div>
      <!-- All events chronologically -->
      <div
        v-for="(e, i) in (events || [])"
        :key="'e-'+i"
        class="agent-event"
      >
        <span
          v-if="e.name === 'thinking'"
          class="ae-type think"
        >{{ t('agentpane.think') }}</span>
        <span
          v-else
          class="ae-type action"
        >{{ t('agentpane.action') }}</span>
        <span
          v-if="e.name === 'thinking'"
          class="ae-text"
        >{{ e.payload.text }}</span>
        <span
          v-else-if="e.name === 'move' && e.payload && e.payload.from"
          class="ae-text action-text"
        >
          ({{ e.payload.from[0] }},{{ e.payload.from[1] }}) → ({{ e.payload.to[0] }},{{ e.payload.to[1] }})
        </span>
        <span
          v-else
          class="ae-text action-text"
        >
          {{ e.payload && e.payload.result ? e.payload.result : '' }}
        </span>
      </div>
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

.memory-entry {
  padding: 0.15rem 0.35rem;
  font-size: 0.7rem;
  color: var(--accent-memory);
  border-bottom: 1px solid var(--border-dim);
}

.agent-event {
  padding: 0.2rem 0.35rem;
  font-size: 0.75rem;
  border-bottom: 1px solid var(--border-dim);
  display: flex;
  gap: 0.4rem;
  align-items: baseline;
}

.ae-type {
  font-size: 0.65rem;
  color: var(--text-muted);
  flex-shrink: 0;
}

.ae-type.think {
  color: var(--accent-think);
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
