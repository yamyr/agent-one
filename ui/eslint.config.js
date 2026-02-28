import js from '@eslint/js'
import globals from 'globals'
import pluginVue from 'eslint-plugin-vue'

export default [
  { languageOptions: { globals: globals.browser } },
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
]
