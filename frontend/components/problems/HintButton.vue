<script setup lang="ts">
const props = defineProps<{
  hintsCount: number
  hintsRevealed: number
  loading: boolean
}>()

defineEmits<{
  (e: 'request-hint'): void
}>()

const hasMore = computed(() => {
  return props.hintsRevealed < props.hintsCount
})
</script>

<template>
  <button
    v-if="hintsCount > 0 && hasMore"
    class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-md hover:bg-amber-100 transition-colors duration-100 disabled:opacity-50"
    :disabled="loading"
    @click="$emit('request-hint')"
  >
    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
    </svg>
    <span v-if="!loading">Show Hint ({{ hintsCount - hintsRevealed }} remaining)</span>
    <span v-else>Loading...</span>
  </button>
</template>
