<script setup lang="ts">
import { ref, computed } from 'vue'
import { LEARNED_HEX, LEARNED_TEXT_HEX, MASTERED_HEX } from '@/composables/useMasteryColors'

const props = withDefaults(defineProps<{
  learnedPct: number
  masteredPct: number
  size?: string
}>(), {
  size: 'w-14 h-14',
})

const INNER_CIRC = 75.398

const clampedMastered = computed(() => Math.min(props.masteredPct, props.learnedPct))
const innerOffset = computed(() => INNER_CIRC - (clampedMastered.value / 100) * INNER_CIRC)
const outerOffset = computed(() => 100 - props.learnedPct)

const hovered = ref(false)

const showingMastery = computed(() => hovered.value && clampedMastered.value < 100)

const centerText = computed(() => {
  if (clampedMastered.value === 100) return null
  if (showingMastery.value) return `${clampedMastered.value}%`
  return `${props.learnedPct}%`
})

const centerFill = computed(() => showingMastery.value ? MASTERED_HEX : LEARNED_TEXT_HEX)

const ariaLabel = computed(() => {
  if (clampedMastered.value === 100) return '100% mastered'
  return `${props.learnedPct}% learned, ${clampedMastered.value}% mastered`
})
</script>

<template>
  <svg
    viewBox="0 0 36 36"
    :class="size"
    :aria-label="ariaLabel"
    role="img"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <!-- Outer track (learned background) -->
    <circle cx="18" cy="18" r="15.9155" fill="none" stroke="#e5e7eb" stroke-width="2.5" />
    <!-- Outer arc (learned, green) -->
    <circle
      cx="18" cy="18" r="15.9155" fill="none"
      :stroke="LEARNED_HEX"
      stroke-width="2.5"
      stroke-dasharray="100"
      :stroke-dashoffset="outerOffset"
      stroke-linecap="round"
      transform="rotate(-90 18 18)"
    />
    <!-- Inner track (mastered background) -->
    <circle cx="18" cy="18" r="12" fill="none" stroke="#e5e7eb" stroke-width="2.5" />
    <!-- Inner arc (mastered, blue) -->
    <circle
      cx="18" cy="18" r="12" fill="none"
      :stroke="MASTERED_HEX"
      stroke-width="2.5"
      :stroke-dasharray="INNER_CIRC"
      :stroke-dashoffset="innerOffset"
      stroke-linecap="round"
      transform="rotate(-90 18 18)"
    />
    <!-- Center: blue checkmark when 100% mastered -->
    <text v-if="clampedMastered === 100" x="18" y="22" text-anchor="middle" font-size="12" :fill="MASTERED_HEX">&#10003;</text>
    <!-- Center: percentage text otherwise -->
    <text v-else x="18" y="21" text-anchor="middle" font-size="8" :fill="centerFill" font-weight="600">
      {{ centerText }}
    </text>
  </svg>
</template>
