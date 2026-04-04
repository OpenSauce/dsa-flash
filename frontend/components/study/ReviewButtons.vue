<script setup lang="ts">
defineProps<{
  revealed: boolean
  buttonsEnabled: boolean
  mode: string
  projectedIntervals?: Record<string, string> | null
}>()

defineEmits<{
  (e: 'rate', grade: 'again' | 'good' | 'easy'): void
}>()
</script>

<template>
  <div v-if="revealed" class="text-center">
    <div class="flex justify-center gap-3 rating-buttons" :class="{ 'rating-buttons--visible': buttonsEnabled }">
      <button @click="buttonsEnabled && $emit('rate', 'again')"
              :disabled="!buttonsEnabled"
              class="min-h-[44px] px-5 py-2.5 bg-red-50 border-2 border-red-200 text-red-700 rounded-lg hover:bg-red-100 transition disabled:cursor-not-allowed">
        <span class="font-semibold text-sm">Again</span>
        <span class="block text-xs opacity-70 mt-0.5">Review again soon</span>
        <span v-if="projectedIntervals" class="block text-[10px] font-mono opacity-60 mt-0.5">{{ projectedIntervals['1'] }}</span>
      </button>
      <button @click="buttonsEnabled && $emit('rate', 'good')"
              :disabled="!buttonsEnabled"
              class="min-h-[44px] px-5 py-2.5 bg-amber-50 border-2 border-amber-200 text-amber-700 rounded-lg hover:bg-amber-100 transition disabled:cursor-not-allowed">
        <span class="font-semibold text-sm">Almost</span>
        <span class="block text-xs opacity-70 mt-0.5">Review later</span>
        <span v-if="projectedIntervals" class="block text-[10px] font-mono opacity-60 mt-0.5">{{ projectedIntervals['3'] }}</span>
      </button>
      <button @click="buttonsEnabled && $emit('rate', 'easy')"
              :disabled="!buttonsEnabled"
              class="min-h-[44px] px-5 py-2.5 bg-green-50 border-2 border-green-200 text-green-700 rounded-lg hover:bg-green-100 transition disabled:cursor-not-allowed">
        <span class="font-semibold text-sm">I know it</span>
        <span class="block text-xs opacity-70 mt-0.5">I could explain this</span>
        <span v-if="projectedIntervals" class="block text-[10px] font-mono opacity-60 mt-0.5">{{ projectedIntervals['5'] }}</span>
      </button>
    </div>
    <p class="text-xs text-gray-400 mt-3">Press 1, 2, or 3</p>
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
