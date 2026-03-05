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

function agentModel(id) {
  if (!props.worldState) return ''
  const a = props.worldState.agents[id]
  return a && a.model ? a.model : ''
}

function messageCount(id) {
  if (!props.worldState) return 0
  const msgs = props.worldState.agent_messages || []
  return msgs.filter(m => m.to === id && !m.read).length
}

function inventorySummary(id) {
  if (!props.worldState) return ''
  const a = props.worldState.agents[id]
  if (!a || !a.inventory || a.inventory.length === 0) return ''
  const qtys = a.inventory.map(s => s.quantity || 0)
  return 'inv (' + qtys.join(' + ') + ')'
}

function missionObjective(id) {
  if (!props.worldState) return ''
  const a = props.worldState.agents[id]
  if (!a) return ''
  // Show current task (dynamic) if available, otherwise static mission objective
  if (a.tasks && a.tasks.length > 0) return a.tasks[0]
  return a.mission ? a.mission.objective : ''
}

function goalConfidence(id) {
  if (!props.worldState) return 0
  const a = props.worldState.agents[id]
  return a ? (a.goal_confidence ?? 0) : 0
}

</script>

<template>
  <section class="agent-panes">
    <template v-if="!worldState">
      <div
        v-for="i in 3"
        :key="'skeleton-'+i"
        class="agent-pane skeleton"
      >
        <div class="skeleton-header">
          <div class="skeleton-title" />
          <div class="skeleton-stats" />
        </div>
        <div class="skeleton-body" />
      </div>
    </template>
    <template v-else>
      <AgentPane
        v-for="id in agentIds"
        :key="id"
        :agent-id="id"
        :model="agentModel(id)"
        :position="agentPosition(id)"
        :battery="batteryPct(id)"
        :battery-level="batteryRaw(id)"
        :inventory-summary="inventorySummary(id)"
        :mission="missionObjective(id)"
        :events="agentEvents[id]"
        :color="agentColor(id)"
        :message-count="messageCount(id)"
        :goal-confidence="goalConfidence(id)"
        @select-agent="emit('select-agent', $event)"
      />
    </template>
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

.agent-pane.skeleton {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  height: 200px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.skeleton-header {
  padding: 0.6rem;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  justify-content: space-between;
}

.skeleton-title {
  width: 80px;
  height: 12px;
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  animation: pulse 1.5s infinite ease-in-out;
}

.skeleton-stats {
  width: 60px;
  height: 12px;
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  animation: pulse 1.5s infinite ease-in-out;
  animation-delay: 0.2s;
}

.skeleton-body {
  flex: 1;
  margin: 0.5rem;
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  opacity: 0.5;
  animation: pulse 1.5s infinite ease-in-out;
  animation-delay: 0.4s;
}

@keyframes pulse {
  0% { opacity: 0.3; }
  50% { opacity: 0.6; }
  100% { opacity: 0.3; }
}
</style>
