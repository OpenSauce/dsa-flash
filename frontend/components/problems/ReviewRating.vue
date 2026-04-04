<script setup lang="ts">
const props = defineProps<{
  suggested: 'again' | 'good' | 'easy'
  hintsUsed: number
  rated?: boolean
  nextReviewDate?: string | null
}>()

const emit = defineEmits<{
  (e: 'rate', quality: number): void
  (e: 'next-problem'): void
}>()

const buttons = [
  { label: 'Again', quality: 1, interval: '~1d', ariaInterval: 'about 1 day', color: 'red' },
  { label: 'Good', quality: 3, interval: '~4d', ariaInterval: 'about 4 days', color: 'amber' },
  { label: 'Easy', quality: 5, interval: '~10d', ariaInterval: 'about 10 days', color: 'green' },
] as const

const qualityMap: Record<string, number> = { again: 1, good: 3, easy: 5 }

function isSuggested(quality: number): boolean {
  return quality === qualityMap[props.suggested]
}
</script>

<template>
  <div class="space-y-2">
    <!-- Post-rating state -->
    <div v-if="rated" class="text-center space-y-3">
      <p class="text-sm text-gray-600">
        <span v-if="nextReviewDate">Next review: <span class="font-semibold text-gray-800">{{ nextReviewDate }}</span></span>
        <span v-else>Scheduled for review</span>
      </p>
      <div class="flex justify-center gap-3">
        <button
          class="next-problem-btn min-h-[44px] px-4 py-2 text-sm font-semibold bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors"
          @click="emit('next-problem')"
        >
          Next problem
        </button>
        <NuxtLink
          to="/problems"
          class="min-h-[44px] inline-flex items-center px-4 py-2 text-sm font-semibold border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
        >
          Back to list
        </NuxtLink>
      </div>
    </div>

    <!-- Rating buttons -->
    <template v-else>
      <p class="text-xs text-gray-500 text-center">How was that?</p>
      <div class="flex justify-center gap-3">
        <button
          v-for="btn in buttons"
          :key="btn.quality"
          :aria-label="`Rate as ${btn.label}, review in ${btn.ariaInterval}`"
          class="min-h-[44px] px-4 py-2.5 rounded-lg text-sm font-semibold transition-all duration-150 border-2"
          :class="[
            btn.color === 'red'
              ? 'bg-red-50 border-red-200 text-red-700 hover:bg-red-100'
              : btn.color === 'amber'
              ? 'bg-amber-50 border-amber-200 text-amber-700 hover:bg-amber-100'
              : 'bg-green-50 border-green-200 text-green-700 hover:bg-green-100',
            isSuggested(btn.quality) && btn.color === 'red'
              ? 'ring-2 ring-red-400 ring-offset-1'
              : isSuggested(btn.quality) && btn.color === 'amber'
              ? 'ring-2 ring-amber-400 ring-offset-1'
              : isSuggested(btn.quality) && btn.color === 'green'
              ? 'ring-2 ring-green-400 ring-offset-1'
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
    </template>
  </div>
</template>
