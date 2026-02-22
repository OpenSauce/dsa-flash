<script setup lang="ts">
import { computed } from 'vue'
import type { StudyMode } from '@/composables/useStudySession'

const props = defineProps<{
  categoryName: string
  categoryEmoji: string
  cardsReviewed: number
  newConcepts: number
  reviewedConcepts: number
  runningTotal: number | null
  categoryTotal: number
  remainingCards: number
  hasMoreCards: boolean
  isLoggedIn: boolean
  mode: StudyMode
}>()

defineEmits<{
  (e: 'keep-going'): void
}>()

const HEADINGS = [
  'Nice work!',
  'Knowledge growing!',
  'Well done!',
  'Keep it up!',
]

const ENCOURAGEMENT_TEMPLATES = [
  (name: string, _pct: number) => `Your ${name} knowledge is growing`,
  (_name: string, pct: number) => `You've covered ${pct}% of this domain`,
  () => 'Come back tomorrow to keep your streak',
  () => 'Spaced repetition makes this stick',
  () => 'Each session builds lasting knowledge',
]

const HEADING_INDEX = Math.floor(Math.random() * HEADINGS.length)
const ENCOURAGEMENT_INDEX = Math.floor(Math.random() * ENCOURAGEMENT_TEMPLATES.length)

const categoryComplete = computed(() =>
  props.isLoggedIn && props.runningTotal !== null && props.categoryTotal > 0 && props.runningTotal >= props.categoryTotal
)

const heading = computed(() => {
  if (categoryComplete.value) return `${props.categoryName} complete!`
  return HEADINGS[HEADING_INDEX]
})

const encouragement = computed(() => {
  if (categoryComplete.value) return 'Come back to review when cards are due — spaced repetition will keep it fresh.'
  const pct = props.categoryTotal > 0 && props.runningTotal !== null
    ? Math.min(100, Math.max(0, Math.round((props.runningTotal / props.categoryTotal) * 100)))
    : 0
  return ENCOURAGEMENT_TEMPLATES[ENCOURAGEMENT_INDEX](props.categoryName, pct)
})
</script>

<template>
  <div class="text-center py-8 sm:py-16">
    <template v-if="cardsReviewed > 0">
      <!-- Category complete celebration -->
      <template v-if="categoryComplete">
        <div class="text-5xl mb-3">{{ categoryEmoji }}</div>
        <h2 class="text-2xl font-bold mb-2">{{ heading }}</h2>
        <p class="text-lg text-gray-700 mb-1">
          You've learned all <span class="font-semibold">{{ categoryTotal }}</span> {{ categoryName }} concepts.
        </p>
        <div class="inline-flex items-center gap-2 bg-green-50 border border-green-200 rounded-full px-4 py-1.5 mt-2 mb-4">
          <svg class="w-5 h-5 text-green-600" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
          </svg>
          <span class="text-sm font-medium text-green-700">{{ categoryTotal }} / {{ categoryTotal }} learned</span>
        </div>
        <p class="text-gray-500 text-sm italic mb-6">{{ encouragement }}</p>
      </template>

      <!-- Normal session complete -->
      <template v-else>
        <div class="text-4xl mb-2">{{ categoryEmoji }}</div>
        <h2 class="text-2xl font-bold mb-3">{{ heading }}</h2>

        <p class="text-lg text-gray-700 mb-2">
          You reviewed <span class="font-semibold">{{ cardsReviewed }}</span> {{ categoryName }} concepts.
        </p>

        <p v-if="isLoggedIn && mode === 'due'" class="text-gray-600 mb-4">
          <span class="font-semibold">{{ cardsReviewed }}</span>
          {{ cardsReviewed === 1 ? 'concept' : 'concepts' }} reinforced — keeping your {{ categoryName }} knowledge fresh.
        </p>

        <p v-if="isLoggedIn" class="text-gray-500 text-sm italic mb-6">{{ encouragement }}</p>

        <p v-if="!isLoggedIn" class="text-gray-500 text-sm mb-6">
          Sign up to track your progress and unlock spaced repetition.
        </p>
      </template>

      <div class="flex flex-wrap justify-center gap-4">
        <button v-if="hasMoreCards" @click="$emit('keep-going')"
                class="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          Keep going
        </button>
        <NuxtLink to="/" class="px-6 py-2 border border-gray-300 rounded hover:bg-gray-50">
          Try another domain
        </NuxtLink>
      </div>
    </template>

    <template v-else>
      <div class="text-4xl mb-2">{{ categoryEmoji }}</div>
      <p class="text-gray-500 mb-4">No concepts due right now.</p>
      <div class="flex flex-wrap justify-center gap-4">
        <NuxtLink to="/" class="text-blue-600 hover:underline">
          Try another domain
        </NuxtLink>
      </div>
    </template>
  </div>
</template>
