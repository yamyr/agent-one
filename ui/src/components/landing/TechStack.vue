<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

/**
 * TechStack — Tech stack categories with pill tags.
 *
 * Uses IntersectionObserver to reveal cards on scroll with stagger.
 * Four category cards in a 2×2 glassmorphism grid.
 */

const categories = ['ai', 'backend', 'frontend', 'infra']

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
    id="tech"
    ref="sectionRef"
    class="tech"
    :class="{ visible }"
  >
    <span class="tech__label">{{ $t('tech.label') }}</span>
    <h2 class="tech__title">{{ $t('tech.title') }}</h2>

    <div class="tech__grid">
      <div
        v-for="(cat, index) in categories"
        :key="cat"
        class="tech-card"
        :class="'tech-card--' + (index + 1)"
      >
        <span class="tech-card__label">{{ $t('tech.' + cat + '.label') }}</span>
        <div class="tech-card__pills">
          <span
            v-for="item in $tm('tech.' + cat + '.items')"
            :key="item"
            class="pill"
          >
            {{ item }}
          </span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.tech {
  padding: 6rem 5%;
  max-width: 1200px;
  margin: 0 auto;
}

/* ─── Section Header ─── */

.tech__label {
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

.tech__title {
  font-family: var(--font-display);
  font-size: clamp(1.5rem, 3vw, 2.5rem);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 2.5rem 0;
  opacity: 0;
  transform: translateY(40px);
  transition: opacity 0.6s ease 0.1s, transform 0.6s ease 0.1s;
}

/* ─── Grid ─── */

.tech__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
}

/* ─── Category Card ─── */

.tech-card {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: 16px;
  padding: 1.5rem;
  opacity: 0;
  transform: translateY(40px);
  transition:
    opacity 0.6s ease,
    transform 0.6s ease,
    border-color 0.3s ease;
}

/* Stagger delays for cards */
.tech-card--1 { transition-delay: 0.2s, 0.2s, 0s; }
.tech-card--2 { transition-delay: 0.3s, 0.3s, 0s; }
.tech-card--3 { transition-delay: 0.4s, 0.4s, 0s; }
.tech-card--4 { transition-delay: 0.5s, 0.5s, 0s; }

.tech-card:hover {
  border-color: var(--glass-border-hover);
}

.tech-card__label {
  display: block;
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 1rem;
}

/* ─── Pills ─── */

.tech-card__pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.pill {
  background: rgba(255, 107, 53, 0.1);
  border: 1px solid rgba(255, 107, 53, 0.2);
  border-radius: 999px;
  padding: 0.3rem 0.8rem;
  font-size: 0.75rem;
  color: var(--text-primary);
  font-family: var(--font-mono);
  transition: background 0.2s ease, transform 0.2s ease;
}

.pill:hover {
  background: rgba(255, 107, 53, 0.2);
  transform: scale(1.05);
}

/* ─── Visible State ─── */

.tech.visible .tech__label,
.tech.visible .tech__title,
.tech.visible .tech-card {
  opacity: 1;
  transform: translateY(0);
}

/* ─── Responsive ─── */

@media (max-width: 768px) {
  .tech__grid {
    grid-template-columns: 1fr;
  }
}

/* ─── Accessibility ─── */

@media (prefers-reduced-motion: reduce) {
  .tech__label,
  .tech__title,
  .tech-card,
  .pill {
    opacity: 1;
    transform: none;
    transition: none;
  }
}
</style>
