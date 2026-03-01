<template>
  <div class="voice-commander">
    <div class="commander-label">COMMANDER</div>

    <div class="commander-controls">
      <button
        class="mic-button"
        :class="{ recording: state === 'recording', error: state === 'error' }"
        @mousedown.prevent="startRecording"
        @mouseup.prevent="stopRecording"
        @mouseleave="cancelIfRecording"
        @touchstart.prevent="startRecording"
        @touchend.prevent="stopRecording"
        :disabled="state === 'transcribing'"
        :aria-label="state === 'recording' ? 'Release to send' : 'Hold to talk'"
      >
        <span class="mic-icon" v-if="state !== 'transcribing'">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="9" y="1" width="6" height="12" rx="3" />
            <path d="M19 10v1a7 7 0 0 1-14 0v-1" />
            <line x1="12" y1="19" x2="12" y2="23" />
            <line x1="8" y1="23" x2="16" y2="23" />
          </svg>
        </span>
        <span class="spinner" v-else></span>
        <span class="rec-dot" v-if="state === 'recording'">●</span>
      </button>

      <div class="status-area">
        <div class="status-line">
          <span v-if="state === 'idle'" class="status-text idle">HOLD MIC TO TRANSMIT</span>
          <span v-else-if="state === 'recording'" class="status-text rec">REC {{ elapsed }}s</span>
          <span v-else-if="state === 'transcribing'" class="status-text processing">DECODING TRANSMISSION...</span>
          <span v-else-if="state === 'error'" class="status-text err">{{ errorMsg }}</span>
        </div>

        <div
          class="transcription"
          v-if="displayText"
          :key="displayText"
        >
          <span class="tx-prefix">&gt;</span>
          <span class="tx-text">{{ displayText }}</span>
        </div>
      </div>
    </div>

    <div class="signal-bar" :class="state">
      <div class="signal-fill"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  voiceTranscription: {
    type: Object,
    default: null
  }
})

const state = ref('idle') // idle | recording | transcribing | error
const errorMsg = ref('')
const elapsed = ref(0)
const displayText = ref('')

let mediaRecorder = null
let audioChunks = []
let stream = null
let elapsedTimer = null

const startRecording = async () => {
  if (state.value === 'transcribing') return

  errorMsg.value = ''
  audioChunks = []
  elapsed.value = 0

  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  } catch (err) {
    state.value = 'error'
    if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
      errorMsg.value = 'MIC ACCESS DENIED'
    } else {
      errorMsg.value = 'MIC UNAVAILABLE'
    }
    return
  }

  let mimeType = 'audio/webm;codecs=opus'
  if (!MediaRecorder.isTypeSupported(mimeType)) {
    mimeType = 'audio/webm'
  }

  try {
    mediaRecorder = new MediaRecorder(stream, { mimeType })
  } catch {
    mediaRecorder = new MediaRecorder(stream)
  }

  mediaRecorder.ondataavailable = (e) => {
    if (e.data.size > 0) audioChunks.push(e.data)
  }

  mediaRecorder.onstop = () => {
    clearInterval(elapsedTimer)
    sendAudio()
    cleanupStream()
  }

  mediaRecorder.start(100)
  state.value = 'recording'

  elapsedTimer = setInterval(() => {
    elapsed.value++
  }, 1000)
}

const stopRecording = () => {
  if (state.value !== 'recording' || !mediaRecorder) return
  mediaRecorder.stop()
}

const cancelIfRecording = () => {
  if (state.value === 'recording') {
    stopRecording()
  }
}

const cleanupStream = () => {
  if (stream) {
    for (const t of stream.getTracks()) t.stop()
    stream = null
  }
}

const sendAudio = async () => {
  if (audioChunks.length === 0) {
    state.value = 'idle'
    return
  }

  state.value = 'transcribing'

  const blob = new Blob(audioChunks, { type: mediaRecorder?.mimeType || 'audio/webm' })
  const formData = new FormData()
  formData.append('audio', blob, 'command.webm')

  try {
    const res = await fetch('/api/voice/command', {
      method: 'POST',
      body: formData
    })

    if (!res.ok) {
      const detail = await res.text().catch(() => '')
      throw new Error(detail || `HTTP ${res.status}`)
    }

    state.value = 'idle'
  } catch {
    state.value = 'error'
    errorMsg.value = 'TRANSMISSION FAILED'
    setTimeout(() => {
      if (state.value === 'error') state.value = 'idle'
    }, 4000)
  }
}

watch(
  () => props.voiceTranscription,
  (val) => {
    if (val?.text) {
      displayText.value = val.text
    }
  },
  { deep: true }
)

onBeforeUnmount(() => {
  clearInterval(elapsedTimer)
  cleanupStream()
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
})
</script>

