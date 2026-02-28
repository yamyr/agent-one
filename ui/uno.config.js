import { defineConfig, presetUno } from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),
  ],
  theme: {
    colors: {
      mars: {
        bg: 'var(--bg-primary)',
        card: 'var(--bg-card)',
        elevated: 'var(--bg-elevated)',
        input: 'var(--bg-input)',
      },
      accent: {
        orange: 'var(--accent-orange)',
        gold: 'var(--accent-gold)',
        amber: 'var(--accent-amber)',
        green: 'var(--accent-green)',
        red: 'var(--accent-red)',
        teal: 'var(--accent-teal)',
        blue: 'var(--accent-blue)',
      },
    },
    fontFamily: {
      mono: 'var(--font-mono)',
    },
    borderRadius: {
      sm: 'var(--radius-sm)',
      md: 'var(--radius-md)',
      lg: 'var(--radius-lg)',
    },
  },
})
