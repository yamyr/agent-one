<script setup>
import { useRevealOnScroll } from '../../composables/useRevealOnScroll.js'

/**
 * HowItWorks — 4-step horizontal timeline showing the mission loop.
 *
 * Displays Observe → Reason → Execute → Update steps with a connecting
 * gradient line. Switches to vertical layout on mobile.
 * Staggered scroll-reveal via IntersectionObserver.
 */

const { sectionRef, visible } = useRevealOnScroll()

</script>

<template>
  <section
    id="how-it-works"
    ref="sectionRef"
    class="how-it-works"
    :class="{ visible }"
  >
    <span class="how-it-works__label">{{ $t('how_it_works.label') }}</span>
    <h2 class="how-it-works__title">{{ $t('how_it_works.title') }}</h2>

    <div class="timeline">
      <div
        v-for="(step, i) in $tm('how_it_works.steps')"
        :key="i"
        class="timeline__step"
      >
        <div class="timeline__circle">
          <span class="timeline__number">{{ step.number }}</span>
        </div>
        <h3 class="timeline__step-title">{{ step.title }}</h3>
        <p class="timeline__step-desc">{{ step.desc }}</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.how-it-works {
  padding: 6rem 5%;
  max-width: 1200px;
  margin: 0 auto;
}

/* ─── Section Header ─── */

.how-it-works__label {
  display: block;
  font-size: 0.75rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--mars-sunset);
  font-family: var(--font-mono);
  margin-bottom: 1rem;
  opacity: 0;
  transform: translateX(-30px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}

.how-it-works__title {
  font-family: var(--font-display);
  font-size: clamp(1.5rem, 3vw, 2.5rem);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 3rem 0;
  opacity: 0;
  transform: translateX(-30px);
  transition: opacity 0.6s ease 0.1s, transform 0.6s ease 0.1s;
}

/* ─── Timeline ─── */

.timeline {
  display: flex;
  gap: 2rem;
  position: relative;
}

/* Connecting gradient line */
.timeline::before {
  content: '';
  position: absolute;
  top: 23px; /* center of 48px circle */
  left: 24px;
  right: 24px;
  height: 2px;
  background: linear-gradient(
    to right,
    var(--mars-sunset),
    var(--accent-cyan)
  );
  z-index: 1;
  opacity: 0;
  transition: opacity 0.8s ease 0.3s;
}

/* ─── Step ─── */

.timeline__step {
  flex: 1;
  text-align: center;
  opacity: 0;
  transform: translateX(-30px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}

/* Stagger delays — 200ms per step */
.timeline__step:nth-child(1) { transition-delay: 0.2s; }
.timeline__step:nth-child(2) { transition-delay: 0.4s; }
.timeline__step:nth-child(3) { transition-delay: 0.6s; }
.timeline__step:nth-child(4) { transition-delay: 0.8s; }

/* ─── Step Circle ─── */

.timeline__circle {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--glass-bg);
  border: 2px solid var(--mars-sunset);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1.5rem;
  position: relative;
  z-index: 2;
  transition: background 0.3s ease, color 0.3s ease, transform 0.3s ease;
}

.timeline__circle:hover {
  background: var(--mars-sunset);
  transform: scale(1.1);
}

.timeline__circle:hover .timeline__number {
  color: #fff;
}

.timeline__number {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--mars-sunset);
  transition: color 0.3s ease;
}

/* ─── Step Content ─── */

.timeline__step-title {
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.5rem 0;
}

.timeline__step-desc {
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0;
}

/* ─── Visible State ─── */

.how-it-works.visible .how-it-works__label,
.how-it-works.visible .how-it-works__title,
.how-it-works.visible .timeline__step {
  opacity: 1;
  transform: translateX(0);
}

.how-it-works.visible .timeline::before {
  opacity: 1;
}

/* ─── Responsive: Vertical Timeline ─── */

@media (max-width: 768px) {
  .timeline {
    flex-direction: column;
    padding-left: 40px;
  }

  .timeline::before {
    top: 0;
    bottom: 0;
    left: 23px; /* center of 48px circle */
    right: auto;
    width: 2px;
    height: 100%;
    background: linear-gradient(
      to bottom,
      var(--mars-sunset),
      var(--accent-cyan)
    );
  }

  .timeline__step {
    text-align: left;
    display: grid;
    grid-template-columns: auto 1fr;
    grid-template-rows: auto auto;
    column-gap: 1.5rem;
    row-gap: 0;
    align-items: start;
  }

  .timeline__circle {
    margin: 0;
    grid-row: 1 / 3;
    grid-column: 1;
    position: relative;
    left: -40px;
  }

  .timeline__step-title {
    grid-column: 2;
    grid-row: 1;
    padding-top: 0.25rem;
  }

  .timeline__step-desc {
    grid-column: 2;
    grid-row: 2;
  }
}

/* ─── Accessibility ─── */

@media (prefers-reduced-motion: reduce) {
  .how-it-works__label,
  .how-it-works__title,
  .timeline__step,
  .timeline__circle {
    opacity: 1;
    transform: none;
    transition: none;
  }

  .timeline::before {
    opacity: 1;
    transition: none;
  }
}
</style>
