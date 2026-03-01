<script setup>
import { useRevealOnScroll } from '../../composables/useRevealOnScroll.js'

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

const { sectionRef, visible } = useRevealOnScroll()

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
        <div class="agent-card__icon-wrap agent-card__icon-wrap--rover">
          <svg class="agent-card__icon" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <!-- Rover body chassis -->
            <rect x="10" y="22" width="44" height="14" rx="4" :stroke="agents[0].themeColor" stroke-width="1.4" fill="none" />
            <!-- Top instrument deck -->
            <rect x="18" y="14" width="22" height="10" rx="3" :stroke="agents[0].themeColor" stroke-width="1.4" fill="none" />
            <!-- Instrument panel lines -->
            <line x1="22" y1="17" x2="22" y2="21" :stroke="agents[0].themeColor" stroke-width="0.8" opacity="0.5" />
            <line x1="26" y1="17" x2="26" y2="21" :stroke="agents[0].themeColor" stroke-width="0.8" opacity="0.5" />
            <!-- Articulated camera mast -->
            <line x1="30" y1="14" x2="28" y2="8" :stroke="agents[0].themeColor" stroke-width="1.4" stroke-linecap="round" />
            <line x1="28" y1="8" x2="24" y2="5" :stroke="agents[0].themeColor" stroke-width="1.4" stroke-linecap="round" />
            <circle cx="22" cy="4" r="2.5" :stroke="agents[0].themeColor" stroke-width="1.2" fill="none" />
            <circle cx="22" cy="4" r="0.8" :fill="agents[0].themeColor" opacity="0.6" />
            <!-- Drill arm (right side) -->
            <line x1="50" y1="26" x2="56" y2="22" :stroke="agents[0].themeColor" stroke-width="1.2" stroke-linecap="round" />
            <line x1="56" y1="22" x2="58" y2="28" :stroke="agents[0].themeColor" stroke-width="1.2" stroke-linecap="round" />
            <line x1="58" y1="28" x2="58" y2="32" :stroke="agents[0].themeColor" stroke-width="1" stroke-linecap="round" stroke-dasharray="1 1.5" />
            <!-- Suspension struts -->
            <line x1="16" y1="36" x2="14" y2="42" :stroke="agents[0].themeColor" stroke-width="1" stroke-linecap="round" />
            <line x1="32" y1="36" x2="32" y2="42" :stroke="agents[0].themeColor" stroke-width="1" stroke-linecap="round" />
            <line x1="48" y1="36" x2="50" y2="42" :stroke="agents[0].themeColor" stroke-width="1" stroke-linecap="round" />
            <!-- Wheels with treads — CSS rotates these on hover -->
            <g class="rover-wheel rover-wheel--1">
              <circle cx="14" cy="48" r="6" :stroke="agents[0].themeColor" stroke-width="1.4" fill="none" />
              <circle cx="14" cy="48" r="3" :stroke="agents[0].themeColor" stroke-width="0.8" fill="none" opacity="0.4" />
              <!-- Tread spokes -->
              <line x1="14" y1="42" x2="14" y2="54" :stroke="agents[0].themeColor" stroke-width="0.6" opacity="0.3" />
              <line x1="8" y1="48" x2="20" y2="48" :stroke="agents[0].themeColor" stroke-width="0.6" opacity="0.3" />
            </g>
            <g class="rover-wheel rover-wheel--2">
              <circle cx="32" cy="48" r="6" :stroke="agents[0].themeColor" stroke-width="1.4" fill="none" />
              <circle cx="32" cy="48" r="3" :stroke="agents[0].themeColor" stroke-width="0.8" fill="none" opacity="0.4" />
              <line x1="32" y1="42" x2="32" y2="54" :stroke="agents[0].themeColor" stroke-width="0.6" opacity="0.3" />
              <line x1="26" y1="48" x2="38" y2="48" :stroke="agents[0].themeColor" stroke-width="0.6" opacity="0.3" />
            </g>
            <g class="rover-wheel rover-wheel--3">
              <circle cx="50" cy="48" r="6" :stroke="agents[0].themeColor" stroke-width="1.4" fill="none" />
              <circle cx="50" cy="48" r="3" :stroke="agents[0].themeColor" stroke-width="0.8" fill="none" opacity="0.4" />
              <line x1="50" y1="42" x2="50" y2="54" :stroke="agents[0].themeColor" stroke-width="0.6" opacity="0.3" />
              <line x1="44" y1="48" x2="56" y2="48" :stroke="agents[0].themeColor" stroke-width="0.6" opacity="0.3" />
            </g>
            <!-- Antenna on top -->
            <line x1="36" y1="14" x2="38" y2="8" :stroke="agents[0].themeColor" stroke-width="0.8" stroke-linecap="round" opacity="0.6" />
            <circle cx="38" cy="7" r="1" :fill="agents[0].themeColor" opacity="0.5" />
          </svg>
        </div>
        <h3 class="agent-card__name">{{ $t(agents[0].nameKey) }}</h3>
        <span class="agent-card__role">{{ $t(agents[0].roleKey) }}</span>
        <p class="agent-card__desc">{{ $t(agents[0].descKey) }}</p>
        <span class="agent-card__tools">{{ $t(agents[0].toolsKey) }}</span>
      </div>

      <!-- Drone — top right -->
      <div class="agent-card agent-card--drone">
        <div class="agent-card__icon-wrap agent-card__icon-wrap--drone">
          <svg class="agent-card__icon" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <!-- Central body -->
            <circle cx="32" cy="32" r="6" :stroke="agents[1].themeColor" stroke-width="1.4" fill="none" />
            <!-- Camera lens -->
            <circle cx="32" cy="34" r="2.5" :stroke="agents[1].themeColor" stroke-width="1" fill="none" />
            <circle cx="32" cy="34" r="1" :fill="agents[1].themeColor" opacity="0.6" />
            <!-- Body panel lines -->
            <path d="M26 30 L26 34" :stroke="agents[1].themeColor" stroke-width="0.6" opacity="0.4" />
            <path d="M38 30 L38 34" :stroke="agents[1].themeColor" stroke-width="0.6" opacity="0.4" />
            <!-- Arms to rotors -->
            <line x1="27" y1="27" x2="14" y2="14" :stroke="agents[1].themeColor" stroke-width="1.4" stroke-linecap="round" />
            <line x1="37" y1="27" x2="50" y2="14" :stroke="agents[1].themeColor" stroke-width="1.4" stroke-linecap="round" />
            <line x1="27" y1="37" x2="14" y2="50" :stroke="agents[1].themeColor" stroke-width="1.4" stroke-linecap="round" />
            <line x1="37" y1="37" x2="50" y2="50" :stroke="agents[1].themeColor" stroke-width="1.4" stroke-linecap="round" />
            <!-- Motor hubs -->
            <circle cx="14" cy="14" r="2" :stroke="agents[1].themeColor" stroke-width="0.8" fill="none" opacity="0.5" />
            <circle cx="50" cy="14" r="2" :stroke="agents[1].themeColor" stroke-width="0.8" fill="none" opacity="0.5" />
            <circle cx="14" cy="50" r="2" :stroke="agents[1].themeColor" stroke-width="0.8" fill="none" opacity="0.5" />
            <circle cx="50" cy="50" r="2" :stroke="agents[1].themeColor" stroke-width="0.8" fill="none" opacity="0.5" />
            <!-- Propeller blades — CSS rotates these on hover -->
            <ellipse class="drone-prop drone-prop--1" cx="14" cy="14" rx="8" ry="2.5" :stroke="agents[1].themeColor" stroke-width="1" fill="none" />
            <ellipse class="drone-prop drone-prop--2" cx="50" cy="14" rx="8" ry="2.5" :stroke="agents[1].themeColor" stroke-width="1" fill="none" />
            <ellipse class="drone-prop drone-prop--3" cx="14" cy="50" rx="8" ry="2.5" :stroke="agents[1].themeColor" stroke-width="1" fill="none" />
            <ellipse class="drone-prop drone-prop--4" cx="50" cy="50" rx="8" ry="2.5" :stroke="agents[1].themeColor" stroke-width="1" fill="none" />
            <!-- Scanning beam lines (downward from camera) -->
            <line class="drone-scan drone-scan--1" x1="30" y1="38" x2="24" y2="58" :stroke="agents[1].themeColor" stroke-width="0.6" opacity="0.2" stroke-dasharray="2 2" />
            <line class="drone-scan drone-scan--2" x1="32" y1="38" x2="32" y2="60" :stroke="agents[1].themeColor" stroke-width="0.6" opacity="0.3" stroke-dasharray="2 2" />
            <line class="drone-scan drone-scan--3" x1="34" y1="38" x2="40" y2="58" :stroke="agents[1].themeColor" stroke-width="0.6" opacity="0.2" stroke-dasharray="2 2" />
          </svg>
        </div>
        <h3 class="agent-card__name">{{ $t(agents[1].nameKey) }}</h3>
        <span class="agent-card__role">{{ $t(agents[1].roleKey) }}</span>
        <p class="agent-card__desc">{{ $t(agents[1].descKey) }}</p>
        <span class="agent-card__tools">{{ $t(agents[1].toolsKey) }}</span>
      </div>

      <!-- Station — bottom right -->
      <div class="agent-card agent-card--station">
        <div class="agent-card__icon-wrap agent-card__icon-wrap--station">
          <svg class="agent-card__icon" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <!-- Main structure / tower -->
            <rect x="26" y="24" width="12" height="20" rx="2" :stroke="agents[2].themeColor" stroke-width="1.4" fill="none" />
            <!-- Panel detail lines -->
            <line x1="29" y1="28" x2="35" y2="28" :stroke="agents[2].themeColor" stroke-width="0.6" opacity="0.4" />
            <line x1="29" y1="32" x2="35" y2="32" :stroke="agents[2].themeColor" stroke-width="0.6" opacity="0.4" />
            <line x1="29" y1="36" x2="35" y2="36" :stroke="agents[2].themeColor" stroke-width="0.6" opacity="0.4" />
            <!-- Status lights -->
            <circle cx="30" cy="40" r="1" :fill="agents[2].themeColor" opacity="0.6" />
            <circle cx="34" cy="40" r="1" :fill="agents[2].themeColor" opacity="0.4" />
            <!-- Antenna mast -->
            <line x1="32" y1="24" x2="32" y2="10" :stroke="agents[2].themeColor" stroke-width="1.4" stroke-linecap="round" />
            <circle cx="32" cy="8" r="2" :stroke="agents[2].themeColor" stroke-width="1.2" fill="none" />
            <circle cx="32" cy="8" r="0.8" :fill="agents[2].themeColor" opacity="0.6" />
            <!-- Signal waves emanating from antenna — CSS pulses these -->
            <path class="station-wave station-wave--1" d="M24 8 Q28 2 32 4 Q36 2 40 8" :stroke="agents[2].themeColor" stroke-width="0.8" fill="none" opacity="0.5" stroke-linecap="round" />
            <path class="station-wave station-wave--2" d="M20 6 Q26 -2 32 1 Q38 -2 44 6" :stroke="agents[2].themeColor" stroke-width="0.6" fill="none" opacity="0.3" stroke-linecap="round" />
            <path class="station-wave station-wave--3" d="M16 4 Q24 -6 32 -2 Q40 -6 48 4" :stroke="agents[2].themeColor" stroke-width="0.5" fill="none" opacity="0.15" stroke-linecap="round" />
            <!-- Left solar panel -->
            <rect x="4" y="30" width="18" height="8" rx="1" :stroke="agents[2].themeColor" stroke-width="1.2" fill="none" />
            <line x1="10" y1="30" x2="10" y2="38" :stroke="agents[2].themeColor" stroke-width="0.6" opacity="0.3" />
            <line x1="16" y1="30" x2="16" y2="38" :stroke="agents[2].themeColor" stroke-width="0.6" opacity="0.3" />
            <line x1="4" y1="34" x2="22" y2="34" :stroke="agents[2].themeColor" stroke-width="0.6" opacity="0.3" />
            <!-- Right solar panel -->
            <rect x="42" y="30" width="18" height="8" rx="1" :stroke="agents[2].themeColor" stroke-width="1.2" fill="none" />
            <line x1="48" y1="30" x2="48" y2="38" :stroke="agents[2].themeColor" stroke-width="0.6" opacity="0.3" />
            <line x1="54" y1="30" x2="54" y2="38" :stroke="agents[2].themeColor" stroke-width="0.6" opacity="0.3" />
            <line x1="42" y1="34" x2="60" y2="34" :stroke="agents[2].themeColor" stroke-width="0.6" opacity="0.3" />
            <!-- Base / foundation -->
            <line x1="20" y1="44" x2="44" y2="44" :stroke="agents[2].themeColor" stroke-width="1.4" stroke-linecap="round" />
            <!-- Ground support legs -->
            <line x1="24" y1="44" x2="20" y2="50" :stroke="agents[2].themeColor" stroke-width="1" stroke-linecap="round" />
            <line x1="40" y1="44" x2="44" y2="50" :stroke="agents[2].themeColor" stroke-width="1" stroke-linecap="round" />
            <!-- Ground line -->
            <line x1="14" y1="50" x2="50" y2="50" :stroke="agents[2].themeColor" stroke-width="0.8" opacity="0.3" stroke-linecap="round" />
          </svg>
        </div>
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
  position: relative;
  overflow: hidden;
  transition:
    opacity 0.6s ease,
    transform 0.6s ease,
    border-color 0.3s ease,
    box-shadow 0.3s ease;
}

