import { createI18n } from 'vue-i18n'
import en from './locales/en.json'

const RTL_LOCALES = ['ar']

const i18n = createI18n({
  legacy: false,
  locale: 'en',
  fallbackLocale: 'en',
  messages: { en },
})

export async function loadLocaleMessages(locale) {
  const messages = await import(`./locales/${locale}.json`)
  i18n.global.setLocaleMessage(locale, messages.default)
  return messages.default
}

export function setLocale(locale) {
  return loadLocaleMessages(locale).then(() => {
    i18n.global.locale.value = locale
    const isRtl = RTL_LOCALES.includes(locale)
    document.documentElement.setAttribute('dir', isRtl ? 'rtl' : 'ltr')
    document.documentElement.setAttribute('lang', locale)
  })
}

export default i18n
