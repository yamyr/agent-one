<script setup>
defineProps({
  agentId: {
    type: String,
    required: true,
  },
  position: {
    type: String,
    default: '',
  },
  battery: {
    type: String,
    default: '',
  },
  inventoryCount: {
    type: Number,
    default: 0,
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
</script>

<template>
  <div class="agent-pane">
    <div
      class="agent-header"
      style="cursor:pointer"
      @click="emit('select-agent', agentId)"
    >
      <span
        class="agent-name"
        :style="{ color }"
      >{{ agentId }}</span>
      <span class="agent-stats">
        {{ position }} &middot; bat {{ battery }}
        <span
          v-if="inventoryCount > 0"
          class="agent-inv"
        >&middot; inv {{ inventoryCount }}</span>
      </span>
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
        No activity yet
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
        >think</span>
        <span
          v-else
          class="ae-type action"
        >{{ e.name }}</span>
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

.agent-inv {
  color: #b8962a;
}

.agent-mission {
  padding: 0.25rem 0.6rem;
  font-size: 0.7rem;
  color: #8a8a6a;
  border-bottom: 1px solid #1a1a24;
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
  color: #7a9a7a;
  border-bottom: 1px solid #111118;
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

.ae-type.think {
  color: #668;
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

.ae-text.action-text {
  color: #7a9a7a;
}
</style>
