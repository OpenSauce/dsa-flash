<script setup lang="ts">
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'

defineProps<{
  front: string
  back: string
  revealed: boolean
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

const md: MarkdownIt = new MarkdownIt({
  breaks: true,
  highlight: (str: string, lang: string) => {
    if (lang && hljs.getLanguage(lang)) {
      return `<pre class="hljs"><code class="language-${lang}">` +
        hljs.highlight(str, { language: lang }).value +
        `</code></pre>`
    }
    return `<pre class="hljs"><code>` +
      hljs.highlightAuto(str).value +
      `</code></pre>`
  }
}).disable('html_inline').disable('html_block')
</script>

<template>
  <div @pointerdown="onPointerDown" @click="onClickCard"
    class="border rounded-xl p-4 sm:p-8 shadow-sm mb-6 cursor-pointer transition duration-300 ease-in-out prose max-w-none sm:max-w-prose mx-auto overflow-hidden"
    :class="{
      'bg-white hover:bg-gray-50': !revealed,
      'bg-amber-50 ring-2 ring-amber-400': revealed,
    }"
    v-html="revealed ? md.render(back) : md.render(front)" />
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
