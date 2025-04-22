<script setup lang="ts">
const categories = [
  { name: 'Data Structures', slug: 'data-structures',        description: 'Arrays, stacks, trees, and more.', emoji: '📦' },
  { name: 'Algorithms',      slug: 'algorithms',             description: 'Sorting, searching, traversal…',   emoji: '⚙️' },
  { name: 'Advanced DSA',    slug: 'advanced-data-structures', description: 'Fenwick trees, tries, unions…', emoji: '🚀' },
  { name: 'Big O Notation',  slug: 'big-o',                  description: 'Complexity analysis essentials.',  emoji: '🧠' },
]

definePageMeta({
  layout: 'default',
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
      <NuxtLink
        v-for="cat in categories"
        :key="cat.slug"
        :to="`/category/${cat.slug}`"
        class="border p-6 rounded-xl shadow hover:shadow-lg transition"
      >
        <div class="text-3xl mb-2">{{ cat.emoji }}</div>
        <h2 class="text-xl font-semibold">{{ cat.name }}</h2>
        <p class="text-gray-500">{{ cat.description }}</p>
      </NuxtLink>
    </div>
  </div>
</template>