/* ─── Card Background Patterns ─── */

.agent-card::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.04;
  transition: opacity 0.3s ease;
  z-index: 0;
}

.agent-card--rover::before {
  /* Topographic contour pattern */
  background:
    repeating-conic-gradient(
      from 0deg at 40% 60%,
      transparent 0deg,
      transparent 356deg,
      var(--mars-rust) 356deg,
      var(--mars-rust) 360deg
    ),
    radial-gradient(ellipse 120% 80% at 40% 60%, var(--mars-rust) 0%, transparent 50%),
    radial-gradient(ellipse 100% 60% at 40% 60%, var(--mars-rust) 0%, transparent 42%),
    radial-gradient(ellipse 80% 40% at 40% 60%, var(--mars-rust) 0%, transparent 34%);
}

.agent-card--drone::before {
  /* Grid scan pattern */
  background:
    linear-gradient(0deg, transparent 49.5%, var(--accent-cyan) 49.5%, var(--accent-cyan) 50.5%, transparent 50.5%),
    linear-gradient(90deg, transparent 49.5%, var(--accent-cyan) 49.5%, var(--accent-cyan) 50.5%, transparent 50.5%);
  background-size: 24px 24px;
}

.agent-card--station::before {
  /* Signal wave / concentric pattern */
  background:
    radial-gradient(circle at 50% 30%, transparent 20%, var(--accent-amber) 20.5%, var(--accent-amber) 21%, transparent 21.5%),
    radial-gradient(circle at 50% 30%, transparent 35%, var(--accent-amber) 35.5%, var(--accent-amber) 36%, transparent 36.5%),
    radial-gradient(circle at 50% 30%, transparent 50%, var(--accent-amber) 50.5%, var(--accent-amber) 51%, transparent 51.5%);
}

