<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useCookie, useRuntimeConfig } from '#imports'
import { useAuth } from '@/composables/useAuth'
import { useAnalytics } from '@/composables/useAnalytics'

interface CategoryFromAPI {
  slug: string
  name: string
  total: number
  due: number | null
  new: number | null
  learned: number | null
  mastered: number | null
  mastery_pct: number | null
}

interface CategoryDisplay extends CategoryFromAPI {
  emoji: string
  description: string
  section: string
}

const CATEGORY_META: Record<string, { emoji: string; description: string; section: string; displayName?: string }> = {
  'data-structures': { emoji: '📦', description: 'Arrays, stacks, trees, and more.', section: 'Coding' },
  'algorithms': { emoji: '⚙️', description: 'Sorting, searching, traversal...', section: 'Coding' },
  'advanced-data-structures': { emoji: '🚀', description: 'Fenwick trees, tries, unions...', section: 'Coding' },
  'big-o-notation': { emoji: '🧠', description: 'Complexity analysis essentials.', section: 'Coding' },
  'system-design': { emoji: '🏗️', description: 'Load balancing, caching, scaling...', section: 'System Design' },
  'aws': { emoji: '☁️', description: 'EC2, S3, Lambda, VPC, and more.', section: 'System Design', displayName: 'AWS' },
  'kubernetes': { emoji: '☸️', description: 'Pods, Deployments, Services, networking...', section: 'System Design' },
  'docker-linux': { emoji: '🐳', description: 'Containers, Dockerfiles, Linux fundamentals...', section: 'System Design' },
}

const DEFAULT_META = { emoji: '📘', description: 'Flashcard concepts.', section: 'Other' }

const SECTION_ORDER = ['Coding', 'System Design', 'Other']

const { public: { apiBase } } = useRuntimeConfig()
const token = useCookie('token')

const { isLoggedIn, authReady } = useAuth()
const { track } = useAnalytics()

const categories = ref<CategoryDisplay[]>([])

const fetchCategories = async () => {
  try {
    const headers = token.value
      ? { Authorization: `Bearer ${token.value}` }
      : undefined
    const data = await $fetch<CategoryFromAPI[]>(`${apiBase}/categories`, { headers })
    categories.value = data.map(cat => {
      const meta = CATEGORY_META[cat.slug] || DEFAULT_META
      return { ...cat, ...meta, name: meta.displayName || cat.name }
    })
  } catch (err) {
    console.error('categories fetch', err)
  }
}

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

onMounted(() => {
  track('page_view', { page: '/', referrer: document.referrer })
})

watch(
  [authReady, isLoggedIn],
  async ([ready]) => {
    if (ready) {
      await fetchCategories()
    }
  },
  { immediate: true }
)
</script>

<template>
  <div class="max-w-4xl mx-auto px-6 pt-4 pb-6">
    <h1 class="font-headline text-4xl sm:text-5xl mb-2 text-center leading-tight">
      📚 dsaflash.cards
    </h1>
    <p class="text-base sm:text-lg text-center text-gray-600 max-w-2xl mx-auto mb-6">
      Free flashcards powered by spaced repetition. Master data structures, system design, cloud, and more — no signup required.
    </p>

    <template v-for="(section, index) in sections" :key="section.name">
      <h3 :class="['text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4', index > 0 ? 'mt-10' : '']">
        {{ section.name }}
      </h3>
      <div class="grid sm:grid-cols-2 gap-6">
        <NuxtLink v-for="cat in section.categories" :key="cat.slug" :to="`/category/${cat.slug}`"
          class="border p-6 rounded-xl shadow hover:shadow-lg transition">
          <div class="flex items-start justify-between">
            <div class="text-3xl mb-2">{{ cat.emoji }}</div>
            <div v-if="cat.mastery_pct !== null" class="flex-shrink-0">
              <svg viewBox="0 0 36 36" class="w-14 h-14"
                :aria-label="cat.mastery_pct === 100 ? '100% mastered' : 'Mastery: ' + cat.mastery_pct + '%'"
              >
                <circle cx="18" cy="18" r="15.9155" fill="none" stroke="#e5e7eb" stroke-width="3" />
                <circle
                  cx="18" cy="18" r="15.9155" fill="none"
                  :stroke="colorForPct(cat.mastery_pct)"
                  stroke-width="3"
                  stroke-dasharray="100"
                  :stroke-dashoffset="100 - cat.mastery_pct"
                  stroke-linecap="round"
                  transform="rotate(-90 18 18)"
                />
                <text v-if="cat.mastery_pct === 100" x="18" y="22" text-anchor="middle" font-size="12" fill="#f59e0b">&#10003;</text>
                <text v-else x="18" y="21" text-anchor="middle" font-size="8" fill="#374151" font-weight="600">
                  {{ cat.mastery_pct }}%
                </text>
              </svg>
            </div>
          </div>
          <h2 class="text-xl font-semibold">{{ cat.name }}</h2>
          <p class="text-gray-500">{{ cat.description }}</p>
          <p v-if="cat.mastery_pct !== null" class="text-sm text-gray-600 mt-2">
            <span class="font-medium">{{ cat.mastered }}</span> of {{ cat.total }} mastered
            &nbsp;&middot;&nbsp;
            <span class="font-medium">{{ cat.learned }}</span> learned
            &nbsp;&middot;&nbsp;
            <span class="font-medium">{{ cat.due }}</span> due
          </p>
          <p v-else class="text-sm text-gray-600 mt-2">
            <span class="font-medium">{{ cat.total }}</span> concepts
          </p>
        </NuxtLink>
      </div>
    </template>
  </div>
</template>
