<script setup>
import { computed } from 'vue'

const props = defineProps({
  level: {
    type: Number,
    default: 0,
  },
})

const pct = computed(() => Math.max(0, Math.min(100, Math.round(props.level * 100))))
</script>

<template>
  <span class="budget-bar" :title="'Power budget: min ' + pct + '%'">
    <span class="budget-track">
      <span
        class="budget-fill"
        :style="{ width: pct + '%' }"
      />
    </span>
    <span class="budget-label">B:{{ pct }}%</span>
  </span>
</template>

<style scoped>
.budget-bar {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.budget-track {
  display: inline-block;
  width: 3rem;
  height: 0.5rem;
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  overflow: hidden;
}

.budget-fill {
  display: block;
  height: 100%;
  border-radius: var(--radius-sm);
  background: var(--accent-blue);
  transition: width 0.3s ease;
}

.budget-label {
  font-size: 0.65rem;
  color: var(--text-muted);
  min-width: 2.8em;
  text-align: right;
}
</style>
