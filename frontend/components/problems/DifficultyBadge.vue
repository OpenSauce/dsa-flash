<script setup lang="ts">
defineProps<{
  difficulty: 'easy' | 'medium' | 'hard'
}>()

const classes: Record<string, string> = {
  easy: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  hard: 'bg-red-100 text-red-700',
}
</script>

<template>
  <span
    class="inline-block px-2 py-0.5 text-xs font-semibold rounded capitalize"
    :class="classes[difficulty]"
  >
    {{ difficulty }}
  </span>
</template>
