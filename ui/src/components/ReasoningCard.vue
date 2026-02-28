<script setup>
const props = defineProps({
  structured: { type: Object, default: () => ({}) },
})

function isChosenOption(opt) {
  const decision = (props.structured.decision || '').toLowerCase()
  const optLower = opt.toLowerCase()
  return decision.includes(optLower) || optLower.includes(decision)
}
</script>

<template>
  <div
    class="reasoning-card"
    :class="'risk-' + (structured.risk || 'low')"
  >
    <div
      v-if="structured.situation"
      class="rc-row"
    >
      <span class="rc-label">SIT</span>
      <span class="rc-value">{{ structured.situation }}</span>
    </div>
    <div
      v-if="structured.options?.length"
      class="rc-row rc-options"
    >
      <span class="rc-label">OPT</span>
      <span class="rc-value">
        <span
          v-for="(o, j) in structured.options"
          :key="j"
          class="rc-opt"
          :class="{ chosen: isChosenOption(o) }"
        >{{ o }}</span>
      </span>
    </div>
    <div
      v-if="structured.decision"
      class="rc-row"
    >
      <span class="rc-label">DEC</span>
      <span class="rc-value rc-decision">{{ structured.decision }}</span>
    </div>
    <div
      v-if="structured.risk"
      class="rc-row"
    >
      <span class="rc-label">RISK</span>
      <span
        class="rc-value rc-risk"
        :class="'risk-text-' + structured.risk"
      >{{ structured.risk }}</span>
    </div>
  </div>
</template>

<style scoped>
.reasoning-card {
  font-size: 0.65rem;
  border-left: 3px solid var(--accent-action, #4ade80);
  border-radius: 4px;
  padding: 0.2rem 0.35rem;
  margin: 0.15rem 0;
  background: rgba(74, 222, 128, 0.06);
  animation: rc-fade-in 0.3s ease;
}

.reasoning-card.risk-medium {
  border-left-color: #f59e0b;
  background: rgba(245, 158, 11, 0.06);
}

.reasoning-card.risk-high {
  border-left-color: #ef4444;
  background: rgba(239, 68, 68, 0.06);
}

.rc-row {
  display: flex;
  gap: 0.3rem;
  padding: 0.1rem 0;
}

.rc-label {
  font-weight: 700;
  color: var(--text-muted, #888);
  flex-shrink: 0;
  min-width: 2.2rem;
}

.rc-value {
  color: var(--text-secondary, #ccc);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rc-decision {
  font-weight: 600;
  color: var(--text-primary, #eee);
}

.rc-options {
  flex-wrap: wrap;
}

.rc-opt {
  background: rgba(255, 255, 255, 0.06);
  border-radius: 3px;
  padding: 0 0.25rem;
  margin-right: 0.2rem;
}

.rc-opt.chosen {
  background: rgba(74, 222, 128, 0.18);
  color: #4ade80;
  font-weight: 600;
}

.risk-text-low { color: #4ade80; }
.risk-text-medium { color: #f59e0b; }
.risk-text-high { color: #ef4444; }

@keyframes rc-fade-in {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
