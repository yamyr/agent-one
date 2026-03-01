<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

/* ─── Staggered mount animation ─── */
const mounted = ref(false)
onMounted(() => {
  mounted.value = true
})

/* ─── Smooth scroll to features ─── */
function scrollToFeatures() {
  const el = document.getElementById('features')
  if (el) {
    el.scrollIntoView({ behavior: 'smooth' })
  }
}
</script>

<template>
  <section id="hero" class="hero">
    <div class="hero__content" :class="{ 'hero__content--visible': mounted }">
      <!-- Badge -->
      <div class="hero__badge" :class="{ 'hero__badge--in': mounted }">
        <span class="hero__badge-dot">🔴</span>
        {{ t('hero.badge') }}
      </div>

      <!-- Title -->
      <h1 class="hero__title" :class="{ 'hero__title--in': mounted }">
        <span class="hero__title-line1">{{ t('hero.title_line1') }}</span>
        <span class="hero__title-line2">{{ t('hero.title_line2') }}</span>
      </h1>

      <!-- Subtitle -->
      <p class="hero__subtitle" :class="{ 'hero__subtitle--in': mounted }">
        {{ t('hero.subtitle') }}
      </p>

      <!-- CTA buttons -->
      <div class="hero__ctas" :class="{ 'hero__ctas--in': mounted }">
        <router-link to="/app" class="hero__cta hero__cta--primary">
          {{ t('hero.cta_launch') }}
        </router-link>
        <button class="hero__cta hero__cta--secondary" @click="scrollToFeatures">
          {{ t('hero.cta_explore') }}
        </button>
      </div>
    </div>

    <!-- Scroll indicator -->
    <div class="hero__scroll-indicator" :class="{ 'hero__scroll-indicator--in': mounted }">
      <svg
        class="hero__scroll-chevron"
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </div>
  </section>
</template>

<style scoped>
/* ─── Hero Section ─── */
.hero {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  padding: 72px 5% 0;
}

/* Atmospheric gradient overlay — layers create depth */
.hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 22% 36%, rgba(5, 2, 14, 0.05), rgba(5, 2, 14, 0.65) 40%, rgba(5, 2, 14, 0.88) 100%),
    radial-gradient(ellipse at 80% 80%, rgba(255, 107, 53, 0.04), transparent 60%);
  pointer-events: none;
}

/* Horizon glow — warm Mars atmosphere along bottom edge */
.hero::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 200px;
  background: linear-gradient(
    to top,
    rgba(255, 107, 53, 0.06),
    rgba(255, 140, 82, 0.03) 40%,
    transparent 100%
  );
  pointer-events: none;
  z-index: 1;
}

.hero__content {
  position: relative;
  z-index: 2;
  width: min(56%, 680px);
}

/* ─── Badge ─── */
.hero__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-primary);
  padding: 0.4rem 1rem;
  border: 1px solid var(--glass-border);
  border-radius: 999px;
  background: var(--glass-bg);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  margin-bottom: 1.8rem;
  letter-spacing: 0.02em;

  /* Animation initial state */
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.6s cubic-bezier(0.16, 1, 0.3, 1),
              transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);
  transition-delay: 0.5s;
}

.hero__badge--in {
  opacity: 1;
  transform: translateY(0);
}

.hero__badge-dot {
  font-size: 0.55rem;
  line-height: 1;
}

/* ─── Title ─── */
.hero__title {
  display: flex;
  flex-direction: column;
  margin-bottom: 1.5rem;

  /* Animation initial state */
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.6s cubic-bezier(0.16, 1, 0.3, 1),
              transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);
  transition-delay: 0.7s;
}

.hero__title--in {
  opacity: 1;
  transform: translateY(0);
}

.hero__title-line1 {
  font-family: var(--font-display);
  font-size: clamp(2rem, 5vw, 4rem);
  font-weight: 400;
  color: var(--text-primary);
  line-height: 1.15;
  text-shadow: 0 8px 28px rgba(0, 0, 0, 0.35);
}

