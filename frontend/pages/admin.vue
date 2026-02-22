<script setup lang="ts">
useSeoMeta({
  title: 'Admin | dsaflash.cards',
  robots: 'noindex, nofollow',
})

const { isAdmin, isLoggedIn, authReady } = useAuth()
const { apiFetch } = useApiFetch()

interface AnalyticsSummary {
  total_sessions: number
  anonymous_sessions: number
  avg_cards_per_session: number
  median_session_duration_ms: number
  drop_off_distribution: Record<string, number>
  conversion_rate: number
  lessons_completed: number
  users_with_lessons: number
  quizzes_taken: number
  users_with_quizzes: number
  avg_quiz_score_pct: number
  funnel: {
    lesson_users: number
    quiz_users: number
    review_users: number
  }
  anonymous_engagement: {
    lesson_views: number
    lesson_sessions: number
    quiz_starts: number
    quiz_completions: number
    quiz_sessions: number
  }
  category_lesson_completions: Record<string, number>
}

const summary = ref<AnalyticsSummary | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

watchEffect(async () => {
  if (!authReady.value) return
  if (!isLoggedIn.value || !isAdmin.value) {
    await navigateTo('/')
    return
  }
  if (!summary.value) await fetchSummary()
})

async function fetchSummary() {
  loading.value = true
  error.value = null
  try {
    summary.value = await apiFetch<AnalyticsSummary>('/analytics/summary')
  } catch (e: any) {
    error.value = e?.data?.detail || 'Failed to load analytics'
  } finally {
    loading.value = false
  }
}

const authenticatedSessions = computed(() => {
  if (!summary.value) return 0
  return summary.value.total_sessions - summary.value.anonymous_sessions
})

const conversionPercent = computed(() => {
  if (!summary.value) return '0'
  return (summary.value.conversion_rate * 100).toFixed(1)
})

const medianDurationSeconds = computed(() => {
  if (!summary.value) return '0'
  return (summary.value.median_session_duration_ms / 1000).toFixed(0)
})

const dropOffBuckets = computed(() => {
  if (!summary.value) return []
  const dist = summary.value.drop_off_distribution
  const order = ['0', '1-3', '4-9', '10+']
  return order
    .filter((k) => k in dist)
    .map((k) => ({ label: `${k} cards`, count: dist[k] }))
})

const funnelSteps = computed(() => {
  if (!summary.value) return []
  const f = summary.value.funnel
  return [
    { label: 'Completed a lesson', count: f.lesson_users },
    { label: 'Took a quiz', count: f.quiz_users },
    { label: 'Reviewed flashcards', count: f.review_users },
  ]
})

const maxFunnelCount = computed(() => {
  if (!funnelSteps.value.length) return 1
  return Math.max(...funnelSteps.value.map((s) => s.count), 1)
})

const categoryLessonList = computed(() => {
  if (!summary.value) return []
  const entries = Object.entries(summary.value.category_lesson_completions)
  return entries.sort((a, b) => b[1] - a[1])
})
</script>

