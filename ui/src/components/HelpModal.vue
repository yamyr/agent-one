<script setup>
defineProps({
  visible: Boolean,
})

const emit = defineEmits(['close'])
</script>

<template>
  <Transition name="fade">
    <div
      v-if="visible"
      class="help-overlay"
      @click.self="emit('close')"
    >
      <div
        class="help-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Keyboard shortcuts"
      >
        <div class="help-header">
          <h3>Keyboard Shortcuts</h3>
          <button
            type="button"
            class="close-btn"
            aria-label="Close help"
            @click="emit('close')"
          >
            x
          </button>
        </div>
        <div class="shortcuts-grid">
          <div class="shortcut-group">
            <h4>Camera</h4>
            <div class="shortcut-row">
              <span class="keys">
                <kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd>
                <span class="or">or</span>
                <kbd>←</kbd><kbd>↑</kbd><kbd>↓</kbd><kbd>→</kbd>
              </span>
              <span class="desc">Pan camera</span>
            </div>
            <div class="shortcut-row">
              <span class="keys"><kbd>Mouse Wheel</kbd></span>
              <span class="desc">Zoom in/out</span>
            </div>
            <div class="shortcut-row">
              <span class="keys"><kbd>0</kbd></span>
              <span class="desc">Free camera</span>
            </div>
          </div>
          <div class="shortcut-group">
            <h4>Simulation</h4>
            <div class="shortcut-row">
              <span class="keys"><kbd>Space</kbd></span>
              <span class="desc">Pause / Resume</span>
            </div>
            <div class="shortcut-row">
              <span class="keys"><kbd>1</kbd>-<kbd>9</kbd></span>
              <span class="desc">Follow agent</span>
            </div>
            <div class="shortcut-row">
              <span class="keys"><kbd>Esc</kbd></span>
              <span class="desc">Close modal</span>
            </div>
            <div class="shortcut-row">
              <span class="keys"><kbd>?</kbd></span>
              <span class="desc">Toggle this help</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.help-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 300;
  backdrop-filter: blur(2px);
}

.help-modal {
  background: var(--bg-elevated);
  border: 1px solid var(--border-medium);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  width: 400px;
  max-width: 90vw;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
}

.help-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border-subtle);
}

h3 {
  font-size: 1rem;
  color: var(--accent-gold);
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0 0.5rem;
}

.close-btn:hover {
  color: var(--text-primary);
}

.shortcuts-grid {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

h4 {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.75rem;
}

.shortcut-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.6rem;
  font-size: 0.8rem;
}

.keys {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  color: var(--text-primary);
}

.or {
  font-size: 0.7rem;
  color: var(--text-muted);
  margin: 0 0.2rem;
}

kbd {
  background: var(--bg-input);
  border: 1px solid var(--border-dim);
  border-radius: 3px;
  padding: 0.1rem 0.3rem;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  min-width: 1.2rem;
  text-align: center;
  box-shadow: 0 1px 0 rgba(0,0,0,0.2);
}

.desc {
  color: var(--text-secondary);
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
