<script setup lang="ts">
const { isAdmin, isLoggedIn, authReady, tokenCookie } = useAuth()

interface AnalyticsSummary {
  total_sessions: number
  anonymous_sessions: number
  avg_cards_per_session: number
  median_session_duration_ms: number
  drop_off_distribution: Record<string, number>
  conversion_rate: number
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
    summary.value = await $fetch<AnalyticsSummary>('/api/analytics/summary', {
      headers: { Authorization: `Bearer ${tokenCookie.value}` },
    })
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
</script>

<template>
  <div class="max-w-4xl mx-auto">
    <h1 class="text-3xl font-bold mb-8">Analytics Dashboard</h1>

    <div v-if="loading" class="text-gray-500">Loading analytics...</div>
    <div v-else-if="error" class="text-red-600">{{ error }}</div>

    <template v-else-if="summary">
      <!-- Stat cards -->
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
