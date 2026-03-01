import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

export function useScrollAnimation() {
  const triggers = []

  function animateOnScroll(element, options = {}) {
    const {
      y = 60,
      opacity = 0,
      duration = 0.8,
      ease = 'power2.out',
      start = 'top 85%',
    } = options

    const tween = gsap.from(element, {
      y,
      opacity,
      duration,
      ease,
      scrollTrigger: {
        trigger: element,
        start,
      },
    })

    triggers.push(tween.scrollTrigger)
    return tween
  }

  function cleanup() {
    triggers.forEach((st) => st?.kill())
    triggers.length = 0
  }

  return { animateOnScroll, cleanup }
}
