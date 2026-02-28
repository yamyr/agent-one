<script setup>
import { ref } from 'vue'

const props = defineProps({
  connected: Boolean,
  paused: Boolean,
})

const emit = defineEmits(['toggle-pause', 'reset', 'show-help'])

// Language selection
const currentLang = ref('en')
const supportedLangs = ['en', 'es', 'fr', 'de', 'zh', 'ja']

async function changeLanguage(lang) {
  currentLang.value = lang
  // TODO: Fetch translations and update UI
  console.log('Language changed to:', lang)
}
</script>

<template>
  <header>
    <h1>Mars Mission Control</h1>
    <div class="header-controls">
      <select 
        v-model="currentLang" 
        class="lang-select"
        @change="changeLanguage(currentLang)"
        aria-label="Select language"
      >
        <option v-for="lang in supportedLangs" :key="lang" :value="lang">
          {{ lang.toUpperCase() }}
        </option>
      </select>
      <button
        class="reset-btn"
        type="button"
        aria-label="Reset simulation"
        @click="emit('reset')"
      >
        RESET
      </button>
      <button
        class="pause-btn"
        :class="{ paused }"
        type="button"
        :aria-label="paused ? 'Resume simulation' : 'Pause simulation'"
        @click="emit('toggle-pause')"
      >
        {{ paused ? 'RESUME' : 'PAUSE' }}
      </button>
      <button
        class="help-btn"
        type="button"
        aria-label="Show help"
        @click="emit('show-help')"
      >
        HELP
      </button>
      <span
        class="status"
        :class="{ online: connected }"
      >
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
  border-bottom: 1px solid var(--border-separator);
  margin-bottom: 1rem;
}

h1 {
  font-size: 1.2rem;
  color: var(--accent-orange);
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.lang-select {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  padding: 0.25rem 0.4rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--text-muted);
  background: var(--bg-input);
  color: var(--text-primary);
  cursor: pointer;
}

.reset-btn {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  padding: 0.25rem 0.6rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--text-muted);
  background: var(--bg-input);
  color: var(--accent-red);
  cursor: pointer;
}

.reset-btn:hover {
  border-color: var(--accent-red);
  color: var(--accent-red-light);
}

.pause-btn {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  padding: 0.25rem 0.6rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--text-muted);
  background: var(--bg-input);
  color: var(--accent-amber);
  cursor: pointer;
}

.pause-btn:hover {
  border-color: var(--text-secondary);
  color: var(--accent-amber-light);
}

.pause-btn.paused {
  background: var(--bg-status-warn);
  border-color: var(--accent-amber);
  color: var(--accent-amber-light);
}

.help-btn {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  padding: 0.25rem 0.6rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--text-muted);
  background: var(--bg-input);
  color: var(--accent-blue);
  cursor: pointer;
}

.help-btn:hover {
  border-color: var(--accent-blue);
  color: var(--accent-blue);
}

.status {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  background: var(--bg-status-error);
  color: var(--accent-red);
}

.status.online {
  background: var(--bg-status-ok);
  color: var(--accent-green);
}

@media (max-width: 768px) {
  header {
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  h1 {
    font-size: 1rem;
  }
}

@media (max-width: 480px) {
  h1 {
    font-size: 0.85rem;
    width: 100%;
  }

  .header-controls {
    width: 100%;
    justify-content: space-between;
  }

  .lang-select,
  .reset-btn,
  .pause-btn {
    font-size: 0.65rem;
    padding: 0.2rem 0.4rem;
  }

  .status {
    font-size: 0.65rem;
  }
}
</style>
