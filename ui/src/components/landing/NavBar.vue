<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { setLocale } from '../../i18n/index.js'

const { t, locale } = useI18n()

/* ─── Scroll state ─── */
const scrolled = ref(false)
function onScroll() {
  scrolled.value = window.scrollY > 50
}

/* ─── Active section tracking ─── */
const activeSection = ref('hero')
let observer = null

function setupObserver() {
  const sectionIds = ['hero', 'mission', 'agents', 'features', 'tech']
  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          activeSection.value = entry.target.id
        }
      })
    },
    { rootMargin: '-40% 0px -50% 0px', threshold: 0 }
  )
  sectionIds.forEach((id) => {
    const el = document.getElementById(id)
    if (el) observer.observe(el)
  })
}

/* ─── Locale switcher ─── */
const localeOpen = ref(false)
const localeRef = ref(null)

const locales = [
  { code: 'en', flag: '🇬🇧', name: 'English' },
  { code: 'de', flag: '🇩🇪', name: 'Deutsch' },
  { code: 'fr', flag: '🇫🇷', name: 'Français' },
  { code: 'es', flag: '🇪🇸', name: 'Español' },
  { code: 'zh', flag: '🇨🇳', name: '中文' },
  { code: 'ja', flag: '🇯🇵', name: '日本語' },
  { code: 'ko', flag: '🇰🇷', name: '한국어' },
  { code: 'ar', flag: '🇸🇦', name: 'العربية' },
  { code: 'ru', flag: '🇷🇺', name: 'Русский' },
  { code: 'pt', flag: '🇧🇷', name: 'Português' },
]

function toggleLocale() {
  localeOpen.value = !localeOpen.value
}

function switchLocale(code) {
  setLocale(code)
  localeOpen.value = false
}

function onClickOutside(e) {
  if (localeRef.value && !localeRef.value.contains(e.target)) {
    localeOpen.value = false
  }
}

/* ─── Mobile menu ─── */
const mobileOpen = ref(false)

function toggleMobile() {
  mobileOpen.value = !mobileOpen.value
}

function closeMobile() {
  mobileOpen.value = false
}

/* ─── Smooth scroll ─── */
function scrollTo(id) {
  const el = document.getElementById(id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth' })
  }
  closeMobile()
}

/* ─── Nav links ─── */
const navLinks = [
  { key: 'mission', section: 'mission' },
  { key: 'agents', section: 'agents' },
  { key: 'features', section: 'features' },
  { key: 'tech', section: 'tech' },
]

/* ─── Lifecycle ─── */
onMounted(() => {
  window.addEventListener('scroll', onScroll, { passive: true })
  document.addEventListener('click', onClickOutside)
  setupObserver()
  onScroll()
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
  document.removeEventListener('click', onClickOutside)
  if (observer) observer.disconnect()
})
</script>

<template>
  <nav
    class="navbar"
    :class="{ 'navbar--scrolled': scrolled }"
    role="navigation"
    :aria-label="t('nav.mission')"
  >
    <div class="navbar__inner">
      <!-- Logo -->
      <a class="navbar__brand" href="#hero" @click.prevent="scrollTo('hero')">
        <span class="navbar__mars-dot">●</span>
        <span class="navbar__brand-text">AGENT ONE</span>
      </a>

      <!-- Desktop links -->
      <div class="navbar__links">
        <a
          v-for="link in navLinks"
          :key="link.key"
          :href="'#' + link.section"
          class="navbar__link"
          :class="{ 'navbar__link--active': activeSection === link.section }"
          @click.prevent="scrollTo(link.section)"
        >
          {{ t('nav.' + link.key) }}
        </a>
      </div>

      <!-- Right actions -->
      <div class="navbar__actions">
        <!-- Locale switcher -->
        <div ref="localeRef" class="locale-switcher">
          <button
            class="locale-switcher__trigger"
            @click="toggleLocale"
            :aria-expanded="localeOpen"
            aria-haspopup="listbox"
          >
            {{ locale.toUpperCase() }}
          </button>
          <Transition name="dropdown">
            <div v-if="localeOpen" class="locale-switcher__dropdown" role="listbox">
              <button
                v-for="loc in locales"
                :key="loc.code"
                class="locale-switcher__option"
                :class="{ 'locale-switcher__option--active': locale === loc.code }"
                role="option"
                :aria-selected="locale === loc.code"
                @click="switchLocale(loc.code)"
              >
                <span class="locale-switcher__flag">{{ loc.flag }}</span>
                <span class="locale-switcher__name">{{ loc.name }}</span>
              </button>
            </div>
          </Transition>
        </div>

        <!-- Replay link -->
        <router-link to="/replay" class="navbar__replay">
          {{ t('nav.replay') }}
        </router-link>

        <!-- Launch CTA -->
        <router-link to="/app" class="navbar__cta">
          {{ t('nav.launch') }}
        </router-link>

        <!-- Hamburger -->
        <button
          class="navbar__hamburger"
          :class="{ 'navbar__hamburger--open': mobileOpen }"
          @click="toggleMobile"
          :aria-label="mobileOpen ? 'Close menu' : 'Open menu'"
          :aria-expanded="mobileOpen"
        >
          <span class="navbar__hamburger-line" />
          <span class="navbar__hamburger-line" />
          <span class="navbar__hamburger-line" />
        </button>
      </div>
    </div>

    <!-- Mobile overlay -->
    <Transition name="backdrop">
      <div
        v-if="mobileOpen"
        class="mobile-backdrop"
        @click="closeMobile"
      />
    </Transition>

    <!-- Mobile menu -->
    <Transition name="slide">
      <div v-if="mobileOpen" class="mobile-menu">
        <a
          v-for="link in navLinks"
          :key="link.key"
          :href="'#' + link.section"
          class="mobile-menu__link"
          :class="{ 'mobile-menu__link--active': activeSection === link.section }"
          @click.prevent="scrollTo(link.section)"
        >
          {{ t('nav.' + link.key) }}
        </a>

        <!-- Mobile locale switcher -->
        <div class="mobile-menu__locale">
          <button
            v-for="loc in locales"
            :key="loc.code"
            class="mobile-menu__locale-btn"
            :class="{ 'mobile-menu__locale-btn--active': locale === loc.code }"
            @click="switchLocale(loc.code)"
          >
            {{ loc.flag }} {{ loc.name }}
          </button>
        </div>

        <router-link to="/replay" class="navbar__replay navbar__replay--mobile" @click="closeMobile">
          {{ t('nav.replay') }}
        </router-link>

        <router-link to="/app" class="navbar__cta navbar__cta--mobile" @click="closeMobile">
          {{ t('nav.launch') }}
        </router-link>
      </div>
    </Transition>
  </nav>
