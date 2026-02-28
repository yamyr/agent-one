import { reactive, watch } from 'vue'

const STORAGE_KEY = 'agent_one_prefs'

const defaultPrefs = {
  zoom: 1,
  showLegend: false,
}

const state = reactive({ ...defaultPrefs })

// Load from local storage immediately
try {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored) {
    const parsed = JSON.parse(stored)
    // Merge to ensure new keys exist
    Object.assign(state, { ...defaultPrefs, ...parsed })
  }
} catch (e) {
  console.error('Failed to load preferences', e)
}

// Persist on change
watch(state, (newVal) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newVal))
  } catch {
    // ignore
  }
}, { deep: true })

export function usePreferences() {
  return {
    prefs: state
  }
}
