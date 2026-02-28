<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

/**
 * FeaturesGrid — 6 capability cards in a responsive grid.
 *
 * Each card showcases a core feature with inline SVG icon,
 * glassmorphism styling, and staggered scroll-reveal animation.
 */

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
    { threshold: 0.1 }
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
    id="features"
    ref="sectionRef"
    class="features"
    :class="{ visible }"
  >
    <span class="features__label">{{ $t('features.label') }}</span>
    <h2 class="features__title">{{ $t('features.title') }}</h2>

    <div class="features__grid">
      <div
        v-for="(item, i) in $tm('features.items')"
        :key="i"
        class="feature-card"
      >
        <!-- LLM Reasoning: brain/neural icon -->
        <svg v-if="i === 0" class="feature-card__icon" width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M16 4C12 4 9 7 9 11c0 2.5 1.2 4.7 3 6v3a2 2 0 002 2h4a2 2 0 002-2v-3c1.8-1.3 3-3.5 3-6 0-4-3-7-7-7z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M12 24v2a2 2 0 002 2h4a2 2 0 002-2v-2M16 4V2M9 11H7M25 11h-2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <circle cx="14" cy="12" r="1" fill="currentColor"/>
          <circle cx="18" cy="12" r="1" fill="currentColor"/>
          <path d="M14 12l-2 2M18 12l2 2M14 12h4" stroke="currentColor" stroke-width="1" stroke-linecap="round"/>
        </svg>

        <!-- Probabilistic Goals: target/crosshair icon -->
        <svg v-else-if="i === 1" class="feature-card__icon" width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="16" cy="16" r="11" stroke="currentColor" stroke-width="1.5"/>
          <circle cx="16" cy="16" r="7" stroke="currentColor" stroke-width="1.5"/>
          <circle cx="16" cy="16" r="3" stroke="currentColor" stroke-width="1.5"/>
          <path d="M16 3v4M16 25v4M3 16h4M25 16h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>

        <!-- Real-Time Streaming: signal/wave icon -->
        <svg v-else-if="i === 2" class="feature-card__icon" width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M6 20a10 10 0 0114.14-14.14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <path d="M9.5 17.5a6 6 0 018.49-8.49" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <circle cx="12" cy="20" r="2.5" fill="currentColor"/>
          <path d="M20 16v10M24 12v14M28 14v10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>

        <!-- AI Narration: microphone/speaker icon -->
        <svg v-else-if="i === 3" class="feature-card__icon" width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="12" y="4" width="8" height="14" rx="4" stroke="currentColor" stroke-width="1.5"/>
          <path d="M8 16a8 8 0 0016 0" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <path d="M16 24v4M12 28h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <path d="M24 10c1.5 1 2.5 3 2.5 5s-1 4-2.5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>

        <!-- Dynamic World: globe/terrain icon -->
        <svg v-else-if="i === 4" class="feature-card__icon" width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="16" cy="16" r="12" stroke="currentColor" stroke-width="1.5"/>
          <ellipse cx="16" cy="16" rx="5" ry="12" stroke="currentColor" stroke-width="1.2"/>
          <path d="M4 16h24M5.5 10h21M5.5 22h21" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
          <path d="M10 26l3-4 2 2 4-5 3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>

        <!-- Multi-Agent: network/nodes icon -->
        <svg v-else class="feature-card__icon" width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="16" cy="8" r="3" stroke="currentColor" stroke-width="1.5"/>
          <circle cx="7" cy="24" r="3" stroke="currentColor" stroke-width="1.5"/>
          <circle cx="25" cy="24" r="3" stroke="currentColor" stroke-width="1.5"/>
          <circle cx="16" cy="18" r="2" fill="currentColor"/>
          <path d="M16 11v5M13.5 19.5L9 22M18.5 19.5L23 22" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <path d="M10 23l6-5 6 5" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-dasharray="2 2"/>
        </svg>

        <h3 class="feature-card__title">{{ item.title }}</h3>
        <p class="feature-card__desc">{{ item.desc }}</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.features {
  padding: 6rem 5%;
  max-width: 1200px;
  margin: 0 auto;
}

/* ─── Section Header ─── */

.features__label {
  display: block;
  font-size: 0.75rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--mars-sunset);
  font-family: var(--font-mono);
  margin-bottom: 1rem;
  opacity: 0;
  transform: translateY(30px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}

.features__title {
  font-family: var(--font-display);
  font-size: clamp(1.5rem, 3vw, 2.5rem);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 2.5rem 0;
  opacity: 0;
  transform: translateY(30px);
  transition: opacity 0.6s ease 0.1s, transform 0.6s ease 0.1s;
}

/* ─── Grid ─── */

.features__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}

/* ─── Feature Card ─── */

.feature-card {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: 16px;
  padding: 2rem;
  opacity: 0;
  transform: translateY(30px);
  transition:
    opacity 0.6s ease,
    transform 0.6s ease,
    border-color 0.3s ease,
    box-shadow 0.3s ease;
}

/* Stagger delays — 120ms per card */
.feature-card:nth-child(1) { transition-delay: 0.2s, 0.2s, 0s, 0s; }
.feature-card:nth-child(2) { transition-delay: 0.32s, 0.32s, 0s, 0s; }
.feature-card:nth-child(3) { transition-delay: 0.44s, 0.44s, 0s, 0s; }
.feature-card:nth-child(4) { transition-delay: 0.56s, 0.56s, 0s, 0s; }
.feature-card:nth-child(5) { transition-delay: 0.68s, 0.68s, 0s, 0s; }
.feature-card:nth-child(6) { transition-delay: 0.80s, 0.80s, 0s, 0s; }

.feature-card:hover {
  border-color: var(--glass-border-hover);
  transform: translateY(-4px);
  box-shadow: 0 8px 32px rgba(255, 107, 53, 0.1);
}

.feature-card__icon {
  color: var(--mars-sunset);
  flex-shrink: 0;
}

.feature-card__title {
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0.75rem 0 0.5rem;
}

.feature-card__desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.7;
  margin: 0;
}

/* ─── Visible State ─── */

.features.visible .features__label,
.features.visible .features__title,
.features.visible .feature-card {
  opacity: 1;
  transform: translateY(0);
}

/* ─── Responsive ─── */

@media (max-width: 768px) {
  .features__grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .features__grid {
    grid-template-columns: 1fr;
  }
}

/* ─── Accessibility ─── */

@media (prefers-reduced-motion: reduce) {
  .features__label,
  .features__title,
  .feature-card {
    opacity: 1;
    transform: none;
    transition: none;
  }
}
</style>
