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
  <div class="max-w-4xl mx-auto px-6 py-6">
    <h1 class="font-headline text-3xl sm:text-4xl mb-3 text-center leading-tight">
      📚 dsaflash.cards
    </h1>
    <p class="text-base sm:text-lg text-center text-gray-600 max-w-2xl mx-auto mb-10">
      Free flashcards powered by spaced repetition. Master data structures, system design, cloud, and more — no signup required.
    </p>

    <template v-for="(section, index) in sections" :key="section.name">
      <h3 :class="['text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4', index > 0 ? 'mt-10' : '']">
        {{ section.name }}
      </h3>
      <div class="grid sm:grid-cols-2 gap-6">
        <NuxtLink v-for="cat in section.categories" :key="cat.slug" :to="`/category/${cat.slug}`"
          class="border p-6 rounded-xl shadow hover:shadow-lg transition">
          <div class="text-3xl mb-2">{{ cat.emoji }}</div>
          <h2 class="text-xl font-semibold">{{ cat.name }}</h2>
          <p class="text-gray-500">{{ cat.description }}</p>
          <p v-if="cat.due !== null" class="text-sm text-gray-600 mt-2">
            <span class="font-medium">{{ cat.due }}</span> due &nbsp;·&nbsp;
            <span class="font-medium">{{ cat.new }}</span> new
          </p>
          <p v-else class="text-sm text-gray-600 mt-2">
            <span class="font-medium">{{ cat.total }}</span> cards
          </p>
        </NuxtLink>
      </div>
    </template>
  </div>
</template>
