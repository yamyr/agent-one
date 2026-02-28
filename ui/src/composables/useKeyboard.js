import { onMounted, onUnmounted } from 'vue'

/**
 * Global keyboard shortcuts for the simulation UI.
 *
 * @param {Object} opts
 * @param {Function} opts.onTogglePause    — Space key
 * @param {Function} opts.onPanCamera      — Arrow / WASD keys → (dx, dy)
 * @param {Function} opts.onFollowAgent    — 1-9 digit keys → index (0-based)
 * @param {Function} opts.onFreeCamera     — 0 key
 * @param {Function} opts.onCloseModal     — Escape key
 * @param {Function} opts.onToggleHelp     — ? key
 */
export function useKeyboard({ onTogglePause, onPanCamera, onFollowAgent, onFreeCamera, onCloseModal, onToggleHelp } = {}) {
  function handler(e) {
    // Skip if user is typing in an input / textarea / contenteditable
    const tag = e.target.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || e.target.isContentEditable) return

    if (e.key === '?' || (e.shiftKey && e.key === '/')) {
      e.preventDefault()
      onToggleHelp?.()
      return
    }

    switch (e.code) {
      case 'Space':
        e.preventDefault()
        onTogglePause?.()
        break
      case 'Escape':
        onCloseModal?.()
        break

      // Camera panning — Arrow keys & WASD
      case 'ArrowLeft':
      case 'KeyA':
        e.preventDefault()
        onPanCamera?.(-1, 0)
        break
      case 'ArrowRight':
      case 'KeyD':
        e.preventDefault()
        onPanCamera?.(1, 0)
        break
      case 'ArrowUp':
      case 'KeyW':
        e.preventDefault()
        onPanCamera?.(0, 1)
        break
      case 'ArrowDown':
      case 'KeyS':
        e.preventDefault()
        onPanCamera?.(0, -1)
        break

      // Agent follow — digit keys 1-9, 0 = free
      case 'Digit0':
        onFreeCamera?.()
        break
      case 'Digit1':
      case 'Digit2':
      case 'Digit3':
      case 'Digit4':
      case 'Digit5':
      case 'Digit6':
      case 'Digit7':
      case 'Digit8':
      case 'Digit9':
        onFollowAgent?.(parseInt(e.code.slice(-1), 10) - 1)
        break
      default:
        break
    }
  }

  onMounted(() => window.addEventListener('keydown', handler))
  onUnmounted(() => window.removeEventListener('keydown', handler))
}
