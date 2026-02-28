<script setup>
defineProps({
  toasts: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['dismiss'])

const ICONS = {
  success: '✓',
  warning: '⚠',
  error: '✗',
  info: '●',
}
</script>

<template>
  <div class="toast-container">
    <TransitionGroup name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="['toast', 'toast-' + toast.type]"
        @click="emit('dismiss', toast.id)"
      >
        <span class="toast-icon">{{ ICONS[toast.type] || ICONS.info }}</span>
        <span class="toast-msg">{{ toast.message }}</span>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-container {
  position: fixed;
  top: 0.75rem;
  right: 0.75rem;
  z-index: 200;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  pointer-events: none;
  max-width: 320px;
}

.toast {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.75rem;
  border-radius: var(--radius-md);
  font-size: 0.7rem;
  font-family: var(--font-mono);
  pointer-events: auto;
  cursor: pointer;
  border: 1px solid var(--border-subtle);
  backdrop-filter: blur(6px);
}

.toast-icon {
  font-size: 0.8rem;
  flex-shrink: 0;
}

.toast-msg {
  line-height: 1.3;
}

.toast-info {
  background: rgba(26, 26, 48, 0.92);
  color: var(--accent-blue);
  border-color: var(--accent-blue);
}

.toast-success {
  background: rgba(17, 51, 17, 0.92);
  color: var(--accent-green);
  border-color: var(--accent-green);
}

.toast-warning {
  background: rgba(42, 26, 10, 0.92);
  color: var(--accent-amber);
  border-color: var(--accent-amber);
}

.toast-error {
  background: rgba(51, 17, 17, 0.92);
  color: var(--accent-red);
  border-color: var(--accent-red);
}

/* TransitionGroup animations */
.toast-enter-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.toast-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.toast-move {
  transition: transform 0.3s ease;
}
</style>
