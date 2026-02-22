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

// Lesson state
interface CategoryLessonInfo {
  slug: string
  title: string
  completed: boolean
  has_quiz: boolean
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

function handleLearnNew() {
  startSession('new')
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 sm:px-6">

    <Breadcrumb :items="sessionStarted
      ? [{ label: 'Home', to: '/' }, { label: categoryDisplayName, onClick: () => finishSession('user_ended') }, { label: 'Review' }]
      : [{ label: 'Home', to: '/' }, { label: categoryDisplayName }]"
    />

    <!-- Mode selector (logged-in users only, before session starts) -->
    <div v-if="!sessionStarted && isLoggedIn" class="text-center py-4 sm:py-12">
      <div class="text-4xl mb-2">{{ categoryEmoji }}</div>
      <h2 class="text-2xl font-bold mb-6">{{ categoryDisplayName }}</h2>

      <div v-if="!statsLoaded"><!-- waiting for stats --></div>

      <template v-else>
        <div class="flex flex-col gap-3 max-w-sm mx-auto">
          <!-- Review due button (always at top when cards are due) -->
          <button v-if="stats.due > 0" @click="startSession('due')"
                  class="flex items-center gap-4 px-6 py-4 border-2 border-blue-600 rounded-xl text-left hover:bg-blue-50 transition">
            <span class="text-2xl flex-shrink-0">💧</span>
            <div>
              <span class="block font-semibold text-blue-700">Review due ({{ stats.due }})</span>
              <span class="block text-sm text-gray-500 mt-0.5">Cards ready for review</span>
            </div>
          </button>

          <!-- Lesson checklist (categories with lessons) -->
          <div v-if="categoryLessons.length > 0" class="mt-2">
            <h3 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Lessons</h3>
            <ul class="space-y-2">
              <li v-for="lesson in categoryLessons" :key="lesson.slug">
                <NuxtLink
                  :to="`/lesson/${lesson.slug}`"
                  class="flex items-center gap-3 px-4 py-3 rounded-lg border text-left transition"
                  :class="lesson.completed
                    ? 'border-green-200 bg-green-50 hover:bg-green-100'
                    : 'border-gray-200 bg-white hover:bg-gray-50'"
                >
                  <span v-if="lesson.completed" class="flex-shrink-0 text-green-600">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </span>
                  <span v-else class="flex-shrink-0 w-5 h-5 rounded-full border-2 border-gray-300" />
                  <span class="text-sm font-medium" :class="lesson.completed ? 'text-green-800' : 'text-gray-700'">
                    {{ lesson.title }}
                  </span>
                </NuxtLink>
              </li>
            </ul>
          </div>

          <!-- Learn new button (only for categories without lessons, or all lessons done) -->
          <button v-if="stats.new > 0 && (categoryLessons.length === 0 || allLessonsComplete)" @click="handleLearnNew()"
                  class="flex items-center gap-4 px-6 py-4 border-2 border-green-600 rounded-xl text-left hover:bg-green-50 transition">
            <span class="text-2xl flex-shrink-0">🌱</span>
            <div>
              <span class="block font-semibold text-green-700">
                Learn new ({{ stats.new > 10 ? 10 : stats.new }})
              </span>
              <span class="block text-sm text-gray-500 mt-0.5">Concepts you haven't seen</span>
            </div>
          </button>

          <div v-if="stats.due === 0 && stats.new === 0 && categoryLessons.length === 0" class="text-gray-500 text-center">
            <p>No cards due and no new cards. Come back tomorrow!</p>
          </div>

          <NuxtLink to="/" class="block text-sm text-gray-400 hover:text-gray-600 mt-6 text-center">&larr; Back to categories</NuxtLink>
        </div>
      </template>
    </div>

    <!-- Study session -->
    <template v-else>
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

        <div class="hidden sm:flex justify-center mt-6">
          <button @click="finishSession('user_ended')"
                  class="text-sm text-gray-400 hover:text-gray-600 transition">
            &larr; Back to categories
          </button>
        </div>
      </div>
    </template>
  </div>
</template>
