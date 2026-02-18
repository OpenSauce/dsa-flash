<script setup lang="ts">
import { useAnalytics } from '@/composables/useAnalytics'

const route = useRoute()
const category = route.params.slug as string
const apiBase = useRuntimeConfig().public.apiBase
const { isLoggedIn, tokenCookie, logout } = useAuth()
const { refreshStreak } = useStreak()
const { track, flushBeacon } = useAnalytics()

const {
  card, error,
  sessionFinished, cardsReviewedInBatch, cardsReviewedInSession,
  currentBatchSize, remainingCards, hasMoreCards, progressPercent,
  revealed, buttonsEnabled,
  flipCard, nextCard, recordResponse, keepGoing, finishSession,
} = await useStudySession({
  category, apiBase, isLoggedIn, tokenCookie,
  track, flushBeacon, refreshStreak, logout,
})
</script>

<template>
  <div class="max-w-4xl mx-auto p-6">
    <button v-if="card" @click="finishSession('user_ended')"
            class="text-blue-600 hover:underline mb-4 inline-block">
      Stop reviewing
    </button>

    <div v-if="error" class="text-red-500">
      {{ error.data?.detail || error }}
    </div>

    <StudyCompletionScreen
      v-else-if="sessionFinished || !card"
      :cards-reviewed="cardsReviewedInSession"
      :remaining-cards="remainingCards"
      :has-more-cards="hasMoreCards"
      :is-logged-in="isLoggedIn"
      @keep-going="keepGoing"
    />

    <div v-else>
      <div v-if="!isLoggedIn"
           class="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
        Your progress won't be saved.
        <NuxtLink to="/signup" class="underline font-medium">Sign up</NuxtLink> to track your learning.
      </div>

      <StudyProgressBar
        :current="cardsReviewedInBatch"
        :total="currentBatchSize"
        :percent="progressPercent"
      />

      <StudyCard
        :front="card.front"
        :back="card.back"
        :revealed="revealed"
        @flip="flipCard"
      />

      <StudyReviewButtons
        :revealed="revealed"
        :is-logged-in="isLoggedIn"
        :buttons-enabled="buttonsEnabled"
        @rate="recordResponse"
        @next="nextCard"
      />
    </div>
  </div>
</template>
