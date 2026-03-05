<template>
  <div class="confirm-overlay" @click.self="$emit('respond', request.request_id, false)">
    <div class="confirm-modal">
      <div class="confirm-header">
        <span class="agent-badge">{{ request.agent_id }}</span>
        <span class="confirm-label">Confirmation Required</span>
      </div>

      <div class="confirm-question">{{ request.question }}</div>

      <div class="confirm-context" v-if="request.context">
        <div class="ctx-row" v-if="request.context.position">
          <span class="ctx-label">Position:</span>
          <span>({{ request.context.position[0] }}, {{ request.context.position[1] }})</span>
        </div>
        <div class="ctx-row" v-if="request.context.battery != null">
          <span class="ctx-label">Battery:</span>
          <span :class="batteryClass">{{ (request.context.battery * 100).toFixed(0) }}%</span>
        </div>
        <div class="ctx-row" v-if="request.context.storm_phase && request.context.storm_phase !== 'clear'">
          <span class="ctx-label">Storm:</span>
          <span class="storm-active">{{ request.context.storm_phase }}
            <template v-if="request.context.storm_intensity">
              ({{ (request.context.storm_intensity * 100).toFixed(0) }}%)
            </template>
          </span>
        </div>
      </div>

      <div class="countdown-section">
        <div class="countdown-bar">
          <div class="countdown-fill" :style="{ width: countdownPct + '%' }"></div>
        </div>
        <span class="countdown-text">{{ remaining }}s</span>
      </div>

      <div class="confirm-actions">
        <button class="btn btn-confirm" @click="$emit('respond', request.request_id, true)">
          Confirm
        </button>
        <button class="btn btn-deny" @click="$emit('respond', request.request_id, false)">
          Deny
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  request: { type: Object, required: true }
})

const emit = defineEmits(['respond', 'timeout'])

const remaining = ref(props.request.timeout || 30)
const total = props.request.timeout || 30
const countdownPct = computed(() => (remaining.value / total) * 100)

const batteryClass = computed(() => {
  const b = props.request.context?.battery ?? 1
  if (b > 0.6) return 'bat-ok'
  if (b > 0.3) return 'bat-warn'
  return 'bat-crit'
})

let timer = null
onMounted(() => {
  timer = setInterval(() => {
    remaining.value--
    if (remaining.value <= 0) {
      clearInterval(timer)
      emit('timeout', props.request.request_id)
    }
  }, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.confirm-overlay {
  position: fixed;
  inset: 0;
  z-index: 400;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
}

.confirm-modal {
  background: var(--bg-elevated, #12121a);
  border: 1px solid var(--border-medium, #2a2a38);
  border-radius: var(--radius-md, 4px);
  padding: 1.25rem;
  width: 420px;
  max-width: 92vw;
  font-family: 'JetBrains Mono', monospace;
}

.confirm-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.agent-badge {
  background: rgba(204, 136, 68, 0.15);
  color: var(--accent-amber, #cc8844);
  padding: 0.15rem 0.4rem;
  border-radius: 3px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
}

.confirm-label {
  color: var(--text-primary, #c8c8d0);
  font-size: 0.8rem;
  font-weight: 600;
}

.confirm-question {
  color: var(--text-primary, #c8c8d0);
  font-size: 0.85rem;
  line-height: 1.4;
  margin-bottom: 0.75rem;
  padding: 0.5rem;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 3px;
}

.confirm-context {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 0.75rem;
  font-size: 0.7rem;
}

.ctx-row {
  display: flex;
  gap: 0.4rem;
  color: var(--text-secondary, #888);
}

.ctx-label {
  color: var(--text-muted, #555);
  min-width: 5rem;
}

.bat-ok { color: var(--accent-green, #44cc44); }
.bat-warn { color: var(--accent-amber, #cc8844); }
.bat-crit { color: var(--accent-red, #cc4444); }

.storm-active {
  color: var(--accent-red, #cc4444);
  font-weight: 600;
}

.countdown-section {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.countdown-bar {
  flex: 1;
  height: 4px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 2px;
  overflow: hidden;
}

.countdown-fill {
  height: 100%;
  background: var(--accent-blue, #6688cc);
  transition: width 1s linear;
  border-radius: 2px;
}

.countdown-text {
  color: var(--text-secondary, #888);
  font-size: 0.7rem;
  min-width: 2rem;
  text-align: right;
}

.confirm-actions {
  display: flex;
  gap: 0.5rem;
}

.btn {
  flex: 1;
  padding: 0.5rem;
  border: none;
  border-radius: var(--radius-md, 4px);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn:hover { opacity: 0.85; }

.btn-confirm {
  background: var(--accent-green, #44cc44);
  color: #000;
}

.btn-deny {
  background: var(--accent-red, #cc4444);
  color: #fff;
}

@media (max-width: 480px) {
  .confirm-modal {
    padding: 0.75rem;
  }
  .confirm-question {
    font-size: 0.75rem;
  }
}
</style>
