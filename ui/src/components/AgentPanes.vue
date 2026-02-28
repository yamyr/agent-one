<script setup>
import AgentPane from './AgentPane.vue'
import { agentColor } from '../constants.js'

const props = defineProps({
  worldState: Object,
  agentIds: Array,
  agentEvents: Object,
})

const emit = defineEmits(['select-agent'])

function batteryPct(id) {
  if (!props.worldState) return '?'
  const a = props.worldState.agents[id]
  return a ? Math.round(a.battery * 100) + '%' : '?'
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
  return a && a.mission ? a.mission.objective : ''
}
</script>

<template>
  <section class="agent-panes">
    <AgentPane
      v-for="id in agentIds" :key="id"
      :agentId="id"
      :position="agentPosition(id)"
      :battery="batteryPct(id)"
      :inventoryCount="inventoryCount(id)"
      :mission="missionObjective(id)"
      :events="agentEvents[id]"
      :color="agentColor(id)"
      @select-agent="emit('select-agent', $event)" />
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
