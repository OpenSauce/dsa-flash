<script setup lang="ts">
import type { TestResult } from '@/types/problem'

defineProps<{
  results: TestResult[]
  passed: boolean
  solveTime?: number | null
}>()

function formatTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}
</script>

<template>
  <div class="space-y-3">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <span
          class="inline-flex items-center gap-1 text-sm font-semibold"
          :class="passed ? 'text-green-600' : 'text-red-600'"
        >
          <svg v-if="passed" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
          {{ passed ? 'All tests passed' : 'Tests failed' }}
        </span>
        <span class="text-xs text-gray-400">
          {{ results.filter(r => r.passed).length }}/{{ results.length }}
        </span>
      </div>
      <span v-if="solveTime != null" class="text-xs text-gray-500 font-mono">
        Solved in {{ formatTime(solveTime) }}
      </span>
    </div>

    <div
      v-for="(result, i) in results"
      :key="i"
      class="rounded-md border p-3 text-sm font-mono"
      :class="result.passed ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'"
    >
      <div class="flex items-center gap-2 mb-1">
        <span
          class="w-2 h-2 rounded-full flex-shrink-0"
          :class="result.passed ? 'bg-green-500' : 'bg-red-500'"
        />
        <span class="text-xs font-semibold" :class="result.passed ? 'text-green-700' : 'text-red-700'">
          Test {{ i + 1 }} — {{ result.passed ? 'Passed' : 'Failed' }}
        </span>
      </div>
      <div class="ml-4 space-y-0.5 text-xs">
        <div><span class="text-gray-500">Input:</span> {{ result.input }}</div>
        <div><span class="text-gray-500">Expected:</span> {{ result.expected }}</div>
        <div v-if="!result.passed"><span class="text-gray-500">Actual:</span> <span class="text-red-600">{{ result.actual }}</span></div>
      </div>
    </div>
  </div>
</template>