</template>

<style scoped>
/* ─── Navbar Shell ─── */
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: rgba(5, 2, 14, 0.78);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--glass-border);
  transition: background 0.3s ease, border-color 0.3s ease;
}

.navbar--scrolled {
  background: rgba(5, 2, 14, 0.92);
  border-bottom-color: var(--glass-border-hover);
}

.navbar__inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 64px;
}

/* ─── Brand ─── */
.navbar__brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
  color: var(--text-primary);
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.08rem;
  letter-spacing: 0.08em;
  white-space: nowrap;
}

.navbar__mars-dot {
  color: var(--mars-sunset);
  font-size: 0.65rem;
  filter: drop-shadow(0 0 6px var(--mars-sunset));
  animation: pulse-dot 3s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 0.8; filter: drop-shadow(0 0 4px var(--mars-sunset)); }
  50% { opacity: 1; filter: drop-shadow(0 0 10px var(--mars-sunset)); }
}

.navbar__brand-text {
  background: linear-gradient(135deg, var(--text-primary) 40%, var(--mars-ochre));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* ─── Desktop Links ─── */
.navbar__links {
  display: flex;
  gap: 2rem;
}

.navbar__link {
  color: rgba(220, 224, 236, 0.86);
  text-decoration: none;
  font-size: 0.82rem;
  font-family: var(--font-mono);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 0.3rem 0;
  position: relative;
  transition: color 0.3s ease;
}

.navbar__link::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 0;
  height: 1px;
  background: var(--mars-sunset);
  transition: width 0.3s ease;
}

.navbar__link:hover {
  color: var(--mars-sunset);
}

.navbar__link:hover::after {
  width: 100%;
}

.navbar__link--active {
  color: var(--mars-sunset);
}

.navbar__link--active::after {
  width: 100%;
}

/* ─── Right Actions ─── */
.navbar__actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

/* ─── Locale Switcher ─── */
.locale-switcher {
  position: relative;
}

.locale-switcher__trigger {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  padding: 0.35rem 0.6rem;
  border-radius: 6px;
  cursor: pointer;
  transition: border-color 0.2s ease, color 0.2s ease, background 0.2s ease;
}

.locale-switcher__trigger:hover {
  border-color: var(--glass-border-hover);
  color: var(--text-primary);
  background: rgba(15, 15, 25, 0.8);
}

.locale-switcher__dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 180px;
  background: rgba(10, 10, 20, 0.95);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--glass-border);
  border-radius: 10px;
  padding: 0.4rem;
  display: flex;
  flex-direction: column;
  gap: 2px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.6);
}

.locale-switcher__option {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.5rem 0.7rem;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 0.78rem;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.15s ease, color 0.15s ease;
}

.locale-switcher__option:hover {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-primary);
}

.locale-switcher__option--active {
  background: rgba(255, 107, 53, 0.1);
  color: var(--mars-sunset);
}

.locale-switcher__flag {
  font-size: 1rem;
  line-height: 1;
}