.hero__title-line2 {
  font-family: var(--font-display);
  font-size: clamp(2rem, 5vw, 4rem);
  font-weight: 700;
  line-height: 1.15;
  background: linear-gradient(135deg, var(--mars-sunset), var(--mars-rust), var(--mars-red));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  width: fit-content;
}

/* ─── Subtitle ─── */
.hero__subtitle {
  font-family: var(--font-mono);
  font-size: clamp(0.9rem, 1.5vw, 1.1rem);
  color: rgba(244, 246, 255, 0.9);
  max-width: 500px;
  line-height: 1.7;
  margin-bottom: 2rem;
  text-shadow: 0 6px 18px rgba(0, 0, 0, 0.35);

  /* Animation initial state */
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.6s cubic-bezier(0.16, 1, 0.3, 1),
              transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);
  transition-delay: 0.9s;
}

.hero__subtitle--in {
  opacity: 1;
  transform: translateY(0);
}

/* ─── CTA Buttons ─── */
.hero__ctas {
  display: flex;
  gap: 1rem;
  align-items: center;

  /* Animation initial state */
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.6s cubic-bezier(0.16, 1, 0.3, 1),
              transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);
  transition-delay: 1.1s;
}

.hero__ctas--in {
  opacity: 1;
  transform: translateY(0);
}

.hero__cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  padding: 0.8rem 2rem;
  border-radius: 8px;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.3s ease;
}

.hero__cta--primary {
  background: linear-gradient(135deg, var(--mars-sunset), var(--mars-red));
  color: #fff;
  border: none;
}

.hero__cta--primary:hover {
  filter: brightness(1.1);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(255, 107, 53, 0.3),
              0 0 0 1px rgba(255, 107, 53, 0.1);
}

.hero__cta--secondary {
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--glass-border-hover);
}

.hero__cta--secondary:hover {
  background: var(--glass-bg);
  border-color: var(--mars-rust);
  transform: translateY(-2px);
}

/* ─── Scroll Indicator ─── */
.hero__scroll-indicator {
  position: absolute;
  bottom: 2.5rem;
  left: 50%;
  transform: translateX(-50%);
  opacity: 0;
  transition: opacity 0.6s ease;
  transition-delay: 1.6s;
}

.hero__scroll-indicator--in {
  opacity: 0.4;
}

.hero__scroll-chevron {
  color: var(--text-secondary);
  animation: bounce-chevron 2s ease-in-out infinite;
}

@keyframes bounce-chevron {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(8px);
  }
}

/* ─── Animated "in" for subtitle/CTAs via parent class ─── */
.hero__content--visible .hero__subtitle {
  opacity: 1;
  transform: translateY(0);
}

.hero__content--visible .hero__ctas {
  opacity: 1;
  transform: translateY(0);
}

/* ─── Responsive ─── */
@media (max-width: 768px) {
  .hero {
    padding: 0 6%;
    padding-top: 80px;
  }

  .hero__content {
    width: 100%;
    text-align: center;
  }

  .hero__badge {
    margin-left: auto;
    margin-right: auto;
  }

  .hero__title-line2 {
    margin-left: auto;
    margin-right: auto;
  }

  .hero__subtitle {
    max-width: 100%;
    margin-left: auto;
    margin-right: auto;
  }

  .hero__ctas {
    justify-content: center;
  }

  .hero__scroll-indicator {
    bottom: 1.5rem;
  }
}

@media (max-width: 480px) {
  .hero__ctas {
    flex-direction: column;
    width: 100%;
  }

  .hero__cta {
    width: 100%;
  }
}

/* ─── Accessibility ─── */
@media (prefers-reduced-motion: reduce) {
  .hero__badge,
  .hero__title,
  .hero__subtitle,
  .hero__ctas,
  .hero__scroll-indicator,
  .hero__cta {
    transition: none !important;
    opacity: 1 !important;
    transform: none !important;
  }

  .hero__scroll-chevron {
    animation: none !important;
  }
}

  .hero::after {
    animation: none !important;
  }
</style>
