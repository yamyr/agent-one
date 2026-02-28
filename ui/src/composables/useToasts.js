import { ref } from 'vue'

let toastId = 0

/**
 * Lightweight toast notification system.
 * Toasts auto-dismiss after a configurable duration.
 */
export function useToasts() {
  const toasts = ref([])

  function addToast(message, { type = 'info', duration = 4000 } = {}) {
    const id = ++toastId
    toasts.value.push({ id, message, type })
    setTimeout(() => {
      toasts.value = toasts.value.filter(t => t.id !== id)
    }, duration)
  }

  function dismiss(id) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  return { toasts, addToast, dismiss }
}
