<script setup>
import { ref, watch, onUnmounted } from 'vue'

const props = defineProps({
  narration: {
    type: Object,
    default: null,
  },
  narrationChunk: {
    type: Object,
    default: null,
  },
  narrationEnabled: Boolean,
})

const emit = defineEmits(['toggle-narration'])

const isPlaying = ref(false)
const currentText = ref('')
const dialogueLines = ref([])
const audioQueue = ref([])
const isProcessing = ref(false)

let currentAudio = null
let typewriterQueue = []
let typewriterTimer = null

function startTypewriter() {
  if (typewriterTimer) return
  typewriterTimer = setInterval(() => {
    if (typewriterQueue.length === 0) {
      clearInterval(typewriterTimer)
      typewriterTimer = null
      return
    }
    currentText.value += typewriterQueue.shift()
  }, 30)
}

function stopTypewriter() {
  if (typewriterTimer) {
    clearInterval(typewriterTimer)
    typewriterTimer = null
  }
  typewriterQueue = []
}

onUnmounted(() => {
  stopTypewriter()
  if (currentAudio) {
    currentAudio.pause()
    currentAudio = null
  }
  audioQueue.value = []
  isProcessing.value = false
})

watch(() => props.narrationChunk, (event) => {
  if (!event || !event.text) return
  const chars = event.text.split('')
  typewriterQueue.push(...chars)
  startTypewriter()
})

watch(() => props.narration, (event) => {
  if (!event) return
  stopTypewriter()
  currentText.value = event.text || ''

  // Parse structured dialogue if available
  if (event.dialogue && Array.isArray(event.dialogue) && event.dialogue.length > 0) {
    dialogueLines.value = event.dialogue.map(d => ({
      speaker: d.speaker,
      text: d.text,
      label: d.speaker === 'COMMANDER REX' ? 'REX' : 'NOVA',
      color: d.speaker === 'COMMANDER REX' ? '#cc8844' : '#44ccaa',
    }))
  } else {
    dialogueLines.value = []
  }

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
      <span class="narrator-label">MISSION COMMS</span>
    </div>

    <Transition
      name="narration-fade"
      mode="out-in"
    >
      <div
        v-if="dialogueLines.length > 0"
        :key="'dialogue-' + dialogueLines.length"
        class="narration-text dialogue-block"
      >
        <div
          v-for="(line, idx) in dialogueLines"
          :key="idx"
          class="dialogue-line"
        >
          <span
            class="speaker-label"
            :style="{ color: line.color }"
          >{{ line.label }}:</span>
          <span class="speaker-text">{{ line.text }}</span>
        </div>
      </div>

      <div
        v-else-if="currentText"
        :key="'text'"
        class="narration-text"
      >
        {{ currentText }}
      </div>
      <div
        v-else
        :key="'idle'"
        class="narration-text idle"
      >
        Awaiting mission events...
      </div>
    </Transition>

    <div class="narration-controls">
      <button
        v-if="isPlaying"
        type="button"
        class="skip-btn"
        title="Skip narration"
        aria-label="Skip narration"
        @click="skipAudio"
      >
        SKIP
      </button>
      <button
        type="button"
        class="toggle-btn"
        :class="{ off: !narrationEnabled }"
        :title="narrationEnabled ? 'Turn voice off' : 'Turn voice on'"
        :aria-label="narrationEnabled ? 'Turn voice off' : 'Turn voice on'"
        @click="emit('toggle-narration')"
      >
        {{ narrationEnabled ? 'Voice ON' : 'Voice OFF' }}
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
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  font-size: 0.75rem;
  transition: border-color 0.3s ease;
}

.narration-bar.playing {
  border-color: var(--bg-status-narration);
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
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.65rem;
}

.narration-text {
  flex: 1;
  color: var(--text-primary);
  font-style: italic;
  line-height: 1.4;
  min-width: 0;
  overflow: hidden;
}

.narration-text:not(.dialogue-block) {
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.narration-text.idle {
  color: var(--text-dim);
  font-style: normal;
}

.dialogue-block {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-style: normal;
}

.dialogue-line {
  display: flex;
  align-items: baseline;
  gap: 0.4rem;
  line-height: 1.4;
}

.speaker-label {
  font-weight: 700;
  font-size: 0.7rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  flex-shrink: 0;
  white-space: nowrap;
}

.speaker-text {
  color: var(--text-primary);
  font-style: italic;
}

.narration-controls {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
}

.skip-btn {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  padding: 0.2rem 0.5rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--text-muted);
  background: var(--bg-input);
  color: var(--accent-amber);
  cursor: pointer;
}

.skip-btn:hover {
  border-color: var(--text-secondary);
  color: var(--accent-amber-light);
}

.toggle-btn {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  padding: 0.2rem 0.5rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--text-muted);
  background: var(--bg-input);
  color: var(--accent-green-soft);
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

/* ── Narration text fade transition ── */
.narration-fade-enter-active,
.narration-fade-leave-active {
  transition: opacity 0.3s ease;
}

.narration-fade-enter-from,
.narration-fade-leave-to {
  opacity: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .narration-bar {
    flex-wrap: wrap;
  }
  .narration-text {
    order: 3;
    width: 100%;
    flex-basis: 100%;
  }
  .narration-text:not(.dialogue-block) {
    -webkit-line-clamp: 3;
  }
  .dialogue-line {
    flex-direction: column;
    gap: 0.15rem;
  }
}
</style>
