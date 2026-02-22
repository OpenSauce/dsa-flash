<script setup lang="ts">
import { computed, watch, onMounted } from 'vue'
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

const { apiFetch } = useApiFetch()

const { isLoggedIn } = useAuth()
const { track } = useAnalytics()

const { data: rawCategories, refresh: refreshCategories, error } = useAsyncData(
  'categories',
  () => apiFetch<CategoryFromAPI[]>('/categories'),
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

function categoryTileTo(cat: CategoryDisplay): string {
  return `/category/${cat.slug}`
}

onMounted(() => {
  track('page_view', { page: '/', referrer: document.referrer })
})

watch(isLoggedIn, () => {
  refreshCategories()
})
</script>

<template>
  <div class="max-w-4xl mx-auto px-6 pb-6">
    <h1 class="sr-only">Technical interview flashcards powered by spaced repetition</h1>
    <div v-if="error" class="text-center text-red-400 py-8">
      Failed to load categories. Please try again later.
    </div>
    <p class="text-base sm:text-lg text-center text-gray-600 max-w-2xl mx-auto mb-4">
      Free flashcards powered by spaced repetition. Master data structures, system design, cloud, and more — no signup required.
    </p>

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
</template>
