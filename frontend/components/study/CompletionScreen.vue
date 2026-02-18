<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  categoryName: string
  cardsReviewed: number
  newConcepts: number
  reviewedConcepts: number
  runningTotal: number | null
  categoryTotal: number
  remainingCards: number
  hasMoreCards: boolean
  isLoggedIn: boolean
}>()

defineEmits<{
  (e: 'keep-going'): void
}>()

const HEADINGS = [
  'Nice work!',
  'Knowledge growing!',
  'Session complete!',
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

const heading = computed(() => HEADINGS[HEADING_INDEX])

const encouragement = computed(() => {
  const pct = props.categoryTotal > 0 && props.runningTotal !== null
    ? Math.min(100, Math.max(0, Math.round((props.runningTotal / props.categoryTotal) * 100)))
    : 0
  return ENCOURAGEMENT_TEMPLATES[ENCOURAGEMENT_INDEX](props.categoryName, pct)
})
</script>

<template>
  <div class="text-center py-16">
    <template v-if="cardsReviewed > 0">
      <h2 class="text-2xl font-bold mb-3 font-heading">{{ heading }}</h2>

      <p class="text-lg text-gray-700 mb-2">
        You studied <span class="font-semibold">{{ cardsReviewed }}</span> {{ categoryName }} concepts.
      </p>

      <p v-if="isLoggedIn && (newConcepts > 0 || reviewedConcepts > 0)" class="text-gray-600 mb-2">
        <span class="font-medium text-indigo-600">{{ newConcepts }}</span> new
        &nbsp;&middot;&nbsp;
        <span class="font-medium">{{ reviewedConcepts }}</span> reviewed
      </p>

      <p v-if="isLoggedIn && runningTotal !== null" class="text-gray-600 mb-4">
        You now know
        <span class="font-semibold">{{ runningTotal }}</span>
        of {{ categoryTotal }} {{ categoryName }} concepts.
      </p>

      <p v-if="isLoggedIn" class="text-gray-500 text-sm italic mb-6">{{ encouragement }}</p>

      <p v-if="!isLoggedIn" class="text-gray-500 text-sm mb-6">
        Sign up to track your progress and unlock spaced repetition.
      </p>

      <div class="flex flex-wrap justify-center gap-4">
        <button v-if="hasMoreCards" @click="$emit('keep-going')"
                class="px-6 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700">
          Keep going
        </button>
        <NuxtLink to="/" class="px-6 py-2 border border-gray-300 rounded hover:bg-gray-50">
          Try another domain
        </NuxtLink>
        <NuxtLink v-if="isLoggedIn" to="/dashboard"
                  class="px-6 py-2 border border-gray-300 rounded hover:bg-gray-50">
          Back to dashboard
        </NuxtLink>
      </div>
    </template>

    <template v-else>
      <p class="text-gray-500 mb-4">No concepts due right now.</p>
      <div class="flex flex-wrap justify-center gap-4">
        <NuxtLink to="/" class="text-blue-600 hover:underline">
          Try another domain
        </NuxtLink>
        <NuxtLink v-if="isLoggedIn" to="/dashboard" class="text-blue-600 hover:underline">
          Back to dashboard
        </NuxtLink>
      </div>
    </template>
  </div>
</template>
