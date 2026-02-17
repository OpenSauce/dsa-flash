<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRuntimeConfig, navigateTo } from '#imports'
import { useAuth } from '@/composables/useAuth'

interface DashboardKnowledgeSummary {
  total_concepts_learned: number
  concepts_mastered: number
  domains_explored: number
}

interface DashboardDomain {
  name: string
  slug: string
  total: number
  learned: number
  mastered: number
  mastery_pct: number
}

interface DashboardStreak {
  current: number
  longest: number
  today_reviewed: number
}

interface DashboardWeek {
  concepts_learned: number
  domains_studied: string[]
  study_days: number
}

interface DashboardWeakCard {
  id: number
  title: string
  category: string
  easiness: number
}

interface DashboardOut {
  knowledge_summary: DashboardKnowledgeSummary
  domains: DashboardDomain[]
  streak: DashboardStreak
  this_week: DashboardWeek
  weakest_cards: DashboardWeakCard[]
  study_calendar: string[]
}

const DOMAIN_DISPLAY_NAMES: Record<string, string> = {
  'aws': 'AWS',
  'data-structures': 'Data Structures',
  'algorithms': 'Algorithms',
  'advanced-data-structures': 'Advanced Data Structures',
  'big-o-notation': 'Big O Notation',
  'system-design': 'System Design',
}

function domainDisplayName(slug: string, apiName: string): string {
  return DOMAIN_DISPLAY_NAMES[slug] ?? apiName
}

const { public: { apiBase } } = useRuntimeConfig()
const { isLoggedIn, authReady, tokenCookie } = useAuth()

const dashboard = ref<DashboardOut | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

const fetchDashboard = async () => {
  loading.value = true
  error.value = null
  try {
    const data = await $fetch<DashboardOut>(`${apiBase}/users/dashboard`, {
      headers: tokenCookie.value ? { Authorization: `Bearer ${tokenCookie.value}` } : {},
    })
    dashboard.value = data
  } catch (err) {
    error.value = 'Failed to load dashboard'
    console.error('dashboard fetch', err)
  } finally {
    loading.value = false
  }
}

watch(
  [authReady, isLoggedIn],
  async ([ready, loggedIn]) => {
    if (!ready) return
    if (!loggedIn) {
      navigateTo('/login')
      return
    }
    await fetchDashboard()
  },
  { immediate: true }
)

const today = new Date()
const currentYear = today.getFullYear()
const currentMonth = today.getMonth()

function buildCalendarGrid(studiedDates: string[]) {
  const studiedSet = new Set(studiedDates)
  const firstDay = new Date(currentYear, currentMonth, 1).getDay()
  const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate()
  const grid: Array<{ day: number | null; studied: boolean; future: boolean }> = []

  for (let i = 0; i < firstDay; i++) {
    grid.push({ day: null, studied: false, future: false })
  }

  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    const cellDate = new Date(currentYear, currentMonth, d)
    const future = cellDate > today
    grid.push({ day: d, studied: studiedSet.has(dateStr), future })
  }

  return grid
}

const calendarGrid = computed(() => {
  if (!dashboard.value) return []
  return buildCalendarGrid(dashboard.value.study_calendar)
})

