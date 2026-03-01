<script setup>
import { AGENT_COLORS, VEIN_COLORS, STRUCTURE_COLORS, STRUCTURE_LABELS } from '../constants.js'
import { usePreferences } from '../composables/usePreferences.js'

const { prefs } = usePreferences()

function toggle() {
  prefs.showLegend = !prefs.showLegend
}
</script>

<template>
  <div class="legend-wrapper">
    <button
      class="legend-toggle"
      :class="{ active: prefs.showLegend }"
      title="Toggle Map Legend"
      type="button"
      :aria-expanded="prefs.showLegend"
      aria-controls="map-legend-content"
      @click="toggle"
    >
      ?
    </button>
    <Transition name="legend">
      <div
        v-if="prefs.showLegend"
        id="map-legend-content"
        class="legend-content"
      >
        <div class="legend-section">
          <h4>Agents</h4>
          <div class="legend-grid">
            <div class="legend-item">
              <span
                class="dot agent"
                :style="{ background: AGENT_COLORS['station'] }"
              />
              <span>Station</span>
            </div>
            <div class="legend-item">
              <span
                class="dot agent"
                :style="{ background: AGENT_COLORS['rover-mistral'] }"
              />
              <span>Rover</span>
            </div>
            <div class="legend-item">
              <span
                class="dot agent"
                :style="{ background: AGENT_COLORS['drone-mistral'] }"
              />
              <span>Drone</span>
            </div>
          </div>
        </div>
        <div class="legend-section">
          <h4>Veins</h4>
          <div class="legend-grid">
            <div
              v-for="(color, grade) in VEIN_COLORS"
              :key="grade"
              class="legend-item"
            >
              <span
                class="dot vein"
                :style="{ background: color }"
              />
              <span class="grade-label">{{ grade }}</span>
            </div>
          </div>
        </div>
        <div class="legend-section">
          <h4>Structures</h4>
          <div class="legend-grid">
            <div
              v-for="(color, type) in STRUCTURE_COLORS"
              :key="type"
              class="legend-item"
            >
              <span
                class="dot structure"
                :style="{ background: color }"
              />
              <span class="grade-label">{{ STRUCTURE_LABELS[type] || type }}</span>
            </div>
          </div>
        </div>
        <div class="legend-section">
          <h4>Communication</h4>
          <div class="legend-grid comm-grid">
            <div class="legend-item">
              <span
                class="comm-swatch"
                style="background: #44ccaa"
              />
              <span>Intel relay</span>
            </div>
            <div class="legend-item">
              <span
                class="comm-swatch"
                style="background: #cc8844"
              />
              <span>Command</span>
            </div>
            <div class="legend-item">
              <span
                class="comm-swatch"
                style="background: #cc4444"
              />
              <span>Alert</span>
            </div>
            <div class="legend-item">
              <span
                class="comm-swatch"
                style="background: #4488cc"
              />
              <span>Notification</span>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.legend-wrapper {
  position: absolute;
  bottom: 0.5rem;
  right: 0.5rem;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.5rem;
}

.legend-toggle {
  width: 1.2rem;
  height: 1.2rem;
  border-radius: 50%;
  border: 1px solid var(--text-muted);
  background: var(--bg-elevated);
  color: var(--text-muted);
  font-size: 0.7rem;
  font-family: var(--font-mono);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  z-index: 10;
}

.legend-toggle:hover,
.legend-toggle.active {
  border-color: var(--accent-blue);
  color: var(--accent-blue);
  background: var(--bg-card);
}

.legend-content {
  background: rgba(12, 12, 20, 0.95);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 0.5rem;
  font-size: 0.65rem;
  backdrop-filter: blur(4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  min-width: 120px;
}

.legend-section {
  margin-bottom: 0.5rem;
}

.legend-section:last-child {
  margin-bottom: 0;
}

h4 {
  font-size: 0.6rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.3rem;
  border-bottom: 1px solid var(--border-dim);
  padding-bottom: 0.1rem;
}

.legend-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.3rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  color: var(--text-secondary);
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot.agent {
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.dot.structure {
  border-radius: 2px;
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.grade-label {
  text-transform: capitalize;
}

.comm-swatch {
  width: 14px;
  height: 2px;
  flex-shrink: 0;
  border-radius: 1px;
  opacity: 0.9;
}

.comm-grid {
  grid-template-columns: 1fr;
}

/* Transitions */
.legend-enter-active,
.legend-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.legend-enter-from,
.legend-leave-to {
  opacity: 0;
  transform: translateY(5px);
}
</style>
