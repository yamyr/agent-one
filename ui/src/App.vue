<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const events = ref([])
const connected = ref(false)
let ws = null

function connect() {
  ws = new WebSocket(`ws://${window.location.host}/ws`)

  ws.onopen = () => {
    connected.value = true
  }

  ws.onmessage = (msg) => {
    const event = JSON.parse(msg.data)
    events.value.unshift(event)
    // keep last 200 events
    if (events.value.length > 200) {
      events.value.length = 200
    }
  }

  ws.onclose = () => {
    connected.value = false
    // reconnect after 2s
    setTimeout(connect, 2000)
  }

  ws.onerror = () => {
    ws.close()
  }
}

onMounted(() => {
  connect()
})

onUnmounted(() => {
  if (ws) ws.close()
})
</script>

<template>
  <div class="app">
    <header>
      <h1>Mars Mission Control</h1>
      <span class="status" :class="{ online: connected }">
        {{ connected ? 'CONNECTED' : 'DISCONNECTED' }}
      </span>
    </header>

    <main>
      <div v-if="events.length === 0" class="empty">
        Waiting for mission events...
      </div>
      <div v-for="(event, i) in events" :key="i" class="event">
        <span class="event-source">{{ event.source }}</span>
        <span class="event-type">{{ event.type }}</span>
        <span class="event-name">{{ event.name }}</span>
        <pre v-if="event.payload" class="event-payload">{{ JSON.stringify(event.payload, null, 2) }}</pre>
      </div>
    </main>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  background: #0a0a0f;
  color: #c8c8d0;
  font-family: 'Courier New', monospace;
}

.app {
  max-width: 960px;
  margin: 0 auto;
  padding: 1rem;
}

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

.empty {
  color: #555;
  padding: 2rem;
  text-align: center;
}

.event {
  padding: 0.5rem;
  border-bottom: 1px solid #1a1a1f;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: baseline;
}

.event-source {
  color: #6688cc;
  font-weight: bold;
  min-width: 80px;
}

.event-type {
  color: #888;
  font-size: 0.8rem;
}

.event-name {
  color: #ccaa44;
}

.event-payload {
  width: 100%;
  font-size: 0.75rem;
  color: #777;
  padding: 0.25rem 0 0 80px;
  white-space: pre-wrap;
}
</style>
