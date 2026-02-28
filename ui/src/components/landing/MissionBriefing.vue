<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

/**
 * MissionBriefing — Mission overview section with animated stats.
 *
 * Uses IntersectionObserver to reveal content on scroll.
 * Stats cards use glassmorphism styling with staggered entrance.
 */

const stats = [
  { value: '3', labelKey: 'mission.stat_agents' },
  { value: '12+', labelKey: 'mission.stat_tools' },
  { value: '< 1s', labelKey: 'mission.stat_realtime' },
  { value: '10', labelKey: 'mission.stat_languages' },
]

const sectionRef = ref(null)
const visible = ref(true)
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
    id="mission"
    ref="sectionRef"
    class="mission"
    :class="{ visible }"
  >
    <div class="mission__content">
      <span class="mission__label">{{ $t('mission.label') }}</span>
      <h2 class="mission__title">{{ $t('mission.title') }}</h2>
      <p class="mission__description">{{ $t('mission.description') }}</p>
    </div>

    <div class="mission__stats">
      <div
        v-for="(stat, index) in stats"
        :key="index"
        class="stat-card"
      >
        <span class="stat-card__value">{{ stat.value }}</span>
        <span class="stat-card__label">{{ $t(stat.labelKey) }}</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.mission {
  padding: 6rem 5%;
  max-width: 1200px;
  margin: 0 auto;
}

/* ─── Content Block ─── */

.mission__content {
  margin-bottom: 3rem;
}

.mission__label {
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

.mission__title {
  font-family: var(--font-display);
  font-size: clamp(1.5rem, 3vw, 2.5rem);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 1rem 0;
  opacity: 0;
  transform: translateY(40px);
  transition: opacity 0.6s ease 0.1s, transform 0.6s ease 0.1s;
}

.mission__description {
  color: var(--text-secondary);
  font-size: 0.95rem;
  line-height: 1.8;
  max-width: 700px;
  margin: 0;
  opacity: 0;
  transform: translateY(40px);
  transition: opacity 0.6s ease 0.2s, transform 0.6s ease 0.2s;
}

/* ─── Stats Grid ─── */

.mission__stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 2rem;
}

/* ─── Stat Card ─── */

.stat-card {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: 12px;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  opacity: 0;
  transform: translateY(40px);
  transition:
    opacity 0.6s ease,
    transform 0.6s ease,
    border-color 0.3s ease,
    box-shadow 0.3s ease;
}

/* Stagger delays for stat cards */
.stat-card:nth-child(1) { transition-delay: 0.3s, 0.3s, 0s, 0s; }
.stat-card:nth-child(2) { transition-delay: 0.4s, 0.4s, 0s, 0s; }
.stat-card:nth-child(3) { transition-delay: 0.5s, 0.5s, 0s, 0s; }
.stat-card:nth-child(4) { transition-delay: 0.6s, 0.6s, 0s, 0s; }

.stat-card:hover {
  border-color: var(--glass-border-hover);
  transform: translateY(-2px);
}

.stat-card__value {
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 700;
  color: var(--mars-sunset);
  line-height: 1;
}

.stat-card__label {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

/* ─── Visible State ─── */

.mission.visible .mission__label,
.mission.visible .mission__title,
.mission.visible .mission__description,
.mission.visible .stat-card {
  opacity: 1;
  transform: translateY(0);
}

/* ─── Responsive ─── */

@media (max-width: 768px) {
  .mission__stats {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .mission__stats {
    grid-template-columns: 1fr;
  }
}

/* ─── Accessibility ─── */

@media (prefers-reduced-motion: reduce) {
  .mission__label,
  .mission__title,
  .mission__description,
  .stat-card {
    opacity: 1;
    transform: none;
    transition: none;
  }
}
</style>
