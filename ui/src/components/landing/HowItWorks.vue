<script setup>
import { useRevealOnScroll } from '../../composables/useRevealOnScroll.js'

/**
 * HowItWorks — 4-step horizontal timeline showing the mission loop.
 *
 * Displays Observe → Reason → Execute → Update steps with a connecting
 * gradient line. Switches to vertical layout on mobile.
 * Staggered scroll-reveal via IntersectionObserver.
 *
 * Each step features a distinctive SVG icon with CSS animations:
 *  - Observe (i=0): Eye/scanner with horizontal scan-line
 *  - Reason  (i=1): Brain/neural with pulse/glow
 *  - Execute (i=2): Interlocking gears with slow rotation
 *  - Adapt   (i=3): Cycling arrows with rotate-loop
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
        <div
          class="timeline__circle"
          :class="[
            i === 0 ? 'timeline__circle--observe' : '',
            i === 1 ? 'timeline__circle--reason' : '',
            i === 2 ? 'timeline__circle--execute' : '',
            i === 3 ? 'timeline__circle--adapt' : ''
          ]"
        >
          <!-- Observe: Eye/scanner icon -->
          <svg
            v-if="i === 0"
            class="timeline__icon timeline__icon--observe"
            width="28"
            height="28"
            viewBox="0 0 28 28"
            fill="none"
            aria-hidden="true"
          >
            <!-- Eye outline -->
            <path
              d="M2 14C2 14 6 6 14 6C22 6 26 14 26 14C26 14 22 22 14 22C6 22 2 14 2 14Z"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
            <!-- Iris -->
            <circle
              cx="14"
              cy="14"
              r="4"
              stroke="currentColor"
              stroke-width="1.5"
            />
            <!-- Pupil -->
            <circle cx="14" cy="14" r="1.5" fill="currentColor" />
            <!-- Scan line -->
            <line
              class="timeline__scan-line"
              x1="2"
              y1="14"
              x2="26"
              y2="14"
              stroke="currentColor"
              stroke-width="0.75"
              stroke-dasharray="2 2"
              opacity="0.5"
            />
          </svg>

          <!-- Reason: Brain/neural-network icon -->
          <svg
            v-if="i === 1"
            class="timeline__icon timeline__icon--reason"
            width="28"
            height="28"
            viewBox="0 0 28 28"
            fill="none"
            aria-hidden="true"
          >
            <!-- Brain left hemisphere -->
            <path
              d="M14 5C11 5 9 6 8 8C6.5 7.5 5 8.5 5 10.5C4 11 3.5 12.5 4 14C3.5 15.5 4 17 5 18C5 19.5 6 21 8 21.5C9 23 11 24 14 24"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
            <!-- Brain right hemisphere -->
            <path
              d="M14 5C17 5 19 6 20 8C21.5 7.5 23 8.5 23 10.5C24 11 24.5 12.5 24 14C24.5 15.5 24 17 23 18C23 19.5 22 21 20 21.5C19 23 17 24 14 24"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
            <!-- Center fold -->
            <line
              x1="14"
              y1="5"
              x2="14"
              y2="24"
              stroke="currentColor"
              stroke-width="1"
              opacity="0.4"
            />
            <!-- Neural dots -->
            <circle class="timeline__neuron timeline__neuron--1" cx="9" cy="11" r="1.2" fill="currentColor" />
            <circle class="timeline__neuron timeline__neuron--2" cx="19" cy="11" r="1.2" fill="currentColor" />
            <circle class="timeline__neuron timeline__neuron--3" cx="10" cy="17" r="1.2" fill="currentColor" />
            <circle class="timeline__neuron timeline__neuron--4" cx="18" cy="17" r="1.2" fill="currentColor" />
            <circle class="timeline__neuron timeline__neuron--5" cx="14" cy="14" r="1.5" fill="currentColor" />
            <!-- Neural connections -->
            <line x1="9" y1="11" x2="14" y2="14" stroke="currentColor" stroke-width="0.5" opacity="0.3" />
            <line x1="19" y1="11" x2="14" y2="14" stroke="currentColor" stroke-width="0.5" opacity="0.3" />
            <line x1="10" y1="17" x2="14" y2="14" stroke="currentColor" stroke-width="0.5" opacity="0.3" />
            <line x1="18" y1="17" x2="14" y2="14" stroke="currentColor" stroke-width="0.5" opacity="0.3" />
          </svg>

          <!-- Execute: Interlocking gears icon -->
          <svg
            v-if="i === 2"
            class="timeline__icon timeline__icon--execute"
            width="28"
            height="28"
            viewBox="0 0 28 28"
            fill="none"
            aria-hidden="true"
          >
            <!-- Large gear -->
            <g class="timeline__gear timeline__gear--large">
              <circle cx="11" cy="13" r="4" stroke="currentColor" stroke-width="1.5" />
              <circle cx="11" cy="13" r="1.5" fill="currentColor" />
              <!-- Gear teeth -->
              <line x1="11" y1="7" x2="11" y2="9" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
              <line x1="11" y1="17" x2="11" y2="19" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
              <line x1="5" y1="13" x2="7" y2="13" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
              <line x1="15" y1="13" x2="17" y2="13" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
              <line x1="7.2" y1="9.2" x2="8.6" y2="10.6" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
              <line x1="13.4" y1="15.4" x2="14.8" y2="16.8" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
              <line x1="7.2" y1="16.8" x2="8.6" y2="15.4" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
              <line x1="13.4" y1="10.6" x2="14.8" y2="9.2" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
            </g>
            <!-- Small gear -->
            <g class="timeline__gear timeline__gear--small">
              <circle cx="20" cy="18" r="3" stroke="currentColor" stroke-width="1.5" />
              <circle cx="20" cy="18" r="1" fill="currentColor" />
              <!-- Gear teeth -->
              <line x1="20" y1="13.5" x2="20" y2="15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
              <line x1="20" y1="21" x2="20" y2="22.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
              <line x1="15.5" y1="18" x2="17" y2="18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
              <line x1="23" y1="18" x2="24.5" y2="18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
            </g>
          </svg>

          <!-- Adapt: Cycling arrows icon -->
          <svg
            v-if="i === 3"
            class="timeline__icon timeline__icon--adapt"
            width="28"
            height="28"
            viewBox="0 0 28 28"
            fill="none"
            aria-hidden="true"
          >
            <g class="timeline__cycle-arrows">
              <!-- Top-right arrow arc -->
              <path
                d="M18 6C21.5 8 23.5 11.5 23 15.5"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
              />
              <polyline
                points="21,15 23,16 25,14"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
              <!-- Bottom-left arrow arc -->
              <path
                d="M10 22C6.5 20 4.5 16.5 5 12.5"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
              />
              <polyline
                points="7,13 5,12 3,14"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
              <!-- Top-left arrow arc -->
              <path
                d="M10 6C7.5 7.5 5.5 10 5 13"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                opacity="0.4"
              />
              <!-- Bottom-right arrow arc -->
              <path
                d="M18 22C20.5 20.5 22.5 18 23 15"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                opacity="0.4"
              />
              <!-- Center dot -->
              <circle cx="14" cy="14" r="2" stroke="currentColor" stroke-width="1.5" />
              <circle cx="14" cy="14" r="0.8" fill="currentColor" />
            </g>
          </svg>

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

/* Connecting gradient line — animated flow */
.timeline::before {
  content: '';
  position: absolute;
  top: 31px; /* center of 64px circle */
  left: 32px;
  right: 32px;
  height: 2px;
  background: linear-gradient(
    90deg,
    var(--mars-sunset),
    var(--accent-cyan),
    var(--mars-sunset),
    var(--accent-cyan)
  );
  background-size: 200% 100%;
  z-index: 1;
  opacity: 0;
  transition: opacity 0.8s ease 0.3s;
  animation: timeline-flow 4s linear infinite;
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
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--glass-bg);
  border: 2px solid var(--mars-sunset);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1.5rem;
  position: relative;
  z-index: 2;
  gap: 2px;
  transition: background 0.3s ease, transform 0.3s ease, box-shadow 0.3s ease;
}