.agent-card:hover::before {
  opacity: 0.07;
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
  transform: translateY(-6px);
  box-shadow:
    0 12px 40px rgba(183, 65, 14, 0.2),
    0 0 0 1px rgba(178, 110, 82, 0.1);
}

.agent-card--drone:hover {
  border-color: var(--accent-cyan);
  transform: translateY(-6px);
  box-shadow:
    0 12px 40px rgba(0, 212, 255, 0.2),
    0 0 0 1px rgba(0, 212, 255, 0.1);
}

.agent-card--station:hover {
  border-color: var(--accent-amber);
  transform: translateY(-6px);
  box-shadow:
    0 12px 40px rgba(204, 136, 68, 0.2),
    0 0 0 1px rgba(204, 136, 68, 0.1);
}

/* ─── Icon Wrapper with Glow Aura ─── */

.agent-card__icon-wrap {
  position: relative;
  width: 56px;
  height: 56px;
  margin-bottom: 1.25rem;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
}

.agent-card__icon-wrap::before {
  content: '';
  position: absolute;
  inset: -8px;
  border-radius: 50%;
  filter: blur(14px);
  opacity: 0.25;
  transition: opacity 0.4s ease, filter 0.4s ease;
  z-index: -1;
}

.agent-card__icon-wrap--rover::before {
  background: var(--mars-rust);
}

