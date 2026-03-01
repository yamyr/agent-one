<script setup>
import { computed } from 'vue'

/**
 * StarField — Multi-layer CSS particle starfield
 *
 * Three depth layers of stars rendered via box-shadow,
 * drifting upward at different speeds to create parallax.
 * 8-10 twinkling accent stars pulse independently.
 *
 * Pure CSS animation, GPU-accelerated, respects prefers-reduced-motion.
 */

// Star color palette — mostly white with subtle temperature shifts
const COLORS = [
  '#ffffff', '#ffffff', '#ffffff', '#ffffff', '#ffffff',
  '#f0f4ff', '#e8eeff', '#aaccff', '#bbd4ff',  // cool blue hints
  '#ffeedc', '#ffddaa', '#ffe8c8',               // warm amber hints
]

function pickColor() {
  return COLORS[Math.floor(Math.random() * COLORS.length)]
}

/**
 * Generate box-shadow string for a star layer.
 * Each star is a 1px dot at a random viewport position.
 * We double the height range (2000px) so the drift animation
 * wraps seamlessly when translateY shifts by -100vh.
 */
function generateStarShadows(count) {
  const shadows = []
  for (let i = 0; i < count; i++) {
    const x = Math.floor(Math.random() * 2560)
    const y = Math.floor(Math.random() * 2560)
    const color = pickColor()
    shadows.push(`${x}px ${y}px ${color}`)
  }
  return shadows.join(', ')
}

// Pre-compute star layers at component setup time
const layerFar = computed(() => generateStarShadows(200))
const layerMid = computed(() => generateStarShadows(100))
const layerNear = computed(() => generateStarShadows(50))

// Twinkling stars — 10 positioned randomly with varying pulse speeds
const twinklingStars = computed(() => {
  const stars = []
  for (let i = 0; i < 10; i++) {
    stars.push({
      id: i,
      left: `${Math.random() * 100}%`,
      top: `${Math.random() * 100}%`,
      duration: `${3 + Math.random() * 2}s`,
      delay: `${Math.random() * 5}s`,
      size: `${1.5 + Math.random() * 1.5}px`,
      color: pickColor(),
    })
  }
  return stars
})
</script>

<template>
  <div class="starfield" aria-hidden="true">
    <!-- Layer 1: Far stars — tiny, slow, dim -->
    <div
      class="star-layer star-layer--far"
      :style="{ boxShadow: layerFar }"
    />

    <!-- Layer 2: Mid stars — medium, moderate -->
    <div
      class="star-layer star-layer--mid"
      :style="{ boxShadow: layerMid }"
    />

    <!-- Layer 3: Near stars — larger, faster, bright -->
    <div
      class="star-layer star-layer--near"
      :style="{ boxShadow: layerNear }"
    />

    <!-- Twinkling accent stars -->
    <div
      v-for="star in twinklingStars"
      :key="star.id"
      class="twinkle-star"
      :style="{
        left: star.left,
        top: star.top,
        width: star.size,
        height: star.size,
        backgroundColor: star.color,
        animationDuration: star.duration,
        animationDelay: star.delay,
      }"
    />
  </div>
</template>

<style scoped>
.starfield {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
  background: transparent;
}

/* ─── Star Layers ─── */

.star-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 1px;
  height: 1px;
  border-radius: 50%;
  will-change: transform;
}

/* Far: 200 stars, 1px, very slow drift, dim */
.star-layer--far {
  opacity: 0.55;
  animation: drift 200s linear infinite;
}

/* Mid: 100 stars, 1.5px visible via scale, medium drift */
.star-layer--mid {
  opacity: 0.75;
  transform-origin: 0 0;
  width: 1.5px;
  height: 1.5px;
  animation: drift 150s linear infinite;
}

/* Near: 50 stars, 2px, faster drift, bright */
.star-layer--near {
  opacity: 0.9;
  width: 2px;
  height: 2px;
  animation: drift 100s linear infinite;
}

@keyframes drift {
  from {
    transform: translateY(0);
  }
  to {
    transform: translateY(-2560px);
  }
}

/* ─── Twinkling Stars ─── */

.twinkle-star {
  position: absolute;
  border-radius: 50%;
  animation: twinkle ease-in-out infinite;
  will-change: opacity, box-shadow;
  box-shadow: 0 0 4px 1px currentColor;
}

@keyframes twinkle {
  0%,
  100% {
    opacity: 0.3;
    box-shadow: 0 0 3px 0px currentColor;
  }
  50% {
    opacity: 1;
    box-shadow: 0 0 8px 2px currentColor;
  }
}

/* ─── Accessibility ─── */

@media (prefers-reduced-motion: reduce) {
  .star-layer {
    animation: none !important;
  }
  .twinkle-star {
    animation: none !important;
    opacity: 0.6;
  }
}
</style>
