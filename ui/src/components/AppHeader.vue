<script setup>
defineProps({
  connected: Boolean,
  paused: Boolean,
})

const emit = defineEmits(['toggle-pause', 'reset'])
</script>

<template>
  <header>
    <h1>Mars Mission Control</h1>
    <div class="header-controls">
      <button class="reset-btn" @click="emit('reset')">RESET</button>
      <button class="pause-btn" :class="{ paused }" @click="emit('toggle-pause')">
        {{ paused ? 'RESUME' : 'PAUSE' }}
      </button>
      <span class="status" :class="{ online: connected }">
        {{ connected ? 'CONNECTED' : 'DISCONNECTED' }}
      </span>
    </div>
  </header>
</template>

<style scoped>
header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 0;
  border-bottom: 1px solid #222;
  margin-bottom: 1rem;
}

h1 {
  font-size: 1.2rem;
  color: #e06030;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.reset-btn {
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
  padding: 0.25rem 0.6rem;
  border-radius: 3px;
  border: 1px solid #555;
  background: #1a1a24;
  color: #cc4444;
  cursor: pointer;
}

.reset-btn:hover {
  border-color: #cc4444;
  color: #ee6666;
}

.pause-btn {
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
  padding: 0.25rem 0.6rem;
  border-radius: 3px;
  border: 1px solid #555;
  background: #1a1a24;
  color: #cc8844;
  cursor: pointer;
}

.pause-btn:hover {
  border-color: #888;
  color: #eebb66;
}

.pause-btn.paused {
  background: #2a1a0a;
  border-color: #cc8844;
  color: #eebb66;
}

.status {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: 3px;
  background: #331111;
  color: #cc4444;
}

.status.online {
  background: #113311;
  color: #44cc44;
}
</style>
