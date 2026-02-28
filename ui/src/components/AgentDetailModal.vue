<script setup>
import { agentColor, VEIN_COLORS } from '../constants.js'

const props = defineProps({
  agent: {
    type: Object,
    default: null,
  },
  agentId: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['close'])

function position() {
  if (!props.agent) return '?'
  return `(${props.agent.position[0]}, ${props.agent.position[1]})`
}

function batteryPct() {
  if (!props.agent) return '?'
  return Math.round(props.agent.battery * 100) + '%'
}
</script>

<template>
  <div
    class="modal-overlay"
    @click.self="emit('close')"
  >
    <div
      v-if="agent"
      class="modal"
    >
      <div class="modal-header">
        <span
          class="modal-title"
          :style="{ color: agentColor(agentId) }"
        >{{ agentId }}</span>
        <button
          class="modal-close"
          @click="emit('close')"
        >
          x
        </button>
      </div>
      <div class="modal-body">
        <div class="modal-section">
          <div class="modal-label">
            Type
          </div>
          <div class="modal-value">
            {{ agent.type || 'rover' }}
          </div>
        </div>
        <div class="modal-section">
          <div class="modal-label">
            Mission
          </div>
          <div class="modal-value">
            {{ agent.mission.objective }}
          </div>
        </div>
        <div
          v-if="agent.tasks && agent.tasks.length"
          class="modal-section"
        >
          <div class="modal-label">
            Current Task
          </div>
          <div class="modal-value task-value">
            {{ agent.tasks[0] }}
          </div>
        </div>
        <div class="modal-section">
          <div class="modal-label">
            Position
          </div>
          <div class="modal-value">
            {{ position() }}
          </div>
        </div>
        <div class="modal-section">
          <div class="modal-label">
            Battery
          </div>
          <div class="modal-value">
            {{ batteryPct() }}
          </div>
        </div>
        <div class="modal-section">
          <div class="modal-label">
            Tiles visited
          </div>
          <div class="modal-value">
            {{ agent.visited.length }}
          </div>
        </div>
        <div
          v-if="agent.inventory"
          class="modal-section"
        >
          <div class="modal-label">
            Inventory
          </div>
          <div
            v-if="agent.inventory.length === 0"
            class="modal-value"
          >
            Empty
          </div>
          <div
            v-else
            class="modal-inv"
          >
            <span
              v-for="(stone, i) in agent.inventory"
              :key="i"
              class="inv-stone"
              :style="{ color: VEIN_COLORS[stone.grade || 'unknown'], borderColor: VEIN_COLORS[stone.grade || 'unknown'] + '44' }"
            >
              {{ (stone.grade || 'unknown').toUpperCase() }} <template v-if="stone.quantity">&times;{{ stone.quantity }}</template>
            </span>
          </div>
        </div>
        <div class="modal-section">
          <div class="modal-label">
            Tools
          </div>
          <div class="modal-tools">
            <div
              v-for="tool in (agent.tools || [])"
              :key="tool.name"
              class="tool-item"
            >
              <span class="tool-name">{{ tool.name }}</span>
              <span class="tool-desc">{{ tool.description }}</span>
            </div>
            <div
              v-if="!agent.tools || agent.tools.length === 0"
              class="empty"
            >
              No tools
            </div>
          </div>
        </div>
        <div
          v-if="agent.last_context"
          class="modal-section"
        >
          <div class="modal-label">
            System Prompt
          </div>
          <pre class="modal-context">{{ agent.last_context }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: var(--bg-elevated);
  border: 1px solid var(--border-medium);
  border-radius: var(--radius-lg);
  width: 380px;
  max-width: 90vw;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--border-subtle);
}

.modal-title {
  font-weight: bold;
  font-size: 0.95rem;
}

.modal-close {
  background: none;
  border: 1px solid var(--text-dim);
  color: var(--text-secondary);
  font-size: 0.8rem;
  padding: 0.15rem 0.45rem;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-family: var(--font-mono);
}

.modal-close:hover {
  color: var(--text-primary);
  border-color: var(--text-muted);
}

.modal-body {
  padding: 0.75rem 1rem;
}

.modal-section {
  margin-bottom: 0.6rem;
}

.modal-label {
  font-size: 0.65rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 0.15rem;
}

.modal-value {
  font-size: 0.8rem;
  color: var(--text-primary);
}

.task-value {
  color: var(--accent-task);
}

.modal-tools {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.tool-item {
  background: var(--bg-revealed);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 0.4rem 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.tool-name {
  font-size: 0.8rem;
  color: var(--accent-gold);
  font-weight: bold;
}

.tool-desc {
  font-size: 0.7rem;
  color: var(--text-tertiary);
}

.modal-inv {
  display: flex;
  gap: 0.3rem;
  flex-wrap: wrap;
}

.inv-stone {
  font-size: 0.7rem;
  padding: 0.15rem 0.4rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  background: var(--bg-revealed);
  font-weight: bold;
  letter-spacing: 0.03em;
}

.inv-stone.core {
  color: var(--accent-amber-dark);
  border-color: #3a2a0a;
}

.inv-stone.basalt {
  color: var(--text-secondary);
  border-color: var(--text-dim);
}

.inv-stone.unknown {
  color: var(--accent-unknown);
  border-color: var(--accent-unknown-border);
}

.modal-context {
  font-size: 0.7rem;
  color: var(--accent-memory);
  background: var(--bg-primary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 0.5rem;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 300px;
  overflow-y: auto;
  font-family: var(--font-mono);
  line-height: 1.4;
}
</style>
