<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

defineProps({
  show: Boolean,
})

const emit = defineEmits(['close'])

// Close on Escape key
function onKeydown(e) {
  if (e.key === 'Escape') {
    emit('close')
  }
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="help-modal">
      <div
        v-if="show"
        class="help-overlay"
        role="dialog"
        aria-modal="true"
        aria-label="Help"
        @click.self="emit('close')"
      >
        <div class="help-modal">
          <div class="help-header">
            <h2 class="help-title">Mission Control Help</h2>
            <button
              class="help-close"
              type="button"
              aria-label="Close help"
              @click="emit('close')"
            >
              ✕
            </button>
          </div>

          <div class="help-content">
            <!-- Drone Section -->
            <div class="help-section">
              <h3 class="help-section-title">
                <span class="icon-drone">◈</span>
                Drone
              </h3>
              <p class="help-text">
                Aerial reconnaissance unit capable of scanning terrain from above, mapping routes through obstacles, and relaying communications between rovers and the station.
              </p>
            </div>

            <!-- Movement Section -->
            <div class="help-section">
              <h3 class="help-section-title">
                <span class="icon-move">↔</span>
                Movement
              </h3>
              <div class="help-movement-grid">
                <div class="movement-card">
                  <span class="movement-icon">Rover</span>
                  <span class="movement-range">±1 tile/turn</span>
                  <span class="movement-desc">Ground traversal</span>
                </div>
                <div class="movement-card">
                  <span class="movement-icon">Drone</span>
                  <span class="movement-range">±2 tiles/turn</span>
                  <span class="movement-desc">Aerial flight</span>
                </div>
                <div class="movement-card">
                  <span class="movement-icon">Station</span>
                  <span class="movement-range">Fixed</span>
                  <span class="movement-desc">Base operations</span>
                </div>
              </div>
            </div>

            <!-- Limitations Section -->
            <div class="help-section">
              <h3 class="help-section-title">
                <span class="icon-limits">⚠</span>
                Limitations
              </h3>
              <ul class="help-list">
                <li>
                  <strong>Storm damage:</strong> High dust storms degrade movement and sensor effectiveness
                </li>
                <li>
                  <strong>Communication range:</strong> Direct contact or relay via drone required
                </li>
                <li>
                  <strong>Carry capacity:</strong> Rovers limited to 3 stone units, drones cannot carry
                </li>
                <li>
                  <strong>Drone battery:</strong> Cannot operate below 20% charge
                </li>
                <li>
                  <strong>Station power:</strong> Limited allocation affects charge rate
                </li>
                <li>
                  <strong>Storm events:</strong> Random storms reduce visibility, increase battery drain, and create urgency
                </li>
              </ul>
            </div>

            <!-- Battery Section -->
            <div class="help-section">
              <h3 class="help-section-title">
                <span class="icon-battery">⚡</span>
                Battery
              </h3>
              <div class="battery-info">
                <div class="battery-row">
                  <span class="battery-label">Full charge:</span>
                  <span class="battery-value">100%</span>
                </div>
                <div class="battery-row">
                  <span class="battery-label">Drone minimum:</span>
                  <span class="battery-value">20%</span>
                </div>
                <div class="battery-row">
                  <span class="battery-label">Cost per move:</span>
                  <span class="battery-value">Rover 2% | Drone 3%</span>
                </div>
                <div class="battery-row">
                  <span class="battery-label">Cost per scan:</span>
                  <span class="battery-value">Drone 5%</span>
                </div>
                <div class="battery-row">
                  <span class="battery-label">Charge rate:</span>
                  <span class="battery-value">5% per turn at station</span>
                </div>
                <div class="battery-row">
                  <span class="battery-label">Storm penalty:</span>
                  <span class="battery-value">+50% cost during storms</span>
                </div>
              </div>
            </div>

            <!-- Controls Section -->
            <div class="help-section">
              <h3 class="help-section-title">
                <span class="icon-controls">⌨</span>
                Controls
              </h3>
              <div class="controls-grid">
                <div class="control-item">
                  <kbd class="key">Space</kbd>
                  <span class="control-desc">Pause/Resume</span>
                </div>
                <div class="control-item">
                  <kbd class="key">Arrow keys</kbd>
                  <span class="control-desc">Pan camera</span>
                </div>
                <div class="control-item">
                  <kbd class="key">1-3</kbd>
                  <span class="control-desc">Follow agent</span>
                </div>
                <div class="control-item">
                  <kbd class="key">0</kbd>
                  <span class="control-desc">Free camera</span>
                </div>
                <div class="control-item">
                  <kbd class="key">Esc</kbd>
                  <span class="control-desc">Close modals</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.help-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 1rem;
}

