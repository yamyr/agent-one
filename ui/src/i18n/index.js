import { createI18n } from 'vue-i18n'

const RTL_LOCALES = ['ar']
const SUPPORTED_LOCALES = ['en', 'de', 'fr', 'es', 'zh', 'ja', 'ko', 'ar', 'ru', 'pt']

const i18n = createI18n({
  legacy: false,
  locale: 'en',
  fallbackLocale: 'en',
  messages: {},
})

function normalizeLocale(rawLocale) {
  if (!rawLocale) return 'en'
  const shortLocale = rawLocale.toLowerCase().split('-')[0]
  return SUPPORTED_LOCALES.includes(shortLocale) ? shortLocale : 'en'
}

function applyLocaleAttributes(locale) {
  const isRtl = RTL_LOCALES.includes(locale)
  document.documentElement.setAttribute('dir', isRtl ? 'rtl' : 'ltr')
  document.documentElement.setAttribute('lang', locale)
}

export async function loadLocaleMessages(locale) {
  const safeLocale = normalizeLocale(locale)
  if (!i18n.global.availableLocales.includes(safeLocale)) {
    const messages = await import(`./locales/${safeLocale}.json`)
    i18n.global.setLocaleMessage(safeLocale, messages.default)
  }
  return safeLocale
}

export async function setLocale(locale) {
  const safeLocale = await loadLocaleMessages(locale)
  i18n.global.locale.value = safeLocale
  applyLocaleAttributes(safeLocale)
  if (typeof window !== 'undefined') {
    window.localStorage.setItem('agent-one-locale', safeLocale)
  }
  return safeLocale
}

export async function initI18n() {
  let initialLocale = 'en'
  if (typeof window !== 'undefined') {
    const storedLocale = window.localStorage.getItem('agent-one-locale')
    initialLocale = normalizeLocale(storedLocale || window.navigator.language)
  }
  await setLocale(initialLocale)
}

export default i18n
