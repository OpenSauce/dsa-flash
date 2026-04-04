<script setup lang="ts">
import { useAuth } from '@/composables/useAuth'
import { useApiFetch } from '@/composables/useApiFetch'

const props = defineProps<{
  lessonSlug: string
  initialRating: number | null
}>()

const { isLoggedIn } = useAuth()
const { apiFetch } = useApiFetch()

const currentRating = ref<number | null>(props.initialRating)
const showThanks = ref(props.initialRating !== null)

watch(() => props.lessonSlug, () => {
  currentRating.value = props.initialRating ?? null
  showThanks.value = props.initialRating !== null
})

const RATINGS = [
  { value: 3, label: 'Helpful', activeColor: '#16a34a' },
  { value: 2, label: 'Neutral', activeColor: '#9ca3af' },
  { value: 1, label: 'Not helpful', activeColor: '#dc2626' },
]

async function submitRating(rating: number) {
  currentRating.value = rating
  showThanks.value = true
  try {
    await apiFetch(`/lessons/${props.lessonSlug}/rate`, {
      method: 'POST',
      body: { rating },
    })
  } catch {
    // non-fatal: optimistic UI stays
  }
}
</script>

<template>
  <div v-if="isLoggedIn" class="flex items-center gap-3 py-4">
    <span class="text-sm text-gray-500">Was this helpful?</span>
    <div class="flex items-center gap-2">
      <template v-for="item in RATINGS" :key="item.value">
        <button
          v-if="currentRating === null || currentRating === item.value"
          type="button"
          :aria-label="item.label"
          :aria-pressed="currentRating === item.value"
          class="inline-flex items-center justify-center min-h-[44px] min-w-[44px] rounded-lg transition-colors hover:bg-gray-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-purple-600"
          @click="submitRating(item.value)"
        >
          <!-- Thumbs up (helpful, rating=3) -->
          <svg
            v-if="item.value === 3"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            class="w-5 h-5"
            :fill="currentRating === 3 ? item.activeColor : 'none'"
            :stroke="currentRating === 3 ? item.activeColor : '#9ca3af'"
            stroke-width="1.75"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M7 10v12" />
            <path d="M15 5.88L14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z" />
          </svg>

          <!-- Neutral (rating=2) — horizontal line / minus -->
          <svg
            v-else-if="item.value === 2"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            class="w-5 h-5"
            :fill="currentRating === 2 ? item.activeColor : 'none'"
            :stroke="currentRating === 2 ? item.activeColor : '#9ca3af'"
            stroke-width="1.75"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="8" y1="12" x2="16" y2="12" />
          </svg>

          <!-- Thumbs down (not helpful, rating=1) -->
          <svg
            v-else
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            class="w-5 h-5"
            :fill="currentRating === 1 ? item.activeColor : 'none'"
            :stroke="currentRating === 1 ? item.activeColor : '#9ca3af'"
            stroke-width="1.75"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M17 14V2" />
            <path d="M9 18.12L10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z" />
          </svg>
        </button>
      </template>
    </div>
    <span
      v-if="showThanks"
      class="text-sm text-gray-500"
      aria-live="polite"
    >Thanks!</span>
  </div>
</template>