<template>
  <div class="max-w-4xl mx-auto">
    <h1 class="text-3xl font-bold mb-8">Analytics Dashboard</h1>

    <div v-if="loading" class="text-gray-500">Loading analytics...</div>
    <div v-else-if="error" class="text-red-600">{{ error }}</div>

    <template v-else-if="summary">
      <!-- Session stat cards -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500">Total Sessions</div>
          <div class="text-2xl font-bold">{{ summary.total_sessions }}</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500">Anonymous</div>
          <div class="text-2xl font-bold">{{ summary.anonymous_sessions }}</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500">Authenticated</div>
          <div class="text-2xl font-bold">{{ authenticatedSessions }}</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500">Conversion Rate</div>
          <div class="text-2xl font-bold">{{ conversionPercent }}%</div>
        </div>
      </div>

      <!-- Session metrics -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500 mb-1">Avg Cards per Session</div>
          <div class="text-2xl font-bold">{{ summary.avg_cards_per_session }}</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500 mb-1">Median Session Duration</div>
          <div class="text-2xl font-bold">{{ medianDurationSeconds }}s</div>
        </div>
      </div>

      <!-- Learning metrics -->
      <h2 class="text-xl font-semibold mb-4">Learning Metrics</h2>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500">Lessons Completed</div>
          <div class="text-2xl font-bold">{{ summary.lessons_completed }}</div>
          <div class="text-xs text-gray-500 mt-1">{{ summary.users_with_lessons }} users</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500">Quizzes Taken</div>
          <div class="text-2xl font-bold">{{ summary.quizzes_taken }}</div>
          <div class="text-xs text-gray-500 mt-1">{{ summary.users_with_quizzes }} users</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500">Avg Quiz Score</div>
          <div class="text-2xl font-bold">{{ summary.avg_quiz_score_pct }}%</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500">Quiz Pass Rate</div>
          <div class="text-2xl font-bold">
            {{ summary.quizzes_taken > 0 ? ((summary.avg_quiz_score_pct >= 70 ? summary.quizzes_taken : 0) > 0 ? '—' : '—') : '—' }}
          </div>
          <div class="text-xs text-gray-500 mt-1">Coming soon</div>
        </div>
      </div>

      <!-- Anonymous Engagement -->
      <h2 class="text-xl font-semibold mb-4">Anonymous Engagement</h2>
      <div class="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500">Lesson Views</div>
          <div class="text-2xl font-bold">{{ summary.anonymous_engagement.lesson_views }}</div>
          <div class="text-xs text-gray-500 mt-1">{{ summary.anonymous_engagement.lesson_sessions }} sessions</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500">Quiz Starts</div>
          <div class="text-2xl font-bold">{{ summary.anonymous_engagement.quiz_starts }}</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500">Quiz Completions</div>
          <div class="text-2xl font-bold">{{ summary.anonymous_engagement.quiz_completions }}</div>
          <div class="text-xs text-gray-500 mt-1">{{ summary.anonymous_engagement.quiz_sessions }} sessions</div>
        </div>
      </div>

      <!-- Lesson→Quiz→Flashcard Funnel -->
      <div class="bg-white rounded-lg shadow p-4 mb-8">
        <h2 class="text-lg font-semibold mb-4">Learning Funnel</h2>
        <p class="text-sm text-gray-500 mb-4">Unique users who reached each stage</p>
        <div class="space-y-3">
          <div v-for="step in funnelSteps" :key="step.label" class="flex items-center gap-3">
            <span class="text-sm text-gray-600 w-44">{{ step.label }}</span>
            <div class="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
              <div
                class="bg-emerald-500 h-full rounded-full transition-all"
                :style="{ width: `${Math.min((step.count / maxFunnelCount) * 100, 100)}%` }"
              />
            </div>
            <span class="text-sm font-medium w-12 text-right">{{ step.count }}</span>
          </div>
        </div>
      </div>

      <!-- Category lesson completions -->
      <div class="bg-white rounded-lg shadow p-4 mb-8" v-if="categoryLessonList.length">
        <h2 class="text-lg font-semibold mb-4">Lesson Completions by Category</h2>
        <div class="space-y-2">
          <div v-for="[category, count] in categoryLessonList" :key="category" class="flex items-center gap-3">
            <span class="text-sm text-gray-600 w-44 truncate">{{ category }}</span>
            <div class="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
              <div
                class="bg-indigo-500 h-full rounded-full transition-all"
                :style="{ width: `${Math.min((count / categoryLessonList[0][1]) * 100, 100)}%` }"
              />
            </div>
            <span class="text-sm font-medium w-12 text-right">{{ count }}</span>
          </div>
        </div>
      </div>

      <!-- Drop-off distribution -->
      <div class="bg-white rounded-lg shadow p-4" v-if="dropOffBuckets.length">
        <h2 class="text-lg font-semibold mb-4">Drop-off Distribution</h2>
        <p class="text-sm text-gray-500 mb-4">How many cards users review before leaving</p>
        <div class="space-y-3">
          <div v-for="bucket in dropOffBuckets" :key="bucket.label" class="flex items-center gap-3">
            <span class="text-sm text-gray-600 w-24">{{ bucket.label }}</span>
            <div class="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
              <div
                class="bg-indigo-500 h-full rounded-full transition-all"
                :style="{ width: `${Math.min((bucket.count / summary!.total_sessions) * 100, 100)}%` }"
              />
            </div>
            <span class="text-sm font-medium w-12 text-right">{{ bucket.count }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
