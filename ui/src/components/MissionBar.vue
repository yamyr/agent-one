<script setup>
defineProps({
  mission: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['abort'])
</script>

<template>
  <div
    v-if="mission"
    class="mission-bar"
  >
    <span class="mission-label">Mission</span>
    <span class="mission-target">collect {{ mission.target_quantity || mission.target_count }} basalt</span>
    <span class="mission-progress">{{ mission.collected_quantity || mission.collected_count || 0 }} / {{ mission.target_quantity || mission.target_count }}</span>
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

.mission-progress {
  color: var(--text-primary);
  font-weight: bold;
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
</style>
