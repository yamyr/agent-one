<script setup>
import AgentPane from './AgentPane.vue'
import { agentColor } from '../constants.js'

const props = defineProps({
  worldState: {
    type: Object,
    default: null,
  },
  agentIds: {
    type: Array,
    default: () => [],
  },
  agentEvents: {
    type: Object,
    default: () => ({}),
  },
})

const emit = defineEmits(['select-agent'])

function batteryPct(id) {
  if (!props.worldState) return '?'
  const a = props.worldState.agents[id]
  return a ? Math.round(a.battery * 100) + '%' : '?'
}

function batteryRaw(id) {
  if (!props.worldState) return 0
  const a = props.worldState.agents[id]
  return a ? a.battery : 0
}

function agentPosition(id) {
  if (!props.worldState) return '?'
  const a = props.worldState.agents[id]
  if (!a) return '?'
  return `(${a.position[0]}, ${a.position[1]})`
}

function inventoryCount(id) {
  if (!props.worldState) return 0
  const a = props.worldState.agents[id]
  return a && a.inventory ? a.inventory.length : 0
}

function missionObjective(id) {
  if (!props.worldState) return ''
  const a = props.worldState.agents[id]
  if (!a) return ''
  // Show current task (dynamic) if available, otherwise static mission objective
  if (a.tasks && a.tasks.length > 0) return a.tasks[0]
  return a.mission ? a.mission.objective : ''
}

function agentMemory(id) {
  if (!props.worldState) return []
  const a = props.worldState.agents[id]
  return a && a.memory ? a.memory : []
}
</script>

<template>
  <section class="agent-panes">
    <AgentPane
      v-for="id in agentIds"
      :key="id"
      :agent-id="id"
      :position="agentPosition(id)"
      :battery="batteryPct(id)"
      :battery-level="batteryRaw(id)"
      :inventory-count="inventoryCount(id)"
      :mission="missionObjective(id)"
      :memory="agentMemory(id)"
      :events="agentEvents[id]"
      :color="agentColor(id)"
      @select-agent="emit('select-agent', $event)"
    />
  </section>
</template>

<style scoped>
.agent-panes {
  flex: 2;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 0;
}
</style>