const monthLabel = computed(() => {
  return new Date(currentYear, currentMonth, 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
})

const thisWeekDomainNames = computed(() => {
  if (!dashboard.value) return []
  const domainsBySlug: Record<string, string> = {}
  for (const d of dashboard.value.domains) {
    domainsBySlug[d.slug] = domainDisplayName(d.slug, d.name)
  }
  return dashboard.value.this_week.domains_studied.map(slug => domainsBySlug[slug] ?? slug)
})

const weekSummaryText = computed(() => {
  if (!dashboard.value) return ''
  const { concepts_learned, study_days } = dashboard.value.this_week
  const names = thisWeekDomainNames.value
  let text = `This week you learned ${concepts_learned} new concept${concepts_learned !== 1 ? 's' : ''}`
  if (names.length > 0) {
    text += ` in ${names.join(', ')}`
  }
  text += `. You studied ${study_days} out of 7 days.`
  return text
})

function colorForPct(pct: number): string {
  if (pct === 0) return '#d1d5db'
  if (pct === 100) return '#f59e0b'
  if (pct >= 50) return '#22c55e'
  return '#6366f1'
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-8">
    <div v-if="loading" class="flex justify-center py-20">
      <div class="text-gray-400 text-lg">Loading your knowledge portfolio...</div>
    </div>

    <div v-else-if="error" class="text-center py-20 text-red-500">
      {{ error }}
    </div>

    <template v-else-if="dashboard">
      <!-- Hero stat block -->
      <div class="mb-10 text-center">
        <p class="text-gray-500 text-lg mb-1">Your knowledge portfolio</p>
        <h1 class="font-headline text-4xl sm:text-5xl font-bold leading-tight text-gray-900">
          You know
          <span class="text-indigo-600">{{ dashboard.knowledge_summary.total_concepts_learned }}</span>
          tech concepts
        </h1>
        <p class="text-gray-600 mt-2 text-xl">
          across
          <span class="font-semibold">{{ dashboard.knowledge_summary.domains_explored }}</span>
          {{ dashboard.knowledge_summary.domains_explored === 1 ? 'domain' : 'domains' }}
          &nbsp;&middot;&nbsp;
          <span class="font-semibold text-green-600">{{ dashboard.knowledge_summary.concepts_mastered }}</span>
          mastered
        </p>
      </div>

      <!-- Streak display -->
      <div class="mb-10 flex justify-center">
        <div class="inline-flex items-center gap-6 bg-white border rounded-xl shadow px-8 py-5">
          <div class="flex items-center gap-2">
            <svg class="w-8 h-8 text-orange-400" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M12 23c-3.866 0-7-3.134-7-7 0-3.037 2.5-6.5 5-9 .396-.396 1.058-.104 1.058.464 0 1.5 1.5 3.5 3 3.5-.442-2-1-4.5 0-7.5.167-.5.833-.5 1 0 1.5 4.5 4.942 6.5 4.942 9.536 0 3.866-3.134 7-7 7z" />
            </svg>
            <div>
              <div class="text-3xl font-bold text-gray-900">{{ dashboard.streak.current }}</div>
              <div class="text-sm text-gray-500">day streak</div>
            </div>
          </div>
          <div class="w-px h-12 bg-gray-200" />
          <div>
            <div class="text-2xl font-semibold text-gray-700">{{ dashboard.streak.longest }}</div>
            <div class="text-sm text-gray-500">longest streak</div>
          </div>
          <div class="w-px h-12 bg-gray-200" />
          <div>
            <div class="text-2xl font-semibold text-gray-700">{{ dashboard.streak.today_reviewed }}</div>
            <div class="text-sm text-gray-500">reviewed today</div>
          </div>
        </div>
      </div>

      <!-- Domain mastery grid -->
      <section class="mb-10">
        <h2 class="text-xl font-bold text-gray-800 mb-4">Domains</h2>
        <div class="grid sm:grid-cols-2 gap-4">
          <NuxtLink
            v-for="domain in dashboard.domains"
            :key="domain.slug"
            :to="`/category/${domain.slug}`"
            class="flex items-center gap-4 bg-white border rounded-xl shadow-sm hover:shadow-md transition p-4"
          >
            <!-- SVG progress ring -->
            <div class="flex-shrink-0">
              <svg viewBox="0 0 36 36" class="w-14 h-14">
                <circle cx="18" cy="18" r="15.9155" fill="none" stroke="#e5e7eb" stroke-width="3" />
                <circle
                  cx="18" cy="18" r="15.9155" fill="none"
                  :stroke="colorForPct(domain.mastery_pct)"
                  stroke-width="3"
                  stroke-dasharray="100"
                  :stroke-dashoffset="100 - domain.mastery_pct"
                  stroke-linecap="round"
                  transform="rotate(-90 18 18)"
                />
                <text x="18" y="21" text-anchor="middle" font-size="8" fill="#374151" font-weight="600">
                  {{ domain.mastery_pct }}%
                </text>
              </svg>
            </div>
            <div class="min-w-0">
              <div class="font-semibold text-gray-900 truncate">{{ domainDisplayName(domain.slug, domain.name) }}</div>
              <div class="text-sm text-gray-500">
                {{ domain.mastered }} of {{ domain.total }} mastered
              </div>
              <div class="text-xs text-gray-400 mt-0.5">
                {{ domain.learned }} concept{{ domain.learned !== 1 ? 's' : '' }} learned
              </div>
            </div>
          </NuxtLink>
        </div>
      </section>

      <!-- This week summary -->
      <section class="mb-10">
        <h2 class="text-xl font-bold text-gray-800 mb-3">This week</h2>
        <div class="bg-white border rounded-xl shadow-sm p-5 text-gray-700">
          <p v-if="dashboard.this_week.concepts_learned > 0">{{ weekSummaryText }}</p>
          <p v-else class="text-gray-500">
            No new concepts learned this week yet. Start studying to build your knowledge!
          </p>
        </div>
      </section>

      <!-- Study calendar -->
      <section class="mb-10">
        <h2 class="text-xl font-bold text-gray-800 mb-3">{{ monthLabel }}</h2>
        <div class="bg-white border rounded-xl shadow-sm p-5">
          <div class="grid grid-cols-7 gap-1 text-center text-xs text-gray-400 mb-2">
            <div>Sun</div>
            <div>Mon</div>
            <div>Tue</div>
            <div>Wed</div>
            <div>Thu</div>
            <div>Fri</div>
            <div>Sat</div>
          </div>
          <div class="grid grid-cols-7 gap-1">
            <div
              v-for="(cell, i) in calendarGrid"
              :key="i"
              class="aspect-square flex items-center justify-center rounded-full text-xs font-medium"
              :class="{
                'bg-indigo-500 text-white': cell.day !== null && cell.studied,
                'text-gray-400': cell.day !== null && !cell.studied && !cell.future,
                'text-gray-200': cell.day !== null && cell.future,
                'invisible': cell.day === null,
              }"
            >
              <span v-if="cell.day !== null">{{ cell.day }}</span>
            </div>
          </div>
          <div class="flex items-center gap-4 mt-3 text-xs text-gray-500">
            <div class="flex items-center gap-1">
              <div class="w-3 h-3 rounded-full bg-indigo-500" />
              <span>Studied</span>
            </div>
            <div class="flex items-center gap-1">
              <div class="w-3 h-3 rounded-full bg-gray-200" />
              <span>Not studied</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Needs practice section -->
      <section v-if="dashboard.weakest_cards.length > 0" class="mb-10">
        <h2 class="text-xl font-bold text-gray-800 mb-3">These concepts need more practice</h2>
        <div class="bg-white border rounded-xl shadow-sm divide-y">
          <div
            v-for="card in dashboard.weakest_cards"
            :key="card.id"
            class="flex items-center justify-between px-5 py-3"
          >
            <div>
              <div class="font-medium text-gray-800">{{ card.title }}</div>
              <div class="text-sm text-gray-500">
                {{ domainDisplayName(card.category, card.category.replace(/-/g, ' ')) }}
              </div>
            </div>
            <NuxtLink
              :to="`/category/${card.category}`"
              class="text-sm font-medium text-indigo-600 hover:underline ml-4 flex-shrink-0"
            >
              Study now
            </NuxtLink>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
