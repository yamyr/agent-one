import { ref } from 'vue'

let toastId = 0

const MAX_VISIBLE = 5
const DEDUP_WINDOW = 5000

/**
 * Lightweight toast notification system.
 * Deduplicates identical messages within a 5s window (with count badge).
 * Rate-limits to MAX_VISIBLE toasts; oldest evicted when full.
 */
export function useToasts() {
  const toasts = ref([])

  function addToast(message, { type = 'info', duration = 4000 } = {}) {
    const now = Date.now()

    // Deduplicate: bump count if same message+type within window
    const existing = toasts.value.find(
      t => t.message === message && t.type === type && (now - t.createdAt) < DEDUP_WINDOW
    )
    if (existing) {
      existing.count = (existing.count || 1) + 1
      existing.createdAt = now
      if (existing.timerId) clearTimeout(existing.timerId)
      existing.timerId = setTimeout(() => {
        toasts.value = toasts.value.filter(t => t.id !== existing.id)
      }, duration)
      return
    }

    // Rate-limit: evict oldest when at capacity
    if (toasts.value.length >= MAX_VISIBLE) {
      const oldest = toasts.value[toasts.value.length - 1]
      if (oldest.timerId) clearTimeout(oldest.timerId)
      toasts.value.pop()
    }

    const id = ++toastId
    const timerId = setTimeout(() => {
      toasts.value = toasts.value.filter(t => t.id !== id)
    }, duration)
    toasts.value.unshift({ id, message, type, count: 1, createdAt: now, timerId })
  }

  function dismiss(id) {
    const toast = toasts.value.find(t => t.id === id)
    if (toast?.timerId) clearTimeout(toast.timerId)
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  return { toasts, addToast, dismiss }
}
