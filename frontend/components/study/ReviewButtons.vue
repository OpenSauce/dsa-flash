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
    <div class="flex justify-center gap-3 rating-buttons" :class="{ 'rating-buttons--visible': buttonsEnabled }">
      <button @click="buttonsEnabled && $emit('rate', 'again')"
              :disabled="!buttonsEnabled"
              class="px-5 py-2.5 bg-red-500 text-white rounded-xl hover:bg-red-600 transition disabled:cursor-not-allowed">
        <span class="font-semibold text-sm">{{ mode === 'new' ? 'Tricky' : 'Again' }}</span>
        <span class="block text-xs text-red-100 mt-0.5">{{ mode === 'new' ? 'Review soon' : 'Review again soon' }}</span>
      </button>
      <button @click="buttonsEnabled && $emit('rate', 'good')"
              :disabled="!buttonsEnabled"
              class="px-5 py-2.5 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition disabled:cursor-not-allowed">
        <span class="font-semibold text-sm">{{ mode === 'new' ? 'Got it' : 'Almost' }}</span>
        <span class="block text-xs text-blue-100 mt-0.5">Review later</span>
      </button>
      <button @click="buttonsEnabled && $emit('rate', 'easy')"
              :disabled="!buttonsEnabled"
              class="px-5 py-2.5 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 transition disabled:cursor-not-allowed">
        <span class="font-semibold text-sm">{{ mode === 'new' ? 'Easy' : 'I know it' }}</span>
        <span class="block text-xs text-emerald-100 mt-0.5">I could explain this</span>
      </button>
    </div>
    <p class="text-xs text-gray-400 mt-3">Press 1, 2, or 3</p>
  </div>

  <!-- Anonymous: next card button -->
  <div v-if="revealed && !isLoggedIn" class="flex justify-center">
    <button @click="$emit('next')" class="px-6 py-2 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition">
      Next card &rarr;
    </button>
  </div>
</template>

<style scoped>
.rating-buttons {
  opacity: 0;
  transition: opacity 150ms ease-out;
}
.rating-buttons--visible {
  opacity: 1;
}
</style>
