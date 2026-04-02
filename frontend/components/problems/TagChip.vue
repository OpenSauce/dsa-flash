<script setup lang="ts">
defineProps<{
  tag: string
  active?: boolean
}>()

defineEmits<{
  (e: 'click'): void
}>()
</script>

<template>
  <button
    class="inline-block px-2.5 py-1 text-xs font-medium rounded-md border transition-colors duration-100"
    :class="active
      ? 'bg-purple-100 border-purple-300 text-purple-700'
      : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100'"
    @click="$emit('click')"
  >
    {{ tag }}
  </button>
</template>
