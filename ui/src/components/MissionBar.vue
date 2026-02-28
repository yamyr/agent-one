<script setup>
import { computed } from 'vue'
import { useI18n } from '../composables/useI18n.js'

const props = defineProps({ mission: { type: Object, default: null } })
const emit = defineEmits(['abort'])
const { t } = useI18n()

const collected = computed(() => props.mission ? (props.mission.collected_quantity || props.mission.collected_count || 0) : 0)
const target = computed(() => props.mission ? (props.mission.target_quantity || props.mission.target_count || 1) : 1)
const progressPct = computed(() => Math.min(100, Math.round((collected.value / target.value) * 100)))
</script>

<template>
  <div
    v-if="mission"
    class="mission-bar"
  >
    <span class="mission-label">{{ t('mission.label') }}</span>
    <span class="mission-target">{{ t('mission.collect', { target }) }}</span>
    <span class="mission-progress-wrap"><span class="progress-track"><span
      class="progress-fill"
      :style="{ width: progressPct + '%' }"
    /></span><span class="mission-progress">{{ collected }} / {{ target }}</span></span>
    <span
      v-if="mission.in_transit_quantity"
      class="mission-transit"
    >{{ t('mission.in_transit', { count: mission.in_transit_quantity }) }}</span>
    <span
      class="mission-status"
      :class="mission.status"
    >{{ mission.status }}</span>
    <button
      v-if="mission.status === 'running'"
      class="abort-btn"
      @click="emit('abort')"
    >
      {{ t('mission.abort') }}
    </button>
  </div>
</template>

<style scoped>
.mission-bar{display:flex;align-items:center;gap:.75rem;padding:.4rem .75rem;margin-bottom:.5rem;border:1px solid var(--border-subtle);border-radius:var(--radius-md);background:var(--bg-card);font-size:.75rem}.mission-label{color:var(--text-muted);text-transform:uppercase;letter-spacing:.08em;font-size:.65rem}.mission-target{color:var(--accent-amber-dark)}.mission-progress-wrap{display:inline-flex;align-items:center;gap:.35rem}.progress-track{display:inline-block;width:4rem;height:.45rem;border-radius:var(--radius-sm);background:var(--bg-elevated);border:1px solid var(--border-subtle);overflow:hidden}.progress-fill{display:block;height:100%;border-radius:var(--radius-sm);background:var(--accent-amber);transition:width .3s ease}.mission-progress{color:var(--text-primary);font-weight:bold}.mission-transit{color:#c9a227;font-size:.7rem}.mission-status{margin-left:auto;padding:.15rem .4rem;border-radius:var(--radius-sm);font-size:.7rem;text-transform:uppercase;letter-spacing:.05em}.mission-status.running{background:var(--bg-status-info);color:var(--accent-blue)}.mission-status.success{background:var(--bg-status-ok);color:var(--accent-green)}.mission-status.failed,.mission-status.aborted{background:var(--bg-status-error);color:var(--accent-red)}.abort-btn{font-family:var(--font-mono);font-size:.65rem;padding:.15rem .5rem;border-radius:var(--radius-sm);border:1px solid var(--text-muted);background:var(--bg-input);color:var(--accent-red);cursor:pointer;margin-left:.25rem}
</style>
