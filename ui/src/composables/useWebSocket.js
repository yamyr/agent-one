import { ref, computed, onMounted, onUnmounted } from 'vue'

export function useWebSocket({ onConnect, onEvent } = {}) {
  const events = ref([])
  const connected = ref(false)
  const worldState = ref(null)
  const narration = ref(null)
  const narrationChunk = ref(null)
  let ws = null
  let eventUid = 0

  const agentEvents = computed(() => {
    const byAgent = {}
    for (const e of events.value) {
      if (e.source === 'world') continue
      if (!byAgent[e.source]) byAgent[e.source] = []
      if (byAgent[e.source].length < 50) byAgent[e.source].push(e)
    }
    return byAgent
  })

  const agentIds = computed(() => {
    if (!worldState.value) return []
    return Object.keys(worldState.value.agents)
  })

  function connect() {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    ws = new WebSocket(`${proto}//${window.location.host}/ws`)

    ws.onopen = () => {
      connected.value = true
      events.value = []
      worldState.value = null
      if (onConnect) onConnect()
    }

    ws.onmessage = (msg) => {
      let event
      try {
        event = JSON.parse(msg.data)
      } catch (e) {
        console.warn('WS: failed to parse message', e)
        return
      }
      if (event.source === 'world' && event.name === 'state') {
        worldState.value = event.payload
      } else if (event.source === 'narrator' && event.name === 'narration') {
        narration.value = event.payload
      } else if (event.source === 'narrator' && event.name === 'narration_chunk') {
        narrationChunk.value = event.payload
      } else {
        event._uid = ++eventUid
        events.value.unshift(event)
        if (events.value.length > 200) {
          events.value.length = 200
        }
        if (onEvent) onEvent(event)
      }
    }

    ws.onclose = () => {
      connected.value = false
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

  return { events, connected, worldState, agentIds, agentEvents, narration, narrationChunk }
}
