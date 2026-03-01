# Landing Page Visual Improvements Plan

**Branch**: `feature/landing-page-visuals`
**Status**: In Progress
**Date**: 2025-03-01

## Goal

Enhance the landing page's "How It Works" section, Agent cards, and Mars hero 3D globe to create a more immersive, action-oriented visual experience.

---

## Task 1: HowItWorks.vue — Mission Loop Visualization

**Current**: Simple numbered circles (01–04) connected by a gradient line. No iconography or visual depiction of each step.

### Changes:
- [ ] Replace plain numbered circles with action-oriented SVG icons for each step:
  - **Observe** (01): Eye/scanner icon with scan-line animation
  - **Reason** (02): Brain/neural-network icon with pulse animation
  - **Execute** (03): Gear/wrench/tool icon with rotation animation
  - **Adapt** (04): Refresh/adaptive arrows icon with morphing animation
- [ ] Add subtle CSS animations to each icon (pulse, glow, rotation) that trigger on scroll-reveal
- [ ] Enhance the connecting timeline with animated gradient flow (moving particles or dashed-line animation)
- [ ] Add background glow/atmosphere behind each step
- [ ] Keep mobile vertical layout working with the new icons

---

## Task 2: AgentsShowcase.vue — Agent Action Depictions

**Current**: Bento grid with SVG silhouette icons, text description, and tools list. Functional but static.

### Changes:
- [ ] Enhance SVG agent icons with more detail and subtle animation on hover:
  - **Rover**: Wheel rotation animation on hover, dust particles
  - **Drone**: Propeller spin animation on hover, scan beam pulse
  - **Station**: Signal wave emission animation on hover, power glow
- [ ] Add colored accent glow behind each icon matching agent theme color
- [ ] Add subtle background pattern or terrain-like texture to each card
- [ ] Improve hover state with more dynamic transform + glow effects

---

## Task 3: MarsGlobe.vue — 3D Hero Enhancement

**Current**: Procedural Three.js globe with sine/cosine noise texture. Has atmospheric glow shell and floating animation. ~512px texture, basic lighting.

### Changes:
- [ ] Improve procedural texture quality:
  - Higher frequency detail for crater-like features
  - Add Valles Marineris-style canyon features (dark groove across equator)
  - Better polar cap rendering with fade gradient
  - Increase texture resolution to 1024px
- [ ] Enhance atmospheric effects:
  - Add thin dust particle ring/haze at limb
  - Improve atmospheric scattering (Fresnel-based edge glow)
  - Add subtle pulsing to atmosphere opacity
- [ ] Add surface features:
  - Procedural impact craters (circular depressions)
  - Olympus Mons-style volcano highlight
- [ ] Improve lighting:
  - Add subtle rim light for depth
  - Warm the sun color slightly
- [ ] Performance: Keep requestAnimationFrame efficient, limit pixel ratio

---

## Task 4: HeroSection.vue — Visual Impact

**Current**: Text-only hero with badge, title, subtitle, CTAs. Radial gradient overlay for darkening.

### Changes:
- [ ] Add subtle particle/dust effect in the hero area
- [ ] Improve the radial gradient to feel more like looking through Mars atmosphere
- [ ] Consider adding a subtle horizon glow at the bottom of hero

---

## Task 5: Responsive & Accessibility

- [ ] Test all changes at 1440px, 768px, 480px breakpoints
- [ ] Ensure all animations respect `prefers-reduced-motion: reduce`
- [ ] Maintain existing scroll-reveal behavior

---

## Task 6: Changelog & PR

- [ ] Update Changelog.md
- [ ] Create PR with semantic diff template