<style scoped>
.voice-commander {
  background: var(--bg-card, #0c0c14);
  border: 1px solid var(--border-subtle, #1a1a24);
  border-radius: var(--radius-md, 4px);
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  position: relative;
  overflow: hidden;
}

.commander-label {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: 0.85rem;
  color: var(--text-muted, #555);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  line-height: 1;
}

.commander-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ── Mic Button ── */
.mic-button {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 2px solid var(--border-medium, #2a2a38);
  background: var(--bg-input, #1a1a24);
  color: var(--text-secondary, #888);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
  transition: border-color 0.2s, color 0.2s, box-shadow 0.2s;
  -webkit-user-select: none;
  user-select: none;
  touch-action: none;
}

.mic-button:hover:not(:disabled) {
  border-color: var(--text-secondary, #888);
  color: var(--text-primary, #c8c8d0);
}

.mic-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mic-button.recording {
  border-color: var(--accent-red, #cc4444);
  color: var(--accent-red-light, #ee6666);
  box-shadow: 0 0 12px rgba(204, 68, 68, 0.3), inset 0 0 8px rgba(204, 68, 68, 0.1);
  animation: mic-pulse 1.2s ease-in-out infinite;
}

.mic-button.error {
  border-color: var(--accent-orange, #e06030);
  color: var(--accent-orange, #e06030);
}

@keyframes mic-pulse {
  0%, 100% { box-shadow: 0 0 8px rgba(204, 68, 68, 0.2); }
  50% { box-shadow: 0 0 20px rgba(204, 68, 68, 0.5), inset 0 0 10px rgba(204, 68, 68, 0.15); }
}

.mic-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.rec-dot {
  position: absolute;
  top: 2px;
  right: 1px;
  font-size: 8px;
  color: var(--accent-red, #cc4444);
  animation: dot-blink 0.8s ease-in-out infinite;
}

@keyframes dot-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}

/* ── Spinner ── */
.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-medium, #2a2a38);
  border-top-color: var(--accent-gold, #ccaa44);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── Status ── */
.status-area {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.status-line {
  display: flex;
  align-items: center;
}

.status-text {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: 0.7rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.status-text.idle {
  color: var(--text-muted, #555);
}

.status-text.rec {
  color: var(--accent-red-light, #ee6666);
  animation: rec-flash 1s step-end infinite;
}

@keyframes rec-flash {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text.processing {
  color: var(--accent-gold, #ccaa44);
}

.status-text.err {
  color: var(--accent-orange, #e06030);
}

/* ── Transcription ── */
.transcription {
  display: flex;
  align-items: baseline;
  gap: 6px;
  animation: tx-appear 0.4s ease-out;
  min-width: 0;
}

.tx-prefix {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: 0.72rem;
  color: var(--accent-gold, #ccaa44);
  flex-shrink: 0;
}

.tx-text {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: 0.72rem;
  color: var(--text-primary, #c8c8d0);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  animation: tx-type 0.6s steps(30, end);
}

@keyframes tx-appear {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes tx-type {
  from { max-width: 0; }
  to { max-width: 100%; }
}

/* ── Signal Bar ── */
.signal-bar {
  height: 2px;
  background: var(--border-subtle, #1a1a24);
  border-radius: 1px;
  overflow: hidden;
}

.signal-fill {
  height: 100%;
  border-radius: 1px;
  width: 0;
  transition: width 0.3s ease;
}

.signal-bar.recording .signal-fill {
  width: 100%;
  background: var(--accent-red, #cc4444);
  animation: signal-scan 1.5s ease-in-out infinite;
}

.signal-bar.transcribing .signal-fill {
  width: 60%;
  background: var(--accent-gold, #ccaa44);
  animation: signal-load 1s ease-in-out infinite alternate;
}

.signal-bar.error .signal-fill {
  width: 100%;
  background: var(--accent-orange, #e06030);
}

@keyframes signal-scan {
  0% { width: 0; margin-left: 0; }
  50% { width: 100%; margin-left: 0; }
  100% { width: 0; margin-left: 100%; }
}

@keyframes signal-load {
  from { width: 20%; }
  to { width: 80%; }
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .voice-commander {
    padding: 6px 10px;
  }

  .mic-button {
    width: 34px;
    height: 34px;
  }
}

@media (max-width: 480px) {
  .voice-commander {
    padding: 5px 8px;
    gap: 4px;
  }

  .commander-label {
    font-size: 0.75rem;
  }

  .mic-button {
    width: 32px;
    height: 32px;
  }

  .status-text {
    font-size: 0.65rem;
  }

  .tx-text,
  .tx-prefix {
    font-size: 0.65rem;
  }
}
</style>
