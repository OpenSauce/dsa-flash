<script setup lang="ts">
const props = defineProps<{
  suggested: 'again' | 'good' | 'easy'
  hintsUsed: number
}>()

const emit = defineEmits<{
  (e: 'rate', quality: number): void
}>()

const buttons = [
  { label: 'Again', quality: 1, interval: '~1d', color: 'red' },
  { label: 'Good', quality: 3, interval: '~4d', color: 'amber' },
  { label: 'Easy', quality: 5, interval: '~10d', color: 'purple' },
] as const

const qualityMap: Record<string, number> = { again: 1, good: 3, easy: 5 }

function isSuggested(quality: number): boolean {
  return quality === qualityMap[props.suggested]
}
</script>

<template>
  <div class="space-y-2">
    <p class="text-xs text-gray-500 text-center">How was that?</p>
    <div class="flex justify-center gap-3">
      <button
        v-for="btn in buttons"
        :key="btn.quality"
        class="px-4 py-2.5 rounded-lg text-sm font-semibold transition-all duration-150 border-2"
        :class="[
          btn.color === 'red'
            ? 'bg-red-50 border-red-200 text-red-700 hover:bg-red-100'
            : btn.color === 'amber'
            ? 'bg-amber-50 border-amber-200 text-amber-700 hover:bg-amber-100'
            : 'bg-purple-50 border-purple-200 text-purple-700 hover:bg-purple-100',
          isSuggested(btn.quality) && btn.color === 'red'
            ? 'ring-2 ring-red-400 ring-offset-1'
            : isSuggested(btn.quality) && btn.color === 'amber'
            ? 'ring-2 ring-amber-400 ring-offset-1'
            : isSuggested(btn.quality) && btn.color === 'purple'
            ? 'ring-2 ring-purple-400 ring-offset-1'
            : '',
        ]"
        @click="emit('rate', btn.quality)"
      >
        <span class="block">{{ btn.label }}</span>
        <span class="block text-[10px] font-normal opacity-70 mt-0.5">{{ btn.interval }}</span>
      </button>
    </div>
    <p v-if="hintsUsed > 0" class="text-[10px] text-gray-400 text-center">
      {{ hintsUsed }} hint{{ hintsUsed > 1 ? 's' : '' }} used
    </p>
  </div>
</template>
