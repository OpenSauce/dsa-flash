<script setup lang="ts">
defineProps<{
  cardsReviewed: number
  remainingCards: number
  hasMoreCards: boolean
  isLoggedIn: boolean
}>()

defineEmits<{
  (e: 'keep-going'): void
}>()
</script>

<template>
  <div class="text-center py-16">
    <template v-if="cardsReviewed > 0">
      <h2 class="text-2xl font-bold mb-2 font-heading">Batch complete!</h2>
      <p class="text-gray-600 mb-2">You reviewed {{ cardsReviewed }} cards</p>
      <p v-if="remainingCards > 0" class="text-gray-500 text-sm mb-8">{{ remainingCards }} cards remaining in this category</p>
      <p v-else-if="isLoggedIn" class="text-gray-500 text-sm mb-8">Come back tomorrow for your next review</p>
      <p v-else class="text-gray-500 text-sm mb-8">You've seen all the cards in this category!</p>
      <div class="flex justify-center gap-4">
        <NuxtLink to="/" class="px-6 py-2 border border-gray-300 rounded hover:bg-gray-50">
          &larr; Back to categories
        </NuxtLink>
        <button v-if="hasMoreCards" @click="$emit('keep-going')"
                class="px-6 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700">
          Keep going
        </button>
      </div>
    </template>
    <template v-else>
      <p class="text-gray-500">No cards due right now.</p>
      <NuxtLink to="/" class="text-blue-600 hover:underline mt-4 inline-block">
        &larr; Back to categories
      </NuxtLink>
    </template>
  </div>
</template>
