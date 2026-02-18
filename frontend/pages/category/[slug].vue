<script setup lang="ts">
import { useAnalytics } from '@/composables/useAnalytics'
import { CATEGORY_META, DEFAULT_META } from '@/utils/categoryMeta'
import type { StudyMode } from '@/composables/useStudySession'

const route = useRoute()
const category = route.params.slug as string
const categoryEmoji = (CATEGORY_META[category] || DEFAULT_META).emoji
const apiBase = useRuntimeConfig().public.apiBase
const { isLoggedIn, authReady, tokenCookie, logout } = useAuth()
const { refreshStreak } = useStreak()
const { track, flushBeacon } = useAnalytics()

// Mode selector state (shown before session starts for logged-in users)
const mode = ref<StudyMode>('all')
const sessionStarted = ref(false)

interface StatsData {
  due: number
  new: number
}
const stats = ref<StatsData>({ due: 0, new: 0 })

const fetchStats = async () => {
  try {
    const data = await $fetch<StatsData>(
      `${apiBase}/flashcards/stats?category=${category}`,
      { headers: tokenCookie.value ? { Authorization: `Bearer ${tokenCookie.value}` } : {} }
    )
    stats.value = data
  } catch {
    // fallback: skip selector, start with mode=all
    sessionStarted.value = true
  }
}

watch(
  [authReady, isLoggedIn],
  async ([ready, loggedIn]) => {
    if (!ready) return
    if (!loggedIn) {
      sessionStarted.value = true
      return
    }
    await fetchStats()
  },
  { immediate: true }
)

const {
  card, pending, error,
  sessionFinished, cardsReviewedInBatch, cardsReviewedInSession,
  currentBatchSize, remainingCards, hasMoreCards, progressPercent,
  revealed, buttonsEnabled,
  categoryDisplayName, categoryLearnedCount, categoryTotal,
  newConceptsInSession, reviewedConceptsInSession,
  flipCard, nextCard, recordResponse, keepGoing, finishSession,
} = await useStudySession({
  category, apiBase, isLoggedIn, tokenCookie,
  track, flushBeacon, refreshStreak, logout,
  mode,
})

async function startSession(selectedMode: StudyMode) {
  mode.value = selectedMode
  // Wait for the refetch triggered by mode change to complete before
  // showing the study UI, so no stale card flashes during transition.
  // Use nextTick first to ensure the reactive URL change has propagated
  // and useFetch has initiated the refetch (pending flips to true).
  await nextTick()
  if (pending.value) {
    await new Promise<void>((resolve) => {
      const stop = watch(pending, (isPending) => {
        if (!isPending) {
          stop()
          resolve()
        }
      })
    })
  }
  sessionStarted.value = true
}
</script>

<template>
  <div class="max-w-4xl mx-auto p-6">

    <!-- Mode selector (logged-in users only, before session starts) -->
    <div v-if="!sessionStarted && isLoggedIn" class="text-center py-16">
      <div class="text-4xl mb-2">{{ categoryEmoji }}</div>
      <h2 class="text-2xl font-bold mb-6">{{ categoryDisplayName }}</h2>

      <div v-if="stats.due === 0 && stats.new === 0" class="text-gray-500">
        <p class="mb-4">No cards due and no new cards. Come back tomorrow!</p>
        <NuxtLink to="/" class="text-blue-600 hover:underline">&larr; Back to categories</NuxtLink>
      </div>

      <div v-else class="flex flex-col gap-3 max-w-sm mx-auto">
        <button v-if="stats.due > 0" @click="startSession('due')"
                class="flex items-center gap-4 px-6 py-4 border-2 border-indigo-600 rounded-xl text-left hover:bg-indigo-50 transition">
          <span class="text-2xl flex-shrink-0">💧</span>
          <div>
            <span class="block font-semibold text-indigo-700">Review due ({{ stats.due }})</span>
            <span class="block text-sm text-gray-500 mt-0.5">Cards ready for review</span>
          </div>
        </button>
        <button v-if="stats.new > 0" @click="startSession('new')"
                class="flex items-center gap-4 px-6 py-4 border-2 border-green-600 rounded-xl text-left hover:bg-green-50 transition">
          <span class="text-2xl flex-shrink-0">🌱</span>
          <div>
            <span class="block font-semibold text-green-700">
              Learn new ({{ stats.new > 10 ? 10 : stats.new }})
            </span>
            <span class="block text-sm text-gray-500 mt-0.5">Concepts you haven't seen</span>
          </div>
        </button>

        <NuxtLink to="/" class="text-sm text-gray-400 hover:text-gray-600 mt-4">&larr; Back to categories</NuxtLink>
      </div>
    </div>

    <!-- Study session -->
    <template v-else>
      <button v-if="card" @click="finishSession('user_ended')"
              class="text-blue-600 hover:underline mb-4 inline-block">
        Stop reviewing
      </button>

      <div v-if="error" class="text-red-500">
        {{ error.data?.detail || error }}
      </div>

      <StudyCompletionScreen
        v-else-if="sessionFinished || !card"
        :category-name="categoryDisplayName"
        :category-emoji="categoryEmoji"
        :cards-reviewed="cardsReviewedInSession"
        :new-concepts="newConceptsInSession"
        :reviewed-concepts="reviewedConceptsInSession"
        :running-total="isLoggedIn ? (categoryLearnedCount + newConceptsInSession) : null"
        :category-total="categoryTotal"
        :remaining-cards="remainingCards"
        :has-more-cards="hasMoreCards"
        :is-logged-in="isLoggedIn"
        :mode="mode"
        @keep-going="keepGoing"
        @switch-mode="startSession"
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
          :mode="mode"
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
          :mode="mode"
          @rate="recordResponse"
          @next="nextCard"
        />
      </div>
    </template>
  </div>
</template>
