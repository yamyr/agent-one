<script setup>
import { RouterView } from 'vue-router'
</script>

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

  /* Radii */
  --radius-sm: 3px;
  --radius-md: 4px;
  --radius-lg: 6px;
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

.app {
  max-width: 1100px;
  margin: 0 auto;
  padding: 1rem;
}

.top-row {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.left-col {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 3;
  min-width: 0;
}

.empty {
  color: var(--text-dimmer);
  padding: 1rem;
  text-align: center;
  font-size: 0.8rem;
}

h2 {
  font-size: 0.85rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 0.5rem;
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

.follow-bar {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.follow-label {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.follow-btn {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  padding: 0.15rem 0.4rem;
  border: 1px solid;
  border-radius: var(--radius-sm);
  background: transparent;
  cursor: pointer;
  transition: all 0.15s;
}

.follow-btn:hover {
  opacity: 0.8;
}

.follow-btn.active {
  font-weight: bold;
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

/* ── Responsive: Tablet (≤768px) ── */
@media (max-width: 768px) {
  .app {
    padding: 0.5rem;
  }

  .top-row {
    flex-direction: column;
  }

  .left-col {
    flex: none;
  }
}

/* ── Responsive: Mobile (≤480px) ── */
@media (max-width: 480px) {
  .app {
    padding: 0.25rem;
  }

  h2 {
    font-size: 0.75rem;
  }

  .follow-bar {
    gap: 0.2rem;
  }

  .follow-btn {
    font-size: 0.55rem;
    padding: 0.1rem 0.3rem;
  }
}
</style>
