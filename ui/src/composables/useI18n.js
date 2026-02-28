import { reactive } from 'vue'

const STORAGE_KEY = 'agent_one_locale'

const state = reactive({
  locale: localStorage.getItem(STORAGE_KEY) || 'en-US',
  locales: [],
  translations: {},
  ready: false,
})

async function loadTranslations(locale = state.locale) {
  const res = await fetch(`/api/i18n/translations?locale=${encodeURIComponent(locale)}`)
  if (!res.ok) return
  const data = await res.json()
  state.locale = data.locale
  state.locales = data.locales || []
  state.translations = data.translations || {}
  state.ready = true
  localStorage.setItem(STORAGE_KEY, state.locale)
}

function t(key, params = {}) {
  const template = state.translations[key] || key
  return template.replace(/\{(\w+)\}/g, (_, token) => String(params[token] ?? `{${token}}`))
}

function setLocale(locale) {
  return loadTranslations(locale)
}

if (!state.ready) {
  loadTranslations().catch(() => {
    state.ready = true
  })
}

export function useI18n() {
  return {
    i18n: state,
    t,
    setLocale,
    loadTranslations,
  }
}
