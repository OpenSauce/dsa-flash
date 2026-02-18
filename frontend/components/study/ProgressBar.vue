<script setup lang="ts">
defineProps<{
  current: number
  total: number
  percent: number
  mode?: string
}>()
</script>

<template>
  <div class="mb-4">
    <div class="flex justify-between text-sm text-gray-500 mb-1">
      <span>Card {{ current + 1 }} of {{ total }}</span>
    </div>
    <div class="w-full bg-gray-200 rounded-full h-2">
      <div class="h-2 rounded-full transition-all duration-300"
           :class="mode === 'new' ? 'bg-green-500' : 'bg-indigo-500'"
           role="progressbar"
           :aria-valuenow="current"
           aria-valuemin="0"
           :aria-valuemax="total"
           :aria-label="`Card ${current + 1} of ${total} reviewed`"
           :style="{ width: percent + '%' }" />
    </div>
  </div>
</template>
