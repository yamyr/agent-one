<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

/**
 * CTASection — Final call-to-action with Mars glow and orbital decorations.
 *
 * Radial gradient pulse behind text, two rotating orbital rings,
 * and dual action buttons (launch + GitHub).
 */

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
    ref="sectionRef"
    class="cta"
    :class="{ visible }"
  >
    <!-- Mars glow -->
    <div class="cta__glow" aria-hidden="true" />

    <!-- Orbital rings -->
    <div class="cta__orbit cta__orbit--1" aria-hidden="true" />
    <div class="cta__orbit cta__orbit--2" aria-hidden="true" />

    <!-- Content -->
    <div class="cta__content">
      <h2 class="cta__title">{{ $t('cta.title') }}</h2>
      <p class="cta__subtitle">{{ $t('cta.subtitle') }}</p>

      <div class="cta__buttons">
        <RouterLink to="/app" class="cta__btn cta__btn--primary">
          {{ $t('cta.button_launch') }}
        </RouterLink>
        <a
          href="https://github.com/mhack-agent-one/agent-one"
          target="_blank"
          rel="noopener noreferrer"
          class="cta__btn cta__btn--secondary"
        >
          {{ $t('cta.button_github') }}
        </a>
      </div>
    </div>
  </section>
</template>

<style scoped>
.cta {
  padding: 8rem 5%;
  text-align: center;
  position: relative;
  overflow: hidden;
}

/* ─── Mars Glow ─── */

.cta__glow {
  position: absolute;
  width: 600px;
  height: 600px;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: radial-gradient(circle at center, rgba(255, 107, 53, 0.15) 0%, transparent 60%);
  pointer-events: none;
  animation: cta-pulse 4s ease-in-out infinite;
}

@keyframes cta-pulse {
  0%, 100% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 0.15;
  }
  50% {
    transform: translate(-50%, -50%) scale(1.1);
    opacity: 0.25;
  }
}

/* ─── Orbital Rings ─── */

.cta__orbit {
  position: absolute;
  top: 50%;
  left: 50%;
  border-radius: 50%;
  pointer-events: none;
}

.cta__orbit--1 {
  width: 300px;
  height: 300px;
  margin-top: -150px;
  margin-left: -150px;
  border: 1px solid rgba(255, 107, 53, 0.1);
  animation: orbit-spin 30s linear infinite;
}

.cta__orbit--2 {
  width: 450px;
  height: 450px;
  margin-top: -225px;
  margin-left: -225px;
  border: 1px solid rgba(0, 212, 255, 0.08);
  animation: orbit-spin 45s linear infinite reverse;
}

@keyframes orbit-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ─── Content ─── */

.cta__content {
  position: relative;
  z-index: 1;
}

.cta__title {
  font-family: var(--font-display);
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  opacity: 0;
  transform: translateY(40px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}

.cta__subtitle {
  color: var(--text-secondary);
  font-size: 1rem;
  max-width: 500px;
  margin: 1rem auto 2rem;
  line-height: 1.7;
  opacity: 0;
  transform: translateY(40px);
  transition: opacity 0.6s ease 0.1s, transform 0.6s ease 0.1s;
}

/* ─── Buttons ─── */

.cta__buttons {
  display: flex;
  justify-content: center;
  gap: 1rem;
  flex-wrap: wrap;
  opacity: 0;
  transform: translateY(40px);
  transition: opacity 0.6s ease 0.2s, transform 0.6s ease 0.2s;
}

.cta__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 1rem 2.5rem;
  border-radius: 8px;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  text-decoration: none;
  cursor: pointer;
  transition: filter 0.3s ease, transform 0.2s ease, box-shadow 0.3s ease, background 0.3s ease;
}

.cta__btn--primary {
  background: linear-gradient(135deg, var(--mars-sunset), var(--mars-red));
  color: #fff;
  border: none;
}

.cta__btn--primary:hover {
  filter: brightness(1.15);
  transform: translateY(-3px);
  box-shadow: 0 8px 32px rgba(255, 107, 53, 0.3);
}

.cta__btn--secondary {
  background: transparent;
  border: 1px solid var(--glass-border-hover);
  color: var(--text-primary);
}

.cta__btn--secondary:hover {
  background: var(--glass-bg);
  transform: translateY(-3px);
}

/* ─── Visible State ─── */

.cta.visible .cta__title,
.cta.visible .cta__subtitle,
.cta.visible .cta__buttons {
  opacity: 1;
  transform: translateY(0);
}

/* ─── Accessibility ─── */

@media (prefers-reduced-motion: reduce) {
  .cta__title,
  .cta__subtitle,
  .cta__buttons,
  .cta__btn {
    opacity: 1;
    transform: none;
    transition: none;
  }

  .cta__glow {
    animation: none;
    opacity: 0.15;
  }

  .cta__orbit--1,
  .cta__orbit--2 {
    animation: none;
  }
}
</style>
