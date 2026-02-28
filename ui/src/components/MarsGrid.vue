<script setup>
import { computed } from 'vue'

const props = defineProps({
  knownCells: { type: Array, default: () => [] },
  roverPosition: { type: Array, default: () => [0, 0] },
  stationPosition: { type: Array, default: () => [0, 0] },
  gridSize: { type: Number, default: 12 },
})

const cellLookup = computed(() => {
  const map = {}
  for (const cell of props.knownCells) {
    const [x, y] = cell.coord
    map[`${x},${y}`] = cell
  }
  return map
})

const totalCells = computed(() => props.gridSize * props.gridSize)

function coordX(idx) { return (idx - 1) % props.gridSize }
function coordY(idx) { return Math.floor((idx - 1) / props.gridSize) }

function cellClass(x, y) {
  const cell = cellLookup.value[`${x},${y}`]
  if (!cell) return 'cell fog'
  const classes = ['cell', 'revealed']
  if (cell.dug) classes.push('dug')
  if (cell.terrain === 'rough') classes.push('rough')
  return classes.join(' ')
}

function isRover(x, y) {
  return x === props.roverPosition[0] && y === props.roverPosition[1]
}

function isStation(x, y) {
  return x === props.stationPosition[0] && y === props.stationPosition[1]
}

function stoneKind(x, y) {
  const cell = cellLookup.value[`${x},${y}`]
  if (!cell || !cell.stone) return null
  return cell.stone.kind
}
</script>

<template>
  <div class="grid-container">
    <div
      class="grid"
      :style="{ gridTemplateColumns: `repeat(${gridSize}, 1fr)` }"
    >
      <div
        v-for="idx in totalCells"
        :key="idx"
        :class="cellClass(coordX(idx), coordY(idx))"
      >
        <span
          v-if="isRover(coordX(idx), coordY(idx))"
          class="marker rover-marker"
        >R</span>
        <span
          v-else-if="isStation(coordX(idx), coordY(idx))"
          class="marker station-marker"
        >S</span>
        <span
          v-else-if="stoneKind(coordX(idx), coordY(idx)) === 'precious'"
          class="stone precious-stone"
        ></span>
        <span
          v-else-if="stoneKind(coordX(idx), coordY(idx)) === 'common'"
          class="stone common-stone"
        ></span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.grid-container {
  width: 100%;
  max-width: 520px;
}

.grid {
  display: grid;
  gap: 2px;
}

.cell {
  aspect-ratio: 1;
  border-radius: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: bold;
  transition: background 0.3s ease;
}

.fog {
  background: #0e0e14;
}

.revealed {
  background: #1a1a28;
}

.revealed.rough {
  background: #1c1818;
}

.revealed.dug {
  background: #1e1610;
}

.marker {
  font-family: 'Courier New', monospace;
  font-weight: bold;
  font-size: 0.75rem;
}

.rover-marker {
  color: #e06030;
  animation: pulse 1.5s ease-in-out infinite;
}

.station-marker {
  color: #44cc44;
}

.stone {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.precious-stone {
  background: #d4a020;
  box-shadow: 0 0 4px #d4a02088;
}

.common-stone {
  background: #666;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.2); }
}
</style>
