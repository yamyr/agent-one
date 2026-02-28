<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** 0-1 fraction */
  level: {
    type: Number,
    default: 0,
  },
})

const pct = computed(() => Math.max(0, Math.min(100, Math.round(props.level * 100))))

const barColor = computed(() => {
  const p = pct.value
  if (p > 60) return 'var(--accent-green)'
  if (p > 30) return 'var(--accent-amber)'
  return 'var(--accent-red)'
})
</script>

<template>
  <span class="battery-bar">
    <span class="battery-track">
      <span
        class="battery-fill"
        :style="{ width: pct + '%', background: barColor }"
      />
    </span>
    <span class="battery-label">{{ pct }}%</span>
  </span>
</template>

<style scoped>
.battery-bar {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.battery-track {
  display: inline-block;
  width: 3rem;
  height: 0.5rem;
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  overflow: hidden;
}

.battery-fill {
  display: block;
  height: 100%;
  border-radius: var(--radius-sm);
  transition: width 0.3s ease, background 0.3s ease;
}

.battery-label {
  font-size: 0.65rem;
  color: var(--text-muted);
  min-width: 2.2em;
  text-align: right;
}
</style>
