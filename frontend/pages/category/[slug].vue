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

const mode = ref<StudyMode>('due')
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
    // fallback: start session immediately
    sessionStarted.value = true
  } finally {
    statsLoaded.value = true
  }
}

watch(
  [authReady, isLoggedIn],
  async ([ready, loggedIn]) => {
    if (!ready) return
    if (loggedIn) {
      await fetchStats()
    }
    // Anonymous users: do NOT auto-start a session — show lesson list instead
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
  <div class="max-w-4xl mx-auto px-4 sm:px-6">

    <Breadcrumb :items="sessionStarted
      ? [{ label: 'Home', to: '/' }, { label: categoryDisplayName, onClick: () => finishSession('user_ended') }, { label: 'Review' }]
      : [{ label: 'Home', to: '/' }, { label: categoryDisplayName }]"
    />

    <!-- Anonymous user landing: lesson list + signup CTA -->
    <div v-if="!isLoggedIn && !sessionStarted" class="text-center py-4 sm:py-12">
      <div class="text-4xl mb-2">{{ categoryEmoji }}</div>
      <h2 class="text-2xl font-bold mb-6">{{ categoryDisplayName }}</h2>

      <!-- Lesson checklist (no completion marks since not logged in) -->
      <div v-if="categoryLessons.length > 0" class="max-w-sm mx-auto mb-8">
        <h3 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3 text-left">Lessons</h3>
        <ul class="space-y-2">
          <li v-for="lesson in categoryLessons" :key="lesson.slug">
            <NuxtLink
              :to="`/lesson/${lesson.slug}`"
              class="flex items-center gap-3 px-4 py-3 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-left transition"
            >
              <span class="flex-shrink-0 w-5 h-5 rounded-full border-2 border-gray-300" />
              <span class="text-sm font-medium text-gray-700">{{ lesson.title }}</span>
            </NuxtLink>
          </li>
        </ul>
      </div>

      <!-- Signup CTA -->
      <div class="max-w-sm mx-auto rounded-xl border border-indigo-100 bg-indigo-50 px-6 py-5 mb-6">
        <p class="text-sm font-semibold text-indigo-800 mb-1">Unlock spaced repetition flashcards</p>
        <p class="text-sm text-indigo-700 mb-4">Complete lessons and quizzes to build your review queue.</p>
        <NuxtLink
          to="/signup"
          class="inline-block px-5 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-lg hover:bg-indigo-700 transition"
        >
          Sign up — it's free
        </NuxtLink>
      </div>

      <NuxtLink to="/" class="block text-sm text-gray-400 hover:text-gray-600 text-center">&larr; Back to categories</NuxtLink>
    </div>

    <!-- Mode selector (logged-in users, before session starts) -->
    <div v-else-if="!sessionStarted && isLoggedIn" class="text-center py-4 sm:py-12">
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

          <div v-if="stats.due === 0 && categoryLessons.length === 0" class="text-gray-500 text-center">
            <p>All caught up! Come back tomorrow.</p>
          </div>

          <div v-else-if="stats.due === 0 && categoryLessons.length > 0" class="text-gray-500 text-center text-sm mt-2">
            <p>No cards due. Complete more lessons to build your review queue.</p>
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
      />

      <div v-else class="pb-24 sm:pb-0">
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
