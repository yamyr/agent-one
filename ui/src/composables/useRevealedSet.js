import { computed, toValue } from 'vue'

/**
 * Shared composable that builds a Set of revealed tile keys ("x,y")
 * from the world state's agent data.
 *
 * @param {import('vue').MaybeRefOrGetter<Object|null>} worldState
 * @returns {{ revealedSet: import('vue').ComputedRef<Set<string>>, isRevealed: (x: number, y: number) => boolean, revealedCount: import('vue').ComputedRef<number> }}
 */
export function useRevealedSet(worldState) {
  const revealedSet = computed(() => {
    const set = new Set()
    const ws = toValue(worldState)
    if (!ws) return set
    for (const agent of Object.values(ws.agents || {})) {
      for (const cell of (agent.revealed || [])) {
        set.add(`${cell[0]},${cell[1]}`)
      }
    }
    return set
  })

  function isRevealed(x, y) {
    return revealedSet.value.has(`${x},${y}`)
  }

  const revealedCount = computed(() => revealedSet.value.size)

  return { revealedSet, isRevealed, revealedCount }
}
