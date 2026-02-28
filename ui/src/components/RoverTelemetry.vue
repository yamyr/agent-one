<script setup>
import { computed } from 'vue'

const props = defineProps({
  rover: { type: Object, default: null },
  mission: { type: Object, default: null },
  status: { type: String, default: 'idle' },
  tick: { type: Number, default: 0 },
})

const batteryPct = computed(() => {
  if (!props.rover) return 0
  return Math.round((props.rover.battery_pct ?? 1) * 100)
})

const batteryClass = computed(() => {
  if (batteryPct.value <= 15) return 'battery-critical'
  if (batteryPct.value <= 30) return 'battery-low'
  return 'battery-ok'
})

const statusClass = computed(() => {
  if (props.status === 'success') return 'badge-success'
  if (props.status === 'failed') return 'badge-failed'
  return 'badge-running'
})
</script>

<template>
  <div class="telemetry">
    <h3>Rover Telemetry</h3>

    <div v-if="rover" class="stats">
      <div class="stat-row">
        <span class="label">Position</span>
        <span class="value">[{{ rover.position[0] }}, {{ rover.position[1] }}]</span>
      </div>
      <div class="stat-row">
        <span class="label">Battery</span>
        <span class="value" :class="batteryClass">{{ rover.battery }} / {{ rover.battery_max }}</span>
      </div>
      <div class="battery-bar-track">
        <div
          class="battery-bar-fill"
          :class="batteryClass"
          :style="{ width: batteryPct + '%' }"
        ></div>
      </div>
      <div class="stat-row">
        <span class="label">Inventory</span>
        <span class="value">{{ rover.inventory_count }} stones</span>
      </div>
      <div class="stat-row">
        <span class="label">Dist to Station</span>
        <span class="value">{{ rover.distance_to_station }} cells</span>
      </div>
    </div>

    <div v-if="mission" class="mission-section">
      <h3>Mission</h3>
      <div class="stat-row">
        <span class="label">Target</span>
        <span class="value target-kind">{{ mission.target_count }}x {{ mission.target_kind }}</span>
      </div>
      <div class="stat-row">
        <span class="label">Collected</span>
        <span class="value">{{ mission.collected_count }} / {{ mission.target_count }}</span>
      </div>
      <div class="stat-row">
        <span class="label">Status</span>
        <span class="badge" :class="statusClass">{{ status }}</span>
      </div>
      <div class="stat-row">
        <span class="label">Tick</span>
        <span class="value">{{ tick }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.telemetry {
  padding: 0.75rem;
  border: 1px solid #1a1a24;
  border-radius: 4px;
  background: #0c0c14;
}

h3 {
  font-size: 0.75rem;
  color: #555;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 0.5rem;
}

.stats, .mission-section {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.mission-section {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid #1a1a24;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
}

.label {
  color: #666;
}

.value {
  color: #c8c8d0;
}

.target-kind {
  color: #d4a020;
}

.battery-bar-track {
  height: 4px;
  background: #111;
  border-radius: 2px;
  overflow: hidden;
  margin-top: 2px;
}

.battery-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.5s ease;
}

.battery-ok { color: #44cc44; }
.battery-ok.battery-bar-fill { background: #44cc44; }
.battery-low { color: #ccaa22; }
.battery-low.battery-bar-fill { background: #ccaa22; }
.battery-critical { color: #cc4444; }
.battery-critical.battery-bar-fill { background: #cc4444; }

.badge {
  font-size: 0.7rem;
  padding: 0.1rem 0.4rem;
  border-radius: 3px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.badge-running { background: #1a2a1a; color: #44cc44; }
.badge-success { background: #1a3a1a; color: #66ee66; }
.badge-failed { background: #3a1a1a; color: #ee4444; }
</style>
