<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

/**
 * AgentsShowcase — Bento grid showcasing 3 AI agents.
 *
 * Rover spans the full left column, Drone and Station
 * stack on the right. Each card uses glassmorphism with
 * agent-themed hover glow. IntersectionObserver for reveal.
 */

const agents = [
  {
    id: 'rover',
    nameKey: 'agents.rover_name',
    roleKey: 'agents.rover_role',
    descKey: 'agents.rover_desc',
    toolsKey: 'agents.rover_tools',
    themeColor: 'var(--mars-rust)',
    cssClass: 'agent-card--rover',
  },
  {
    id: 'drone',
    nameKey: 'agents.drone_name',
    roleKey: 'agents.drone_role',
    descKey: 'agents.drone_desc',
    toolsKey: 'agents.drone_tools',
    themeColor: 'var(--accent-cyan)',
    cssClass: 'agent-card--drone',
  },
  {
    id: 'station',
    nameKey: 'agents.station_name',
    roleKey: 'agents.station_role',
    descKey: 'agents.station_desc',
    toolsKey: 'agents.station_tools',
    themeColor: 'var(--accent-amber)',
    cssClass: 'agent-card--station',
  },
]

const sectionRef = ref(null)
const visible = ref(false)
let observer = null

onMounted(() => {
  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          visible.value = true
          observer.disconnect()
        }
      })
    },
    { threshold: 0.2 }
  )

  if (sectionRef.value) {
    observer.observe(sectionRef.value)
  }
})

onUnmounted(() => {
  if (observer) {
    observer.disconnect()
  }
})
</script>

<template>
  <section
    id="agents"
    ref="sectionRef"
    class="agents"
    :class="{ visible }"
  >
    <span class="agents__label">{{ $t('agents.label') }}</span>
    <h2 class="agents__title">{{ $t('agents.title') }}</h2>

    <div class="agents__grid">
      <!-- Rover — spans full left column -->
      <div class="agent-card agent-card--rover">
        <svg class="agent-card__icon" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <!-- 6-wheeled rover silhouette -->
          <rect x="6" y="14" width="28" height="10" rx="3" :stroke="agents[0].themeColor" stroke-width="1.5" fill="none" />
          <rect x="12" y="10" width="14" height="6" rx="2" :stroke="agents[0].themeColor" stroke-width="1.5" fill="none" />
          <line x1="18" y1="10" x2="16" y2="6" :stroke="agents[0].themeColor" stroke-width="1.5" stroke-linecap="round" />
          <circle cx="14" cy="6" r="2" :stroke="agents[0].themeColor" stroke-width="1.2" fill="none" />
          <circle cx="10" cy="28" r="4" :stroke="agents[0].themeColor" stroke-width="1.5" fill="none" />
          <circle cx="20" cy="28" r="4" :stroke="agents[0].themeColor" stroke-width="1.5" fill="none" />
          <circle cx="30" cy="28" r="4" :stroke="agents[0].themeColor" stroke-width="1.5" fill="none" />
          <line x1="10" y1="24" x2="10" y2="24" :stroke="agents[0].themeColor" stroke-width="1.5" />
          <line x1="20" y1="24" x2="20" y2="24" :stroke="agents[0].themeColor" stroke-width="1.5" />
          <line x1="30" y1="24" x2="30" y2="24" :stroke="agents[0].themeColor" stroke-width="1.5" />
        </svg>
        <h3 class="agent-card__name">{{ $t(agents[0].nameKey) }}</h3>
        <span class="agent-card__role">{{ $t(agents[0].roleKey) }}</span>
        <p class="agent-card__desc">{{ $t(agents[0].descKey) }}</p>
        <span class="agent-card__tools">{{ $t(agents[0].toolsKey) }}</span>
      </div>

      <!-- Drone — top right -->
      <div class="agent-card agent-card--drone">
        <svg class="agent-card__icon" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <!-- Quadcopter silhouette -->
          <circle cx="20" cy="20" r="4" :stroke="agents[1].themeColor" stroke-width="1.5" fill="none" />
          <line x1="16" y1="16" x2="8" y2="8" :stroke="agents[1].themeColor" stroke-width="1.5" stroke-linecap="round" />
          <line x1="24" y1="16" x2="32" y2="8" :stroke="agents[1].themeColor" stroke-width="1.5" stroke-linecap="round" />
          <line x1="16" y1="24" x2="8" y2="32" :stroke="agents[1].themeColor" stroke-width="1.5" stroke-linecap="round" />
          <line x1="24" y1="24" x2="32" y2="32" :stroke="agents[1].themeColor" stroke-width="1.5" stroke-linecap="round" />
          <ellipse cx="8" cy="8" rx="5" ry="2" :stroke="agents[1].themeColor" stroke-width="1.2" fill="none" />
          <ellipse cx="32" cy="8" rx="5" ry="2" :stroke="agents[1].themeColor" stroke-width="1.2" fill="none" />
          <ellipse cx="8" cy="32" rx="5" ry="2" :stroke="agents[1].themeColor" stroke-width="1.2" fill="none" />
          <ellipse cx="32" cy="32" rx="5" ry="2" :stroke="agents[1].themeColor" stroke-width="1.2" fill="none" />
        </svg>
        <h3 class="agent-card__name">{{ $t(agents[1].nameKey) }}</h3>
        <span class="agent-card__role">{{ $t(agents[1].roleKey) }}</span>
        <p class="agent-card__desc">{{ $t(agents[1].descKey) }}</p>
        <span class="agent-card__tools">{{ $t(agents[1].toolsKey) }}</span>
      </div>

      <!-- Station — bottom right -->
      <div class="agent-card agent-card--station">
        <svg class="agent-card__icon" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <!-- Satellite dish / base station -->
          <path d="M20 32 L20 20" :stroke="agents[2].themeColor" stroke-width="1.5" stroke-linecap="round" />
          <path d="M14 32 L26 32" :stroke="agents[2].themeColor" stroke-width="1.5" stroke-linecap="round" />
          <path d="M10 34 L30 34" :stroke="agents[2].themeColor" stroke-width="1.5" stroke-linecap="round" />
          <path d="M8 16 Q20 4 32 16" :stroke="agents[2].themeColor" stroke-width="1.5" fill="none" stroke-linecap="round" />
          <path d="M12 18 Q20 10 28 18" :stroke="agents[2].themeColor" stroke-width="1.2" fill="none" stroke-linecap="round" />
          <circle cx="20" cy="20" r="3" :stroke="agents[2].themeColor" stroke-width="1.5" fill="none" />
          <circle cx="20" cy="20" r="1" :fill="agents[2].themeColor" />
        </svg>
        <h3 class="agent-card__name">{{ $t(agents[2].nameKey) }}</h3>
        <span class="agent-card__role">{{ $t(agents[2].roleKey) }}</span>
        <p class="agent-card__desc">{{ $t(agents[2].descKey) }}</p>
        <span class="agent-card__tools">{{ $t(agents[2].toolsKey) }}</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.agents {
  padding: 6rem 5%;
  max-width: 1200px;
  margin: 0 auto;
}

