<script setup>
defineProps({
  mission: {
    type: Object,
    default: null,
  },
})
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
  </div>
</template>

<style scoped>
.mission-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.4rem 0.75rem;
  margin-bottom: 0.5rem;
  border: 1px solid #1a1a24;
  border-radius: 4px;
  background: #0c0c14;
  font-size: 0.75rem;
}

.mission-label {
  color: #555;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.65rem;
}

.mission-target {
  color: #b8962a;
}

.mission-progress {
  color: #c8c8d0;
  font-weight: bold;
}

.mission-status {
  margin-left: auto;
  padding: 0.15rem 0.4rem;
  border-radius: 3px;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.mission-status.running {
  background: #1a1a30;
  color: #6688cc;
}

.mission-status.success {
  background: #113311;
  color: #44cc44;
}

.mission-status.failed {
  background: #331111;
  color: #cc4444;
}
</style>
