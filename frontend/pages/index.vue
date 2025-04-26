<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useCookie, definePageMeta, useRuntimeConfig } from '#imports'

interface Category {
  name: string
  slug: string
  description: string
  emoji: string
  due?: number
  unlearnt?: number
}

const categories = ref<Category[]>([
  { name: 'Data Structures', slug: 'data structures', description: 'Arrays, stacks, trees, and more.', emoji: '📦' },
  { name: 'Algorithms', slug: 'algorithms', description: 'Sorting, searching, traversal…', emoji: '⚙️' },
  { name: 'Advanced DSA', slug: 'advanced data structures', description: 'Fenwick trees, tries, unions…', emoji: '🚀' },
  { name: 'Big O Notation', slug: 'big o', description: 'Complexity analysis essentials.', emoji: '🧠' },
])

const { public: { apiBase } } = useRuntimeConfig()
const token = useCookie('token')

onMounted(async () => {

  const headers = token.value
    ? { Authorization: `Bearer ${token.value}` }
    : undefined
  await Promise.all(
    categories.value.map(async (cat) => {
      try {
        const qs = new URLSearchParams({ category: cat.slug })
        const stats = await $fetch<{ due: number; new: number }>(
          `${apiBase}/flashcards/stats?${qs}`,
          { headers },
        )
        cat.due = stats.due
        cat.unlearnt = stats.new
      } catch (err) {
        console.error('stats fetch', cat.slug, err)
      }
    }),
  )
})
</script>

<template>
  <div class="max-w-4xl mx-auto px-6 py-10">
    <h1 class="font-headline text-5xl sm:text-6xl mb-6 text-center leading-tight">
      📚 dsaflash.cards
    </h1>
    <p class="text-center text-gray-600 mb-10">
      Select a category to start learning with flashcards.
    </p>

    <div class="grid sm:grid-cols-2 gap-6">
      <NuxtLink v-for="cat in categories" :key="cat.slug" :to="`/category/${cat.slug}`"
        class="border p-6 rounded-xl shadow hover:shadow-lg transition">
        <div class="text-3xl mb-2">{{ cat.emoji }}</div>
        <h2 class="text-xl font-semibold">{{ cat.name }}</h2>
        <p class="text-gray-500">{{ cat.description }}</p>
        <p v-if="cat.due !== undefined" class="text-sm text-gray-600 mt-2">
          <span class="font-medium">{{ cat.due }}</span> due &nbsp;·&nbsp;
          <span class="font-medium">{{ cat.unlearnt }}</span> new
        </p>
      </NuxtLink>
    </div>
  </div>
</template>
