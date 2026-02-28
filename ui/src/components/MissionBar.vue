<script setup>
import { computed } from 'vue'

const props = defineProps({
  mission: {
    type: Object,
    default: null,
  },
  storm: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['abort'])

const collected = computed(() => {
  if (!props.mission) return 0
  return props.mission.collected_quantity || props.mission.collected_count || 0
})

const target = computed(() => {
  if (!props.mission) return 1
  return props.mission.target_quantity || props.mission.target_count || 1
})

const progressPct = computed(() => Math.min(100, Math.round((collected.value / target.value) * 100)))
</script>

<template>
  <div
    v-if="mission"
    class="mission-bar"
  >
    <span class="mission-label">Mission</span>
    <span class="mission-target">collect {{ target }} basalt</span>
    <span class="mission-progress-wrap">
      <span class="progress-track">
        <span
          class="progress-fill"
          :style="{ width: progressPct + '%' }"
        />
      </span>
      <span class="mission-progress">{{ collected }} / {{ target }}</span>
    </span>
    <span
      v-if="mission.in_transit_quantity"
      class="mission-transit"
    >{{ mission.in_transit_quantity }} in transit</span>
    <span
      v-if="storm && storm.phase === 'active'"
      class="storm-badge active"
    >🌪 STORM {{ Math.round((storm.intensity || 0) * 100) }}%</span>
    <span
      v-else-if="storm && storm.phase === 'warning'"
      class="storm-badge warning"
    >⚠ STORM INCOMING</span>
    <span
      class="mission-status"
      :class="mission.status"
    >{{ mission.status }}</span>
    <button
      v-if="mission.status === 'running'"
      class="abort-btn"
      @click="emit('abort')"
    >
      ABORT
    </button>
  </div>
</template>

<style scoped>
.mission-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.4rem 0.75rem;
  margin-bottom: 0.5rem;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  font-size: 0.75rem;
}

.mission-label {
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.65rem;
}

.mission-target {
  color: var(--accent-amber-dark);
}

.mission-progress-wrap {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.progress-track {
  display: inline-block;
  width: 4rem;
  height: 0.45rem;
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  overflow: hidden;
}

.progress-fill {
  display: block;
  height: 100%;
  border-radius: var(--radius-sm);
  background: var(--accent-amber);
  transition: width 0.3s ease;
}

.mission-progress {
  color: var(--text-primary);
  font-weight: bold;
}

.mission-transit {
  color: #c9a227;
  font-size: 0.7rem;
}

.mission-status {
  margin-left: auto;
  padding: 0.15rem 0.4rem;
  border-radius: var(--radius-sm);
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.mission-status.running {
  background: var(--bg-status-info);
  color: var(--accent-blue);
}

.mission-status.success {
  background: var(--bg-status-ok);
  color: var(--accent-green);
}

.mission-status.failed,
.mission-status.aborted {
  background: var(--bg-status-error);
  color: var(--accent-red);
}

.abort-btn {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--text-muted);
  background: var(--bg-input);
  color: var(--accent-red);
  cursor: pointer;
  margin-left: 0.25rem;
}

.abort-btn:hover {
  border-color: var(--accent-red);
  color: var(--accent-red-light);
}

.storm-badge {
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-sm);
  font-size: 0.65rem;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.storm-badge.active {
  background: rgba(255, 100, 50, 0.2);
  color: #ff6432;
  animation: storm-pulse 1.5s ease-in-out infinite;
}

.storm-badge.warning {
  background: rgba(255, 200, 50, 0.2);
  color: #ffc832;
}

@keyframes storm-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
