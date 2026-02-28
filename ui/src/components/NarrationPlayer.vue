<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  narration: {
    type: Object,
    default: null,
  },
  narrationEnabled: Boolean,
})

const emit = defineEmits(['toggle-narration'])

const isPlaying = ref(false)
const currentText = ref('')
const audioQueue = ref([])
const isProcessing = ref(false)

let currentAudio = null

watch(() => props.narration, (event) => {
  if (!event) return
  currentText.value = event.text || ''

  if (event.audio && props.narrationEnabled) {
    audioQueue.value.push(event.audio)
    processQueue()
  }
})

async function processQueue() {
  if (isProcessing.value || audioQueue.value.length === 0) return
  isProcessing.value = true

  while (audioQueue.value.length > 0) {
    const audioB64 = audioQueue.value.shift()
    await playAudio(audioB64)
  }

  isProcessing.value = false
}

function playAudio(base64Data) {
  return new Promise((resolve) => {
    try {
      const binaryStr = atob(base64Data)
      const bytes = new Uint8Array(binaryStr.length)
      for (let i = 0; i < binaryStr.length; i++) {
        bytes[i] = binaryStr.charCodeAt(i)
      }
      const blob = new Blob([bytes], { type: 'audio/mpeg' })
      const url = URL.createObjectURL(blob)

      if (currentAudio) {
        currentAudio.pause()
        currentAudio = null
      }

      const audio = new Audio(url)
      currentAudio = audio
      isPlaying.value = true

      audio.onended = () => {
        isPlaying.value = false
        URL.revokeObjectURL(url)
        currentAudio = null
        resolve()
      }

      audio.onerror = () => {
        isPlaying.value = false
        URL.revokeObjectURL(url)
        currentAudio = null
        resolve()
      }

      audio.play().catch(() => {
        isPlaying.value = false
        URL.revokeObjectURL(url)
        currentAudio = null
        resolve()
      })
    } catch {
      isPlaying.value = false
      resolve()
    }
  })
}

function skipAudio() {
  if (currentAudio) {
    currentAudio.pause()
    currentAudio.currentTime = currentAudio.duration || 0
  }
  audioQueue.value = []
  isPlaying.value = false
}
</script>

<template>
  <div
    class="narration-bar"
    :class="{ playing: isPlaying }"
  >
    <div class="narration-left">
      <span
        class="narrator-icon"
        :class="{ active: isPlaying }"
      >🎙</span>
      <span class="narrator-label">NARRATOR</span>
    </div>

    <div
      v-if="currentText"
      class="narration-text"
    >
      {{ currentText }}
    </div>
    <div
      v-else
      class="narration-text idle"
    >
      Awaiting mission events...
    </div>

    <div class="narration-controls">
      <button
        v-if="isPlaying"
        class="skip-btn"
        title="Skip narration"
        @click="skipAudio"
      >
        SKIP
      </button>
      <button
        class="toggle-btn"
        :class="{ off: !narrationEnabled }"
        :title="narrationEnabled ? 'Mute narrator' : 'Unmute narrator'"
        @click="emit('toggle-narration')"
      >
        {{ narrationEnabled ? '🔊' : '🔇' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.narration-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  margin-bottom: 0.5rem;
  border: 1px solid #1a1a24;
  border-radius: 4px;
  background: #0c0c14;
  font-size: 0.75rem;
  transition: border-color 0.3s ease;
}

.narration-bar.playing {
  border-color: #2a1a30;
}

.narration-left {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
}

.narrator-icon {
  font-size: 1rem;
  opacity: 0.4;
  transition: opacity 0.3s ease;
}

.narrator-icon.active {
  opacity: 1;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.narrator-label {
  color: #555;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.65rem;
}

.narration-text {
  flex: 1;
  color: #c8c8d0;
  font-style: italic;
  line-height: 1.4;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.narration-text.idle {
  color: #333;
  font-style: normal;
}

.narration-controls {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
}

.skip-btn {
  font-family: 'Courier New', monospace;
  font-size: 0.65rem;
  padding: 0.2rem 0.5rem;
  border-radius: 3px;
  border: 1px solid #555;
  background: #1a1a24;
  color: #cc8844;
  cursor: pointer;
}

.skip-btn:hover {
  border-color: #888;
  color: #eebb66;
}

.toggle-btn {
  font-size: 0.9rem;
  padding: 0.15rem 0.3rem;
  border-radius: 3px;
  border: 1px solid transparent;
  background: none;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.toggle-btn:hover {
  opacity: 1;
}

.toggle-btn.off {
  opacity: 0.3;
}

/* Responsive */
@media (max-width: 768px) {
  .narration-bar {
    flex-wrap: wrap;
  }
  .narration-text {
    order: 3;
    width: 100%;
    -webkit-line-clamp: 3;
  }
}
</style>
