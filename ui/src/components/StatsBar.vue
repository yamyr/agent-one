<script setup>
import { computed } from 'vue'
import { useI18n } from '../composables/useI18n.js'
const props = defineProps({ worldState:{type:Object,default:null}, agentIds:{type:Array,default:()=>[]}, eventCount:{type:Number,default:0} })
const { t } = useI18n()
const tick = computed(() => props.worldState?.tick ?? 0)
const tilesRevealed = computed(() => { if(!props.worldState) return 0; const set=new Set(); for (const agent of Object.values(props.worldState.agents||{})) for (const c of (agent.revealed||[])) set.add(`${c[0]},${c[1]}`); return set.size })
const mobileCount = computed(() => !props.worldState ? 0 : Object.values(props.worldState.agents||{}).filter(a=>a.type!=='station').length)
const totalStones = computed(() => (props.worldState?.stones||[]).length)
const collectedQty = computed(() => props.worldState?.mission ? (props.worldState.mission.collected_quantity || props.worldState.mission.collected_count || 0) : 0)
const targetQty = computed(() => props.worldState?.mission ? (props.worldState.mission.target_quantity || props.worldState.mission.target_count || 0) : 0)
</script>
<template>
  <div class="stats-bar">
    <template v-if="worldState">
      <span class="stat"><span class="stat-label">{{ t('stats.tick') }}</span><span class="stat-value">#{{ tick }}</span></span><span class="stat-sep" />
      <span class="stat"><span class="stat-label">{{ t('stats.revealed') }}</span><span class="stat-value">{{ tilesRevealed }} {{ t('stats.tiles') }}</span></span><span class="stat-sep" />
      <span class="stat"><span class="stat-label">{{ t('stats.agents') }}</span><span class="stat-value">{{ mobileCount }}</span></span><span class="stat-sep" />
      <span class="stat"><span class="stat-label">{{ t('stats.veins') }}</span><span class="stat-value">{{ totalStones }}</span></span><span class="stat-sep" />
      <span class="stat"><span class="stat-label">{{ t('stats.collected') }}</span><span class="stat-value collected">{{ collectedQty }}<template v-if="targetQty"> / {{ targetQty }}</template></span></span><span class="stat-sep" />
      <span class="stat"><span class="stat-label">{{ t('stats.events') }}</span><span class="stat-value">{{ eventCount }}</span></span>
    </template>
    <div
      v-else
      class="skeleton-stats"
    >
      <div
        v-for="i in 6"
        :key="i"
        class="skeleton-item"
      />
    </div>
  </div>
</template>
<style scoped>
.stats-bar{display:flex;align-items:center;gap:.5rem;padding:.3rem .75rem;margin-bottom:.5rem;border:1px solid var(--border-dim);border-radius:var(--radius-md);background:var(--bg-primary);font-size:.65rem;flex-wrap:wrap}.stat{display:inline-flex;align-items:center;gap:.3rem}.stat-label{color:var(--text-dim);text-transform:uppercase;letter-spacing:.06em}.stat-value{color:var(--text-secondary);font-weight:bold}.stat-value.collected{color:var(--accent-green-soft)}.stat-sep{width:1px;height:.65rem;background:var(--border-medium)}
</style>
