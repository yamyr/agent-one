import { ref, computed, onMounted, onUnmounted } from 'vue'

export function useWebSocket({ onConnect, onEvent } = {}) {
  const events = ref([])
  const connected = ref(false)
  const worldState = ref(null)
  const narration = ref(null)
  const narrationChunk = ref(null)
  let reconnectDelay = 2000
  const RECONNECT_MAX = 30000
  let ws = null
  let eventUid = 0
  let isFirstConnect = true

  const agentEvents = computed(() => {
    const byAgent = {}
    for (const e of events.value) {
      if (e.source === 'world') continue
      const bucket = byAgent[e.source]
      if (bucket) {
        if (bucket.length < 50) bucket.push(e)
      } else {
        byAgent[e.source] = [e]
      }
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
      if (isFirstConnect) {
        events.value = []
      }
      const first = isFirstConnect
      isFirstConnect = false
      worldState.value = null
      if (onConnect) onConnect(first)
      reconnectDelay = 2000  // reset backoff on successful connection
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
          events.value.splice(200)
        }
        if (onEvent) onEvent(event)
      }
    }

    ws.onclose = () => {
      connected.value = false
      setTimeout(connect, reconnectDelay)
      reconnectDelay = Math.min(reconnectDelay * 2, RECONNECT_MAX)
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