.help-modal {
  background: var(--bg-elevated);
  border: 1px solid var(--border-medium);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 540px;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.help-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-card);
}

.help-title {
  font-size: 1rem;
  color: var(--accent-orange);
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0;
}

.help-close {
  background: none;
  border: 1px solid var(--text-dim);
  color: var(--text-secondary);
  font-size: 0.9rem;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-family: var(--font-mono);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.help-close:hover {
  color: var(--text-primary);
  border-color: var(--text-muted);
  background: var(--bg-input);
}

.help-content {
  padding: 1.25rem;
  overflow-y: auto;
}

.help-section {
  margin-bottom: 1.25rem;
}

.help-section:last-child {
  margin-bottom: 0;
}

.help-section-title {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.75rem;
  color: var(--accent-gold);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 0.5rem;
  font-weight: bold;
}

.help-section-title span:first-child {
  font-size: 1rem;
}

.help-text {
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0;
}

.help-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.help-list li {
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.5;
  padding-left: 1.2rem;
  position: relative;
  margin-bottom: 0.25rem;
}

.help-list li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: var(--accent-teal);
}

.help-list strong {
  color: var(--text-primary);
}

/* Movement Grid */
.help-movement-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
}

.movement-card {
  background: var(--bg-revealed);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 0.6rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
}

.movement-icon {
  font-size: 0.7rem;
  font-weight: bold;
  color: var(--accent-blue);
}

.movement-range {
  font-size: 0.65rem;
  color: var(--accent-gold);
}

.movement-desc {
  font-size: 0.6rem;
  color: var(--text-tertiary);
}

/* Battery Info */
.battery-info {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  background: var(--bg-revealed);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 0.75rem;
}

.battery-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.75rem;
}

.battery-label {
  color: var(--text-tertiary);
}

.battery-value {
  color: var(--accent-green-soft);
  font-weight: bold;
}

/* Controls Grid */
.controls-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
}

.control-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.key {
  background: var(--bg-input);
  border: 1px solid var(--border-medium);
  border-radius: var(--radius-sm);
  padding: 0.25rem 0.5rem;
  font-size: 0.7rem;
  color: var(--accent-blue);
  font-family: var(--font-mono);
  min-width: 60px;
  text-align: center;
}

.control-desc {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

/* Icons */
.icon-drone {
  color: var(--accent-blue);
}

.icon-move {
  color: var(--accent-teal);
}

.icon-limits {
  color: var(--accent-amber);
}

.icon-battery {
  color: var(--accent-green);
}

.icon-controls {
  color: var(--accent-orange);
}

/* Transition */
.help-modal-enter-active,
.help-modal-leave-active {
  transition: opacity 0.25s ease;
}

.help-modal-enter-active .help-modal,
.help-modal-leave-active .help-modal {
  transition: transform 0.25s ease, opacity 0.25s ease;
}

.help-modal-enter-from,
.help-modal-leave-to {
  opacity: 0;
}

.help-modal-enter-from .help-modal {
  transform: translateY(20px) scale(0.96);
  opacity: 0;
}

.help-modal-leave-to .help-modal {
  transform: translateY(10px) scale(0.98);
  opacity: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .help-modal {
    max-height: 90vh;
  }

  .help-content {
    padding: 1rem;
  }

  .help-movement-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .controls-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .help-modal {
    max-height: 95vh;
  }

  .help-header {
    padding: 0.75rem 1rem;
  }

  .help-title {
    font-size: 0.9rem;
  }

  .help-content {
    padding: 0.75rem;
  }

  .help-movement-grid {
    grid-template-columns: 1fr;
  }

  .movement-card {
    flex-direction: row;
    justify-content: space-between;
  }

  .controls-grid {
    gap: 0.4rem;
  }

  .key {
    min-width: 50px;
    padding: 0.2rem 0.4rem;
  }
}
</style>
