import { ref, onMounted, onUnmounted } from 'vue'

/**
 * Composable for scroll-triggered reveal animations.
 * Returns a template ref and a reactive visibility flag.
 * Once the element scrolls into view, visible becomes true (one-shot).
 */
export function useRevealOnScroll(options = {}) {
  const { threshold = 0.15, rootMargin = '0px' } = options
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
      { threshold, rootMargin },
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

  return { sectionRef, visible }
}
