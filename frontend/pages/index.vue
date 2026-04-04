<script setup lang="ts">
import { computed, ref, watch, onMounted, nextTick } from 'vue'
import { useAsyncData } from '#imports'
import { useAuth } from '@/composables/useAuth'
import { useAnalytics } from '@/composables/useAnalytics'
import { CATEGORY_META, DEFAULT_META, SECTION_ORDER, getCategoryDisplayName } from '@/utils/categoryMeta'

useSeoMeta({
  title: 'Flashcards for Engineers – Master Technical Concepts | dsaflash.cards',
  ogTitle: 'Flashcards for Engineers – Master Technical Concepts | dsaflash.cards',
  description: 'Free spaced repetition flashcards for data structures, algorithms, system design, AWS, Kubernetes, Docker, and networking. No signup required.',
  ogDescription: 'Free spaced repetition flashcards for data structures, algorithms, system design, AWS, Kubernetes, Docker, and networking. No signup required.',
  ogUrl: 'https://dsaflash.cards/',
  ogType: 'website',
})

const orderedSlugs = SECTION_ORDER.flatMap((section) =>
  Object.entries(CATEGORY_META)
    .filter(([, meta]) => meta.section === section)
    .map(([slug]) => slug)
)
const categoryListItems = orderedSlugs.map((slug, i) => ({
  '@type': 'ListItem',
  position: i + 1,
  name: getCategoryDisplayName(slug),
  url: `https://dsaflash.cards/category/${slug}`,
}))

useHead({
  link: [{ rel: 'canonical', href: 'https://dsaflash.cards/' }],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        name: 'dsaflash.cards',
        url: 'https://dsaflash.cards',
        description: 'Free spaced repetition flashcards for engineers covering data structures, algorithms, system design, AWS, Kubernetes, Docker, and networking.',
      }),
    },
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'ItemList',
        name: 'Technical Flashcard Categories',
        itemListElement: categoryListItems,
      }),
    },
  ],
})

interface CategoryFromAPI {
  slug: string
  name: string
  total: number
  due: number | null
  new: number | null
  learned: number | null
  mastered: number | null
  mastery_pct: number | null
  learned_pct: number | null
  lessons_available: number | null
  lessons_completed: number | null
  first_lesson_slug: string | null
}

interface CategoryDisplay extends CategoryFromAPI {
  emoji: string
  description: string
  section: string
}

interface ProblemCategory {
  category: string
  total: number
  solved: number | null
  due: number | null
  mastered: number | null
  difficulty: { easy: number; medium: number; hard: number }
  languages: string[]
}

const { apiFetch } = useApiFetch()
const route = useRoute()
const router = useRouter()

const { isLoggedIn } = useAuth()
const { track } = useAnalytics()

const activeTab = ref<'concepts' | 'problems'>(
  route.query.view === 'problems' ? 'problems' : 'concepts'
)

watch(activeTab, (tab) => {
  if (tab === 'problems') {
    router.replace({ query: { ...route.query, view: 'problems' } })
  } else {
    const { view, ...rest } = route.query
    router.replace({ query: rest })
  }
  if (tab === 'problems' && !problemCategories.value) {
    refreshProblemCategories()
  }
})

watch(() => route.query.view, (view) => {
  const nextTab = view === 'problems' ? 'problems' : 'concepts'
  if (activeTab.value !== nextTab) activeTab.value = nextTab
})

const { data: rawCategories, refresh: refreshCategories, error } = useAsyncData(
  'categories',
  () => apiFetch<CategoryFromAPI[]>('/categories'),
)

const { data: problemCategories, refresh: refreshProblemCategories, status: problemCategoriesStatus } = useAsyncData(
  'problem-categories',
  () => apiFetch<ProblemCategory[]>('/problems/categories'),
  { lazy: true, immediate: route.query.view === 'problems' },
)

const categories = computed<CategoryDisplay[]>(() => {
  if (!rawCategories.value) return []
  return rawCategories.value.map(cat => {
    const meta = CATEGORY_META[cat.slug] || DEFAULT_META
    return { ...cat, ...meta }
  })
})

