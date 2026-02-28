<template>
  <RouterView />
</template>

<style>
:root {
  /* Backgrounds */
  --bg-primary: #0a0a0f;
  --bg-card: #0c0c14;
  --bg-elevated: #12121a;
  --bg-input: #1a1a24;
  --bg-tile: #060609;
  --bg-revealed: #0e0e16;

  /* Borders */
  --border-subtle: #1a1a24;
  --border-medium: #2a2a38;
  --border-dim: #111118;
  --border-separator: #222;

  /* Text */
  --text-primary: #c8c8d0;
  --text-muted: #555;
  --text-dim: #333;
  --text-dimmer: #444;
  --text-secondary: #888;
  --text-tertiary: #666;

  /* Accents */
  --accent-orange: #e06030;
  --accent-gold: #ccaa44;
  --accent-amber: #cc8844;
  --accent-amber-light: #eebb66;
  --accent-amber-dark: #b8962a;
  --accent-green: #44cc44;
  --accent-green-soft: #88cc88;
  --accent-red: #cc4444;
  --accent-red-light: #ee6666;
  --accent-teal: #44ccaa;
  --accent-blue: #6688cc;
  --accent-action: #c86040;
  --accent-task: #e0a040;
  --accent-memory: #7a9a7a;
  --accent-mission: #8a8a6a;
  --accent-think: #668;
  --accent-unknown: #4a4a6a;
  --accent-unknown-border: #2a2a3a;
  --accent-free: #555;
  --accent-panel-stroke: #aa8020;

  /* Status backgrounds */
  --bg-status-ok: #113311;
  --bg-status-error: #331111;
  --bg-status-info: #1a1a30;
  --bg-status-warn: #2a1a0a;
  --bg-status-narration: #2a1a30;
  --bg-minimap: #060609;
  --bg-minimap-revealed: #1a1a28;

  /* Typography */
  --font-mono: 'JetBrains Mono', monospace;
  --font-display: 'Space Grotesk', sans-serif;

  /* Radii */
  --radius-sm: 3px;
  --radius-md: 4px;
  --radius-lg: 6px;

  /* ── Landing page tokens ── */
  --space-void: #05020e;
  --space-midnight: #0a0a0f;
  --space-dark: #0c0c14;
  --mars-red: #924737;
  --mars-rust: #b26e52;
  --mars-sunset: #ff6b35;
  --mars-ochre: #d4893f;
  --accent-cyan: #00d4ff;
  --glass-bg: rgba(15, 15, 25, 0.6);
  --glass-border: rgba(255, 255, 255, 0.08);
  --glass-border-hover: rgba(255, 255, 255, 0.15);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: var(--font-mono);
}

/* scrollbar */
::-webkit-scrollbar {
  width: 4px;
}
::-webkit-scrollbar-track {
  background: var(--bg-primary);
}
::-webkit-scrollbar-thumb {
  background: var(--border-separator);
  border-radius: 2px;
}

/* ── Modal transition ── */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.25s ease;
}

.modal-enter-active .modal,
.modal-leave-active .modal {
  transition: transform 0.25s ease, opacity 0.25s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal {
  transform: translateY(16px) scale(0.97);
  opacity: 0;
}

.modal-leave-to .modal {
  transform: translateY(8px) scale(0.98);
  opacity: 0;
}

:focus-visible {
  outline: 2px solid var(--accent-blue);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
</style>
