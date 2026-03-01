<script setup>
import StarField from '../components/landing/StarField.vue'
import MarsGlobe from '../components/landing/MarsGlobe.vue'
import NavBar from '../components/landing/NavBar.vue'
import HeroSection from '../components/landing/HeroSection.vue'
import MissionBriefing from '../components/landing/MissionBriefing.vue'
import AgentsShowcase from '../components/landing/AgentsShowcase.vue'
import FeaturesGrid from '../components/landing/FeaturesGrid.vue'
import HowItWorks from '../components/landing/HowItWorks.vue'
import TechStack from '../components/landing/TechStack.vue'
import CTASection from '../components/landing/CTASection.vue'
import FooterSection from '../components/landing/FooterSection.vue'
</script>
<template>
  <div class="landing">
    <StarField />
    <MarsGlobe />
    <NavBar />
    <main>
      <HeroSection />
      <MissionBriefing />
      <AgentsShowcase />
      <FeaturesGrid />
      <HowItWorks />
      <TechStack />
      <CTASection />
    </main>
    <FooterSection />
  </div>
</template>

<style>
/* Landing-page design tokens — scoped via .landing class, not polluting global :root */
.landing {
  --space-void: #05020e;
  --space-midnight: #0a0a0f;
  --space-dark: #0c0c14;
  --mars-red: #924737;
  --mars-rust: #b26e52;
  --mars-sunset: #ff6b35;
  --mars-ochre: #d4893f;
  --accent-cyan: #00d4ff;
  --star-white: #e8e6e3;
  --cosmic-purple: #2a1542;
  --nebula-blue: #1a2744;
  --comet-tail: rgba(255, 107, 53, 0.3);
}
</style>

<style scoped>
.landing {
  position: relative;
  min-height: 100vh;
  overflow-x: hidden;
  background: var(--space-void, #05020e);
}
main {
  position: relative;
  z-index: 2;
}
</style>