const sections = computed(() => {
  const grouped: Record<string, CategoryDisplay[]> = {}
  for (const cat of categories.value) {
    const section = cat.section
    if (!grouped[section]) grouped[section] = []
    grouped[section].push(cat)
  }
  return SECTION_ORDER
    .filter(s => grouped[s]?.length)
    .map(s => ({ name: s, categories: grouped[s] }))
})

const visibleProblemCategories = computed<ProblemCategory[]>(() => {
  if (!problemCategories.value) return []
  return problemCategories.value.filter(c => c.total > 0)
})

function categoryTileTo(cat: CategoryDisplay): string {
  return `/category/${cat.slug}`
}

function problemCategoryLink(cat: ProblemCategory): string {
  return `/problems?category=${encodeURIComponent(cat.category)}`
}

function solvedPct(cat: ProblemCategory): number {
  if (!cat.total || cat.solved === null) return 0
  return Math.round((cat.solved / cat.total) * 100)
}

function masteredPct(cat: ProblemCategory): number {
  if (!cat.total || cat.mastered === null) return 0
  return Math.round((cat.mastered / cat.total) * 100)
}

onMounted(() => {
  track('page_view', { page: '/', referrer: document.referrer })
})

watch(isLoggedIn, () => {
  refreshCategories()
  refreshProblemCategories()
})

function handleTabKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
    e.preventDefault()
    activeTab.value = activeTab.value === 'concepts' ? 'problems' : 'concepts'
    nextTick(() => {
      const tabId = activeTab.value === 'concepts' ? 'tab-concepts' : 'tab-problems'
      document.getElementById(tabId)?.focus()
    })
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-6 pb-6">
    <h1 class="font-headline text-3xl sm:text-4xl font-bold text-center text-gray-900 mt-2 mb-2">
      Technical knowledge that sticks
    </h1>
    <div v-if="error" class="text-center text-red-400 py-8">
      Failed to load categories. Please try again later.
    </div>
    <p class="text-base sm:text-lg text-center text-gray-500 max-w-2xl mx-auto mb-4">
      Free flashcards powered by spaced repetition. Master data structures, system design, cloud, and more — no signup required.
    </p>
    <p v-if="!isLoggedIn" class="text-sm text-center text-gray-400 mb-6">Pick a topic below to start learning.</p>

    <!-- Concepts / Problems toggle -->
    <div
      role="tablist"
      class="flex bg-gray-100 rounded-lg p-1 mb-8 w-full sm:max-w-xs sm:mx-auto"
    >
      <button
        id="tab-concepts"
        role="tab"
        :aria-selected="activeTab === 'concepts'"
        :tabindex="activeTab === 'concepts' ? 0 : -1"
        aria-controls="panel-concepts"
        :class="activeTab === 'concepts' ? 'bg-purple-600 text-white shadow' : 'text-gray-600 hover:text-gray-900'"
        class="flex-1 px-4 py-2 text-sm font-semibold rounded-md transition"
        @click="activeTab = 'concepts'"
        @keydown="handleTabKeydown"
      >
        Concepts
      </button>
      <button
        id="tab-problems"
        role="tab"
        :aria-selected="activeTab === 'problems'"
        :tabindex="activeTab === 'problems' ? 0 : -1"
        aria-controls="panel-problems"
        :class="activeTab === 'problems' ? 'bg-purple-600 text-white shadow' : 'text-gray-600 hover:text-gray-900'"
        class="flex-1 px-4 py-2 text-sm font-semibold rounded-md transition"
        @click="activeTab = 'problems'"
        @keydown="handleTabKeydown"
      >
        Problems
      </button>
    </div>

    <!-- Concepts tab -->
    <div v-show="activeTab === 'concepts'" id="panel-concepts" role="tabpanel" aria-labelledby="tab-concepts">
      <template v-for="(section, index) in sections" :key="section.name">
        <h3 :class="['text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4', index > 0 ? 'mt-10' : '']">
          {{ section.name }}
        </h3>
        <div class="grid sm:grid-cols-2 gap-6">
          <NuxtLink v-for="cat in section.categories" :key="cat.slug" :to="categoryTileTo(cat)"
            class="border p-6 rounded-xl shadow hover:shadow-lg transition"
            :class="cat.due !== null && cat.due === 0 && cat.new === 0 ? 'bg-gray-100/80 opacity-60' : 'bg-white'">
            <div class="flex items-start justify-between">
              <div class="text-3xl mb-2">{{ cat.emoji }}</div>
              <div v-if="cat.learned_pct !== null" class="flex-shrink-0">
                <DualProgressRing
                  :learned-pct="cat.learned_pct"
                  :mastered-pct="cat.mastery_pct ?? 0"
                />
              </div>
            </div>
            <h2 class="text-xl font-semibold">{{ cat.name }}</h2>
            <p class="text-gray-500">{{ cat.description }}</p>
            <p v-if="cat.learned_pct !== null" class="text-sm text-gray-600 mt-2">
              <template v-if="cat.lessons_available && cat.lessons_available > 0">
                <span class="font-medium text-green-600">{{ cat.lessons_completed ?? 0 }}</span> of {{ cat.lessons_available }} lessons
                &nbsp;&middot;&nbsp;
                <span class="font-medium text-purple-600">{{ cat.mastered }}</span> concepts mastered
                &nbsp;&middot;&nbsp;
                <span class="font-medium text-blue-600">{{ cat.due }}</span> due
              </template>
              <template v-else>
                <span class="font-medium text-green-600">{{ cat.learned }}</span> of {{ cat.total }} learned
                &nbsp;&middot;&nbsp;
                <span class="font-medium text-purple-600">{{ cat.mastered }}</span> mastered
                &nbsp;&middot;&nbsp;
                <span class="font-medium text-blue-600">{{ cat.due }}</span> due
              </template>
            </p>
            <p v-else class="text-sm text-gray-600 mt-2">
              <template v-if="cat.lessons_available && cat.lessons_available > 0">
                <span class="font-medium text-green-600">{{ cat.lessons_available }}</span> lessons
                &nbsp;&middot;&nbsp;
              </template>
              <span class="font-medium text-indigo-600">{{ cat.total }}</span> concepts
            </p>
          </NuxtLink>
        </div>
      </template>
    </div>

    <!-- Problems tab -->
    <div v-show="activeTab === 'problems'" id="panel-problems" role="tabpanel" aria-labelledby="tab-problems">
      <div v-if="problemCategoriesStatus === 'pending'" class="text-center text-gray-400 py-12">
        Loading problem categories...
      </div>
      <div v-else-if="!visibleProblemCategories.length" class="text-center text-gray-400 py-12">
        No problem categories available yet.
      </div>
      <div v-else class="grid sm:grid-cols-2 gap-6">
        <NuxtLink
          v-for="cat in visibleProblemCategories"
          :key="cat.category"
          :to="problemCategoryLink(cat)"
          class="border bg-white p-6 rounded-xl shadow hover:shadow-lg transition"
        >
          <div class="flex items-start justify-between mb-3">
            <h2 class="text-xl font-semibold">{{ getCategoryDisplayName(cat.category) }}</h2>
            <div v-if="isLoggedIn && cat.solved !== null" class="flex-shrink-0">
              <DualProgressRing
                :learned-pct="solvedPct(cat)"
                :mastered-pct="masteredPct(cat)"
              />
            </div>
          </div>
          <p v-if="isLoggedIn && cat.solved !== null" class="text-sm text-gray-600 mb-2">
            <span class="font-medium text-green-600">{{ cat.solved }}</span> solved
            &nbsp;&middot;&nbsp;
            <span class="font-medium text-purple-600">{{ cat.mastered }}</span> mastered
            &nbsp;&middot;&nbsp;
            <span class="font-medium text-blue-600">{{ cat.due }}</span> due
          </p>
          <p v-else class="text-sm text-gray-600 mb-2">
            <span class="font-medium text-indigo-600">{{ cat.total }}</span> problems
          </p>
          <p class="text-sm text-gray-500">
            Easy {{ cat.difficulty.easy }} / Med {{ cat.difficulty.medium }} / Hard {{ cat.difficulty.hard }}
          </p>
          <p class="text-xs text-gray-400 mt-1">{{ cat.languages.join(', ') }}</p>
        </NuxtLink>
      </div>
    </div>
  </div>
</template>