.agent-card__icon-wrap--drone::before {
  background: var(--accent-cyan);
}

.agent-card__icon-wrap--station::before {
  background: var(--accent-amber);
}

.agent-card:hover .agent-card__icon-wrap::before {
  opacity: 0.5;
  filter: blur(18px);
}

/* ─── Card Inner Elements ─── */

.agent-card__icon {
  width: 56px;
  height: 56px;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.agent-card__name {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 0.25rem 0;
  position: relative;
  z-index: 1;
}

.agent-card__role {
  display: block;
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 0.75rem;
  position: relative;
  z-index: 1;
}

.agent-card__desc {
  color: var(--text-secondary);
  font-size: 0.85rem;
  line-height: 1.7;
  margin: 0;
  flex: 1;
  position: relative;
  z-index: 1;
}

.agent-card__tools {
  display: block;
  font-size: 0.7rem;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  margin-top: auto;
  padding-top: 1rem;
  border-top: 1px solid var(--glass-border);
  position: relative;
  z-index: 1;
}

/* ─── Rover Wheel Spin Animation ─── */

.rover-wheel {
  transition: none;
}

.agent-card--rover:hover .rover-wheel {
  animation: rover-wheel-spin 2s linear infinite;
}

.rover-wheel--1 {
  transform-origin: 14px 48px;
}

.rover-wheel--2 {
  transform-origin: 32px 48px;
}

.rover-wheel--3 {
  transform-origin: 50px 48px;
}

@keyframes rover-wheel-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/* ─── Drone Propeller Spin Animation ─── */

.drone-prop {
  transition: none;
}

.agent-card--drone:hover .drone-prop {
  animation: drone-prop-spin 0.4s linear infinite;
}

.drone-prop--1 {
  transform-origin: 14px 14px;
}

.drone-prop--2 {
  transform-origin: 50px 14px;
}

.drone-prop--3 {
  transform-origin: 14px 50px;
}

.drone-prop--4 {
  transform-origin: 50px 50px;
}

@keyframes drone-prop-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/* Scanning beam pulse on hover */
.drone-scan {
  transition: opacity 0.3s ease;
}

.agent-card--drone:hover .drone-scan {
  animation: drone-scan-pulse 1.5s ease-in-out infinite;
}

.agent-card--drone:hover .drone-scan--1 {
  animation-delay: 0s;
}

.agent-card--drone:hover .drone-scan--2 {
  animation-delay: 0.2s;
}

.agent-card--drone:hover .drone-scan--3 {
  animation-delay: 0.4s;
}

@keyframes drone-scan-pulse {
  0%, 100% { opacity: 0.15; }
  50%      { opacity: 0.5; }
}

/* ─── Station Signal Wave Pulse Animation ─── */

.station-wave {
  transition: opacity 0.3s ease;
}

.agent-card--station:hover .station-wave {
  animation: station-signal-pulse 2s ease-in-out infinite;
}

.agent-card--station:hover .station-wave--1 {
  animation-delay: 0s;
}

.agent-card--station:hover .station-wave--2 {
  animation-delay: 0.3s;
}

.agent-card--station:hover .station-wave--3 {
  animation-delay: 0.6s;
}

@keyframes station-signal-pulse {
  0%   { opacity: 0; transform: translateY(2px); }
  30%  { opacity: 0.6; transform: translateY(-1px); }
  60%  { opacity: 0.3; transform: translateY(-3px); }
  100% { opacity: 0; transform: translateY(-5px); }
}

.station-wave--1 { transform-origin: center 8px; }
.station-wave--2 { transform-origin: center 6px; }
.station-wave--3 { transform-origin: center 4px; }

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

  .agent-card::before {
    transition: none;
  }

  .agent-card__icon-wrap::before {
    transition: none;
  }

  .agent-card--rover:hover .rover-wheel,
  .agent-card--drone:hover .drone-prop,
  .agent-card--drone:hover .drone-scan,
  .agent-card--station:hover .station-wave {
    animation: none;
  }

  .agent-card--rover:hover,
  .agent-card--drone:hover,
  .agent-card--station:hover {
    transform: none;
  }
}
</style>
