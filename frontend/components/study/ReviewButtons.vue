<script setup lang="ts">
defineProps<{
  revealed: boolean
  isLoggedIn: boolean
  buttonsEnabled: boolean
  mode: string
}>()

defineEmits<{
  (e: 'rate', grade: 'again' | 'good' | 'easy'): void
  (e: 'next'): void
}>()
</script>

<template>
  <!-- Logged-in: review buttons -->
  <div v-if="revealed && isLoggedIn" class="text-center">
    <div class="flex justify-center gap-4 rating-buttons" :class="{ 'rating-buttons--visible': buttonsEnabled }">
      <button @click="buttonsEnabled && $emit('rate', 'again')"
              :disabled="!buttonsEnabled"
              class="px-5 py-3 bg-red-600 text-white rounded-lg transition-opacity disabled:cursor-not-allowed">
        <span class="font-semibold">{{ mode === 'new' ? 'Tricky' : 'Again' }}</span>
        <span class="block text-xs opacity-80 mt-0.5">{{ mode === 'new' ? 'Review soon' : 'Review again soon' }}</span>
      </button>
      <button @click="buttonsEnabled && $emit('rate', 'good')"
              :disabled="!buttonsEnabled"
              class="px-5 py-3 bg-yellow-500 text-white rounded-lg transition-opacity disabled:cursor-not-allowed">
        <span class="font-semibold">{{ mode === 'new' ? 'Got it' : 'Almost' }}</span>
        <span class="block text-xs opacity-80 mt-0.5">Review later</span>
      </button>
      <button @click="buttonsEnabled && $emit('rate', 'easy')"
              :disabled="!buttonsEnabled"
              class="px-5 py-3 bg-green-600 text-white rounded-lg transition-opacity disabled:cursor-not-allowed">
        <span class="font-semibold">{{ mode === 'new' ? 'Easy' : 'I know it' }}</span>
        <span class="block text-xs opacity-80 mt-0.5">I could explain this</span>
      </button>
    </div>
    <p class="text-xs text-gray-400 mt-3">Press 1, 2, or 3</p>
  </div>

  <!-- Anonymous: next card button -->
  <div v-if="revealed && !isLoggedIn" class="flex justify-center">
    <button @click="$emit('next')" class="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
      Next card &rarr;
    </button>
  </div>
</template>

<style scoped>
.rating-buttons {
  opacity: 0;
  transition: opacity 400ms ease-out;
}
.rating-buttons--visible {
  opacity: 1;
}
</style>
