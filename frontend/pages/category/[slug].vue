<script setup lang="ts">
import { useAnalytics } from '@/composables/useAnalytics'
import { CATEGORY_META, DEFAULT_META, getCategoryDisplayName } from '@/utils/categoryMeta'
import type { StudyMode } from '@/composables/useStudySession'

const route = useRoute()
const category = route.params.slug as string
const categoryEmoji = (CATEGORY_META[category] || DEFAULT_META).emoji

const categoryDisplayNameForMeta = getCategoryDisplayName(category)

useSeoMeta({
  title: `${categoryDisplayNameForMeta} Flashcards | dsaflash.cards`,
  ogTitle: `${categoryDisplayNameForMeta} Flashcards | dsaflash.cards`,
  description: `Free spaced repetition flashcards for ${categoryDisplayNameForMeta}. Learn and retain key concepts with active recall.`,
  ogDescription: `Free spaced repetition flashcards for ${categoryDisplayNameForMeta}. Learn and retain key concepts with active recall.`,
  ogUrl: `https://dsaflash.cards/category/${category}`,
  ogType: 'article',
})

useHead({
  link: [{ rel: 'canonical', href: `https://dsaflash.cards/category/${category}` }],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'Course',
        name: `${categoryDisplayNameForMeta} Flashcards`,
        description: `Spaced repetition flashcards covering ${categoryDisplayNameForMeta} concepts for engineers.`,
        provider: {
          '@type': 'Organization',
          name: 'dsaflash.cards',
          url: 'https://dsaflash.cards',
        },
        educationalLevel: 'intermediate',
        isAccessibleForFree: true,
        url: `https://dsaflash.cards/category/${category}`,
      }),
    },
  ],
})

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
const statsLoaded = ref(false)

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
  } finally {
    statsLoaded.value = true
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

// Lesson hint banner
interface CategoryLessonInfo {
  slug: string
  title: string
  completed: boolean
}
const categoryLessons = ref<CategoryLessonInfo[]>([])

const allLessonsComplete = computed(() =>
  categoryLessons.value.length > 0 && categoryLessons.value.every(l => l.completed)
)

onMounted(async () => {
  try {
    const headers = tokenCookie.value ? { Authorization: `Bearer ${tokenCookie.value}` } : {}
    categoryLessons.value = await $fetch<CategoryLessonInfo[]>(
      `${apiBase}/lessons/by-category/${category}`,
      { headers }
    )
  } catch {
    // non-fatal
  }
})

const {
  card, pending, error,
  sessionFinished, cardsReviewedInBatch, cardsReviewedInSession,
  currentBatchSize, remainingCards, hasMoreCards, progressPercent,
  revealed, buttonsEnabled, totalFlipsInSession,
  categoryDisplayName, categoryLearnedCount, categoryTotal,
  newConceptsInSession, reviewedConceptsInSession,
  hasFlippedOnce, hasFlippedEver,
  projectedIntervals,
  flipCard, nextCard, recordResponse, keepGoing, finishSession,
} = useStudySession({
  category, apiBase, isLoggedIn, tokenCookie,
  track, flushBeacon, refreshStreak, logout,
  mode,
})

const ctaDismissed = ref(false)

const showFlipHint = computed(() => !hasFlippedOnce.value && !hasFlippedEver.value)

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
  <div class="max-w-4xl mx-auto p-2 sm:p-6">

    <!-- Mode selector (logged-in users only, before session starts) -->
    <div v-if="!sessionStarted && isLoggedIn" class="text-center py-8 sm:py-16">
      <div class="text-4xl mb-2">{{ categoryEmoji }}</div>
      <h2 class="text-2xl font-bold mb-6">{{ categoryDisplayName }}</h2>

      <!-- Lesson hint banner -->
      <div v-if="categoryLessons.length > 0 && !allLessonsComplete"
           class="mb-6 rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-800 max-w-sm mx-auto text-left">
        <span class="font-medium">Recommended:</span> Read the lesson before studying flashcards.
        <NuxtLink :to="`/lesson/${categoryLessons[0].slug}`" class="underline font-semibold ml-1">
          Start lesson
        </NuxtLink>
      </div>

      <div v-if="!statsLoaded"><!-- waiting for stats --></div>

      <div v-else-if="stats.due === 0 && stats.new === 0" class="text-gray-500">
        <p class="mb-4">No cards due and no new cards. Come back tomorrow!</p>
        <NuxtLink to="/" class="text-blue-600 hover:underline">&larr; Back to categories</NuxtLink>
      </div>

      <div v-else class="flex flex-col gap-3 max-w-sm mx-auto">
        <button v-if="stats.due > 0" @click="startSession('due')"
                class="flex items-center gap-4 px-6 py-4 border-2 border-blue-600 rounded-xl text-left hover:bg-blue-50 transition">
          <span class="text-2xl flex-shrink-0">💧</span>
          <div>
            <span class="block font-semibold text-blue-700">Review due ({{ stats.due }})</span>
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

      <div v-else-if="pending && !card" class="py-16"><!-- loading cards --></div>

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

      <div v-else class="pb-24 sm:pb-0">
        <!-- Initial amber banner: anonymous users before 3rd flip -->
        <div v-if="!isLoggedIn && totalFlipsInSession < 3 && !ctaDismissed"
             class="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          <NuxtLink to="/signup" class="underline font-medium">Sign up</NuxtLink> to save your progress and unlock spaced repetition.
        </div>

        <!-- Upgraded CTA: appears after 3rd flip, dismissable -->
        <div v-if="!isLoggedIn && totalFlipsInSession >= 3 && !ctaDismissed"
             class="mb-4 rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-2.5 text-sm text-indigo-800 flex items-center justify-between gap-3">
          <div>
            <NuxtLink to="/signup" class="underline font-semibold">Sign up</NuxtLink>
            to save your progress and unlock spaced repetition &mdash; the system that makes knowledge stick.
          </div>
          <button @click="ctaDismissed = true"
                  class="flex-shrink-0 text-indigo-400 hover:text-indigo-600 transition"
                  aria-label="Dismiss signup prompt">
            <svg class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>

        <!-- "Learning new concepts" label for anonymous sessions -->
        <div v-if="!isLoggedIn" class="flex items-center gap-2 mb-2 text-sm text-green-700">
          <span class="text-lg">🌱</span>
          <span class="font-medium">Learning new concepts</span>
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
          :show-flip-hint="showFlipHint"
          @flip="flipCard"
        />

        <div class="fixed bottom-0 left-0 right-0 z-20 bg-gray-50 px-4 py-3 border-t border-gray-200 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)] sm:relative sm:border-0 sm:p-0 sm:bg-transparent sm:shadow-none sm:z-auto">
          <StudyReviewButtons
            :revealed="revealed"
            :buttons-enabled="buttonsEnabled"
            :mode="mode"
            :projected-intervals="projectedIntervals"
            @rate="recordResponse"
          />
        </div>
      </div>
    </template>
  </div>
</template>
