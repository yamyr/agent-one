<script setup>
import { useI18n } from '../composables/useI18n.js'

defineProps({
  connected: Boolean,
  paused: Boolean,
})

const emit = defineEmits(['toggle-pause', 'reset'])
const { i18n, t, setLocale } = useI18n()
</script>

<template>
  <header>
    <h1>{{ t('app.title') }}</h1>
    <div class="header-controls">
      <select
        class="lang-select"
        :value="i18n.locale"
        :aria-label="t('header.language')"
        @change="setLocale($event.target.value)"
      >
        <option
          v-for="locale in i18n.locales"
          :key="locale.code"
          :value="locale.code"
        >
          {{ locale.label }}
        </option>
      </select>
      <button
        class="reset-btn"
        type="button"
        :aria-label="t('header.reset')"
        @click="emit('reset')"
      >
        {{ t('header.reset') }}
      </button>
      <button
        class="pause-btn"
        :class="{ paused }"
        type="button"
        :aria-label="paused ? t('header.resume') : t('header.pause')"
        @click="emit('toggle-pause')"
      >
        {{ paused ? t('header.resume') : t('header.pause') }}
      </button>
      <span
        class="status"
        :class="{ online: connected }"
      >{{ connected ? t('status.connected') : t('status.disconnected') }}</span>
    </div>
  </header>
</template>

<style scoped>
header { display:flex; justify-content:space-between; align-items:center; padding:1rem 0; border-bottom:1px solid var(--border-separator); margin-bottom:1rem; }
h1 { font-size:1.2rem; color:var(--accent-orange); }
.header-controls { display:flex; align-items:center; gap:0.5rem; }
.lang-select { background:var(--bg-input); color:var(--text-primary); border:1px solid var(--border-medium); border-radius:var(--radius-sm); padding:0.2rem 0.4rem; font-size:0.7rem; font-family:var(--font-mono); }
.reset-btn,.pause-btn { font-family:var(--font-mono); font-size:0.75rem; padding:0.25rem 0.6rem; border-radius:var(--radius-sm); border:1px solid var(--text-muted); background:var(--bg-input); cursor:pointer; }
.reset-btn { color:var(--accent-red); }
.pause-btn { color:var(--accent-amber); }
.pause-btn.paused { background:var(--bg-status-warn); border-color:var(--accent-amber); color:var(--accent-amber-light); }
.status { font-size:0.75rem; padding:0.25rem 0.5rem; border-radius:var(--radius-sm); background:var(--bg-status-error); color:var(--accent-red); }
.status.online { background:var(--bg-status-ok); color:var(--accent-green); }
</style>
