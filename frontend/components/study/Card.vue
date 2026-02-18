<script setup lang="ts">
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'

defineProps<{
  front: string
  back: string
  revealed: boolean
}>()

defineEmits<{
  (e: 'flip'): void
}>()

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
  <div @click="$emit('flip')"
    class="border rounded-xl p-8 shadow-sm mb-6 cursor-pointer select-none transition duration-300 ease-in-out prose mx-auto"
    :class="{
      'bg-white hover:bg-gray-50': !revealed,
      'bg-amber-50 ring-2 ring-amber-400': revealed,
    }"
    v-html="revealed ? md.render(back) : md.render(front)" />
</template>