/* Radial glow behind each circle */
.timeline__circle::before {
  content: '';
  position: absolute;
  inset: -8px;
  border-radius: 50%;
  background: radial-gradient(
    circle,
    rgba(255, 107, 53, 0.15) 0%,
    transparent 70%
  );
  z-index: -1;
  transition: opacity 0.3s ease;
  opacity: 0.6;
}

.timeline__circle:hover {
  background: rgba(255, 107, 53, 0.12);
  transform: scale(1.15);
  box-shadow:
    0 0 20px rgba(255, 107, 53, 0.25),
    0 0 40px rgba(255, 107, 53, 0.1);
}

.timeline__circle:hover::before {
  opacity: 1;
}

.timeline__circle:hover .timeline__number {
  color: var(--accent-cyan);
}

.timeline__circle:hover .timeline__icon {
  color: #fff;
}

/* ─── Icon base ─── */

.timeline__icon {
  color: var(--mars-sunset);
  transition: color 0.3s ease, filter 0.3s ease;
  flex-shrink: 0;
}

/* ─── Number badge below icon ─── */

.timeline__number {
  font-family: var(--font-mono);
  font-size: 0.6rem;
  font-weight: 700;
  color: var(--mars-sunset);
  transition: color 0.3s ease;
  line-height: 1;
  opacity: 0.7;
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

/* ═══════════════════════════════════════════════
   ICON ANIMATIONS
   ═══════════════════════════════════════════════ */

/* ─── Observe: Horizontal scan-line sweep ─── */

.timeline__scan-line {
  animation: scan-sweep 3s ease-in-out infinite;
  transform-origin: center;
}

@keyframes scan-sweep {
  0%, 100% { opacity: 0.15; transform: translateY(-4px); }
  50%      { opacity: 0.7;  transform: translateY(4px); }
}

/* ─── Reason: Neural pulse/glow ─── */

.timeline__icon--reason {
  animation: brain-glow 3s ease-in-out infinite;
}

@keyframes brain-glow {
  0%, 100% { filter: drop-shadow(0 0 0px transparent); }
  50%      { filter: drop-shadow(0 0 6px rgba(255, 107, 53, 0.5)); }
}

.timeline__neuron {
  animation: neuron-pulse 2s ease-in-out infinite;
}

.timeline__neuron--1 { animation-delay: 0s; }
.timeline__neuron--2 { animation-delay: 0.4s; }
.timeline__neuron--3 { animation-delay: 0.8s; }
.timeline__neuron--4 { animation-delay: 1.2s; }
.timeline__neuron--5 { animation-delay: 0.2s; }

@keyframes neuron-pulse {
  0%, 100% { opacity: 0.4; r: 1.2; }
  50%      { opacity: 1;   r: 1.8; }
}

/* ─── Execute: Gear rotation ─── */

.timeline__gear--large {
  animation: gear-spin 6s linear infinite;
  transform-origin: 11px 13px;
}

.timeline__gear--small {
  animation: gear-spin-reverse 4s linear infinite;
  transform-origin: 20px 18px;
}

@keyframes gear-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

@keyframes gear-spin-reverse {
  from { transform: rotate(0deg); }
  to   { transform: rotate(-360deg); }
}

/* ─── Adapt: Cycling arrows rotation ─── */

.timeline__cycle-arrows {
  animation: cycle-rotate 8s linear infinite;
  transform-origin: 14px 14px;
}

@keyframes cycle-rotate {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/* ═══════════════════════════════════════════════
   TIMELINE FLOW ANIMATION
   ═══════════════════════════════════════════════ */

@keyframes timeline-flow {
  0%   { background-position: 0% 0; }
  100% { background-position: 200% 0; }
}

/* ═══════════════════════════════════════════════
   PER-STEP CIRCLE MODIFIERS (accent glow colors)
   ═══════════════════════════════════════════════ */

.timeline__circle--observe:hover {
  box-shadow:
    0 0 20px rgba(255, 107, 53, 0.3),
    0 0 40px rgba(255, 107, 53, 0.12);
}

.timeline__circle--reason:hover {
  box-shadow:
    0 0 20px rgba(0, 212, 255, 0.25),
    0 0 40px rgba(0, 212, 255, 0.1);
}

.timeline__circle--execute:hover {
  box-shadow:
    0 0 20px rgba(255, 167, 53, 0.3),
    0 0 40px rgba(255, 167, 53, 0.12);
}

.timeline__circle--adapt:hover {
  box-shadow:
    0 0 20px rgba(0, 212, 255, 0.3),
    0 0 40px rgba(0, 212, 255, 0.12);
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
    left: 31px; /* center of 64px circle */
    right: auto;
    width: 2px;
    height: 100%;
    background: linear-gradient(
      180deg,
      var(--mars-sunset),
      var(--accent-cyan),
      var(--mars-sunset),
      var(--accent-cyan)
    );
    background-size: 100% 200%;
    animation: timeline-flow-vertical 4s linear infinite;
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

@keyframes timeline-flow-vertical {
  0%   { background-position: 0 0%; }
  100% { background-position: 0 200%; }
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
    animation: none;
  }

  .timeline__scan-line,
  .timeline__icon--reason,
  .timeline__neuron,
  .timeline__gear--large,
  .timeline__gear--small,
  .timeline__cycle-arrows {
    animation: none;
  }

  .timeline__circle::before {
    animation: none;
  }
}
</style>
