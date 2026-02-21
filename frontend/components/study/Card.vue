<script setup lang="ts">
import { useMarkdown } from '@/composables/useMarkdown'

defineProps<{
  front: string
  back: string
  revealed: boolean
  showFlipHint?: boolean
}>()

const emit = defineEmits<{
  (e: 'flip'): void
}>()

// Only flip on clean clicks — ignore if the user dragged to select text
let startX = 0
let startY = 0
function onPointerDown(e: PointerEvent) {
  startX = e.clientX
  startY = e.clientY
}
function onClickCard(e: MouseEvent) {
  const dx = e.clientX - startX
  const dy = e.clientY - startY
  if (Math.abs(dx) + Math.abs(dy) > 10 || window.getSelection()?.toString()) return
  emit('flip')
}

const md = useMarkdown()
</script>

<template>
  <div
    @pointerdown="onPointerDown"
    @click="onClickCard"
    class="border rounded-xl p-4 sm:p-8 shadow-sm mb-6 cursor-pointer transition duration-300 ease-in-out max-w-none sm:max-w-prose mx-auto overflow-hidden"
    :class="{
      'bg-white hover:bg-gray-50': !revealed,
      'bg-amber-50 ring-2 ring-amber-400': revealed,
    }"
  >
    <div class="prose max-w-none" v-html="revealed ? md.render(back) : md.render(front)" />

    <!-- Full discoverability hint: shown to first-time users (before first flip) -->
    <div
      v-if="!revealed && showFlipHint"
      class="mt-4 pt-3 border-t border-gray-100 text-center text-sm text-gray-400 select-none"
    >
      <span class="inline-flex items-center gap-1.5">
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M17 1l4 4-4 4" /><path d="M3 11V9a4 4 0 014-4h14" />
          <path d="M7 23l-4-4 4-4" /><path d="M21 13v2a4 4 0 01-4 4H3" />
        </svg>
        Tap to reveal answer
      </span>
      <span class="hidden sm:block text-xs text-gray-300 mt-1">or press Space</span>
    </div>

    <!-- Subtle icon: shown when card is not yet revealed and hint is hidden (returning users) -->
    <div
      v-else-if="!revealed"
      class="mt-4 text-center select-none"
    >
      <svg class="w-4 h-4 inline text-gray-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="Flip card">
        <path d="M17 1l4 4-4 4" /><path d="M3 11V9a4 4 0 014-4h14" />
        <path d="M7 23l-4-4 4-4" /><path d="M21 13v2a4 4 0 01-4 4H3" />
      </svg>
    </div>
  </div>
</template>

<style scoped>
.prose :deep(pre) {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.prose :deep(code) {
  word-break: break-word;
}
.prose :deep(pre code) {
  word-break: normal;
}
</style>
