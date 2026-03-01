import { createApp } from 'vue'
import 'virtual:uno.css'
import '@fontsource/jetbrains-mono/400.css'
import '@fontsource/jetbrains-mono/700.css'
import App from './App.vue'
import router from './router/index.js'
import i18n, { initI18n } from './i18n/index.js'

async function bootstrap() {
  const app = createApp(App)
  app.use(router)
  app.use(i18n)
  await initI18n()
  app.mount('#app')
}

bootstrap()
