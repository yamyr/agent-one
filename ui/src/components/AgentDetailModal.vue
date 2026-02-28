<script setup>
import { agentColor } from '../constants.js'

const props = defineProps({
  agent: Object,
  agentId: String,
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
  <div class="modal-overlay" @click.self="emit('close')">
    <div class="modal" v-if="agent">
      <div class="modal-header">
        <span class="modal-title" :style="{ color: agentColor(agentId) }">{{ agentId }}</span>
        <button class="modal-close" @click="emit('close')">x</button>
      </div>
      <div class="modal-body">
        <div class="modal-section">
          <div class="modal-label">Type</div>
          <div class="modal-value">{{ agent.type || 'rover' }}</div>
        </div>
        <div class="modal-section">
          <div class="modal-label">Mission</div>
          <div class="modal-value">{{ agent.mission.objective }}</div>
        </div>
        <div class="modal-section">
          <div class="modal-label">Position</div>
          <div class="modal-value">{{ position() }}</div>
        </div>
        <div class="modal-section">
          <div class="modal-label">Battery</div>
          <div class="modal-value">{{ batteryPct() }}</div>
        </div>
        <div class="modal-section">
          <div class="modal-label">Tiles visited</div>
          <div class="modal-value">{{ agent.visited.length }}</div>
        </div>
        <div class="modal-section">
          <div class="modal-label">Tools</div>
          <div class="modal-tools">
            <div v-for="tool in (agent.tools || [])" :key="tool.name" class="tool-item">
              <span class="tool-name">{{ tool.name }}</span>
              <span class="tool-desc">{{ tool.description }}</span>
            </div>
            <div v-if="!agent.tools || agent.tools.length === 0" class="empty">
              No tools
            </div>
          </div>
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
  background: #12121a;
  border: 1px solid #2a2a38;
  border-radius: 6px;
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
  border-bottom: 1px solid #1a1a24;
}

.modal-title {
  font-weight: bold;
  font-size: 0.95rem;
}

.modal-close {
  background: none;
  border: 1px solid #333;
  color: #888;
  font-size: 0.8rem;
  padding: 0.15rem 0.45rem;
  border-radius: 3px;
  cursor: pointer;
  font-family: 'Courier New', monospace;
}

.modal-close:hover {
  color: #ccc;
  border-color: #555;
}

.modal-body {
  padding: 0.75rem 1rem;
}

.modal-section {
  margin-bottom: 0.6rem;
}

.modal-label {
  font-size: 0.65rem;
  color: #555;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 0.15rem;
}

.modal-value {
  font-size: 0.8rem;
  color: #c8c8d0;
}

.modal-tools {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.tool-item {
  background: #0e0e16;
  border: 1px solid #1a1a24;
  border-radius: 3px;
  padding: 0.4rem 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.tool-name {
  font-size: 0.8rem;
  color: #ccaa44;
  font-weight: bold;
}

.tool-desc {
  font-size: 0.7rem;
  color: #777;
}
</style>