/* ─── Header ─── */

.agents__label {
  display: block;
  font-size: 0.75rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--mars-sunset);
  font-family: var(--font-mono);
  margin-bottom: 1rem;
  opacity: 0;
  transform: translateY(40px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}

.agents__title {
  font-family: var(--font-display);
  font-size: clamp(1.5rem, 3vw, 2.5rem);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 3rem 0;
  opacity: 0;
  transform: translateY(40px);
  transition: opacity 0.6s ease 0.1s, transform 0.6s ease 0.1s;
}

/* ─── Bento Grid ─── */

.agents__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto auto;
  gap: 2rem;
}

/* ─── Agent Card Base ─── */

.agent-card {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: 16px;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  opacity: 0;
  transform: translateY(40px);
  transition:
    opacity 0.6s ease,
    transform 0.6s ease,
    border-color 0.3s ease,
    box-shadow 0.3s ease;
}

/* ─── Card Positions ─── */

.agent-card--rover {
  grid-row: 1 / 3;
  grid-column: 1;
  transition-delay: 0.2s, 0.2s, 0s, 0s;
}

.agent-card--drone {
  grid-row: 1;
  grid-column: 2;
  transition-delay: 0.35s, 0.35s, 0s, 0s;
}

.agent-card--station {
  grid-row: 2;
  grid-column: 2;
  transition-delay: 0.5s, 0.5s, 0s, 0s;
}

/* ─── Card Hover Effects ─── */

.agent-card--rover:hover {
  border-color: var(--mars-rust);
  transform: translateY(-4px);
  box-shadow: 0 8px 32px rgba(183, 65, 14, 0.15);
}

.agent-card--drone:hover {
  border-color: var(--accent-cyan);
  transform: translateY(-4px);
  box-shadow: 0 8px 32px rgba(0, 188, 212, 0.15);
}

.agent-card--station:hover {
  border-color: var(--accent-amber);
  transform: translateY(-4px);
  box-shadow: 0 8px 32px rgba(255, 160, 0, 0.15);
}

/* ─── Card Inner Elements ─── */

.agent-card__icon {
  width: 40px;
  height: 40px;
  margin-bottom: 1.25rem;
  flex-shrink: 0;
}

.agent-card__name {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 0.25rem 0;
}

.agent-card__role {
  display: block;
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 0.75rem;
}

.agent-card__desc {
  color: var(--text-secondary);
  font-size: 0.85rem;
  line-height: 1.7;
  margin: 0;
  flex: 1;
}

.agent-card__tools {
  display: block;
  font-size: 0.7rem;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  margin-top: auto;
  padding-top: 1rem;
  border-top: 1px solid var(--glass-border);
}

/* ─── Visible State ─── */

.agents.visible .agents__label,
.agents.visible .agents__title,
.agents.visible .agent-card {
  opacity: 1;
  transform: translateY(0);
}

/* ─── Responsive ─── */

@media (max-width: 768px) {
  .agents__grid {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
  }

  .agent-card--rover {
    grid-row: auto;
    grid-column: auto;
  }

  .agent-card--drone {
    grid-row: auto;
    grid-column: auto;
  }

  .agent-card--station {
    grid-row: auto;
    grid-column: auto;
  }
}

/* ─── Accessibility ─── */

@media (prefers-reduced-motion: reduce) {
  .agents__label,
  .agents__title,
  .agent-card {
    opacity: 1;
    transform: none;
    transition: none;
  }
}
</style>