.locale-switcher__name {
  flex: 1;
}

/* ─── Replay Link ─── */
.navbar__replay {
  display: inline-flex;
  align-items: center;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  text-decoration: none;
  padding: 0.5rem 1rem;
  border: 1px solid var(--glass-border);
  border-radius: 6px;
  transition: border-color 0.3s ease, color 0.3s ease;
}

.navbar__replay:hover {
  border-color: var(--mars-ochre);
  color: var(--mars-ochre);
}

.navbar__replay--mobile {
  width: 100%;
  justify-content: center;
  padding: 0.7rem 1.5rem;
  font-size: 0.85rem;
}

/* ─── Launch CTA ─── */
.navbar__cta {
  display: inline-flex;
  align-items: center;
  background: linear-gradient(135deg, var(--mars-sunset), var(--mars-red));
  color: #fff;
  font-family: var(--font-mono);
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  text-decoration: none;
  padding: 0.5rem 1.2rem;
  border-radius: 6px;
  transition: filter 0.3s ease, transform 0.2s ease, box-shadow 0.3s ease;
}

.navbar__cta:hover {
  filter: brightness(1.15);
  transform: translateY(-1px);
  box-shadow: 0 4px 20px rgba(255, 107, 53, 0.3);
}

.navbar__cta--mobile {
  width: 100%;
  justify-content: center;
  padding: 0.8rem 1.5rem;
  margin-top: 1rem;
  font-size: 0.85rem;
}

/* ─── Hamburger ─── */
.navbar__hamburger {
  display: none;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  width: 32px;
  height: 32px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
}

.navbar__hamburger-line {
  display: block;
  width: 100%;
  height: 1.5px;
  background: var(--text-secondary);
  border-radius: 2px;
  transition: transform 0.3s ease, opacity 0.2s ease, background 0.2s ease;
  transform-origin: center;
}

.navbar__hamburger--open .navbar__hamburger-line:nth-child(1) {
  transform: translateY(6.5px) rotate(45deg);
  background: var(--mars-sunset);
}

.navbar__hamburger--open .navbar__hamburger-line:nth-child(2) {
  opacity: 0;
}

.navbar__hamburger--open .navbar__hamburger-line:nth-child(3) {
  transform: translateY(-6.5px) rotate(-45deg);
  background: var(--mars-sunset);
}

/* ─── Mobile Backdrop ─── */
.mobile-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 98;
}

/* ─── Mobile Menu ─── */
.mobile-menu {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: min(320px, 85vw);
  z-index: 99;
  background: rgba(8, 5, 18, 0.97);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border-left: 1px solid var(--glass-border);
  padding: 80px 2rem 2rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  overflow-y: auto;
}

.mobile-menu__link {
  display: block;
  padding: 0.8rem 0.5rem;
  color: var(--text-secondary);
  text-decoration: none;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border-bottom: 1px solid var(--glass-border);
  transition: color 0.2s ease, padding-left 0.2s ease;
}

.mobile-menu__link:hover,
.mobile-menu__link--active {
  color: var(--mars-sunset);
  padding-left: 1rem;
}

.mobile-menu__locale {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  padding: 1rem 0;
  border-bottom: 1px solid var(--glass-border);
}

.mobile-menu__locale-btn {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  padding: 0.35rem 0.6rem;
  border-radius: 6px;
  cursor: pointer;
  transition: border-color 0.2s ease, color 0.2s ease;
}

.mobile-menu__locale-btn:hover {
  border-color: var(--glass-border-hover);
  color: var(--text-primary);
}

.mobile-menu__locale-btn--active {
  border-color: var(--mars-sunset);
  color: var(--mars-sunset);
  background: rgba(255, 107, 53, 0.08);
}

/* ─── Dropdown Transition ─── */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.96);
}

/* ─── Backdrop Transition ─── */
.backdrop-enter-active,
.backdrop-leave-active {
  transition: opacity 0.3s ease;
}

.backdrop-enter-from,
.backdrop-leave-to {
  opacity: 0;
}

/* ─── Slide Transition ─── */
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}

/* ─── Responsive ─── */
@media (max-width: 768px) {
  .navbar__links {
    display: none;
  }

  .navbar__cta:not(.navbar__cta--mobile) {
    display: none;
  }

  .locale-switcher {
    display: none;
  }

  .navbar__hamburger {
    display: flex;
  }

  .navbar__inner {
    padding: 0 1.2rem;
    height: 56px;
  }
}

/* ─── Accessibility ─── */
@media (prefers-reduced-motion: reduce) {
  .navbar,
  .navbar__link::after,
  .navbar__cta,
  .navbar__hamburger-line,
  .locale-switcher__trigger,
  .locale-switcher__option {
    transition: none !important;
  }

  .navbar__mars-dot {
    animation: none !important;
  }
}
</style>
