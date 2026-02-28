<script setup>
defineProps({
  connected: Boolean,
})
</script>

<template>
  <header>
    <h1>Mars Mission Control</h1>
    <span class="status" :class="{ online: connected }">
      {{ connected ? 'CONNECTED' : 'DISCONNECTED' }}
    </span>
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
