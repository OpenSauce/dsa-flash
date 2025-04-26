<script setup lang="ts">
import { ref, computed } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import { useCookie } from '#imports'

// Routing + auth
const route = useRoute()
const category = route.params.slug as string
const apiBase = useRuntimeConfig().public.apiBase
const token = useCookie('token')
const md: MarkdownIt = new MarkdownIt({
  breaks: true,
  highlight: (str: string, lang: string) => {
    if (lang && hljs.getLanguage(lang)) {
      return `<pre class="hljs"><code class="language-${lang}">` +
        hljs.highlight(str, { language: lang }).value +
        `</code></pre>`;
    }
    return `<pre class="hljs"><code>` +
      hljs.highlightAuto(str).value +
      `</code></pre>`;
  }
})

// Optional language selector
const categoryHasLang = computed(() => category !== 'big-o-notation')
const language = ref<string | null>(categoryHasLang.value ? 'go' : null)

// Build the “next card” endpoint URL
const url = computed(() => {
  const qs = new URLSearchParams({ category })
  if (language.value) qs.append('language', language.value)
  return `${apiBase}/flashcards?${qs.toString()}`
})

// Fetch exactly one card
const { data: cards, pending, error, refresh } = await useFetch<
  { id: number; front: string; back: string }[]
>(url, {
  headers: token.value
    ? { Authorization: `Bearer ${token.value}` }
    : {}
})

// Single card
const card = computed(() => cards.value?.[0] ?? null)

// Reveal state
const revealed = ref(false)

// Reset “revealed” whenever a new card arrives
watch(card, () => {
  revealed.value = false
})

// SM-2 grading map
const qualityMap = { easy: 5, good: 3, again: 1 } as const

async function recordResponse(grade: keyof typeof qualityMap) {
  if (!card.value) return

  try {
    await $fetch(`${apiBase}/flashcards/${card.value.id}/review`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token.value && { Authorization: `Bearer ${token.value}` }),
      },
      body: { quality: qualityMap[grade] },
    })
    // wait for the new next-card to load
    await refresh()
  } catch (err) {
    console.error('review failed', err)
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto p-6">
    <NuxtLink to="/" class="text-blue-600 hover:underline mb-4 inline-block">
      ← Back to categories
    </NuxtLink>

    <!-- error -->
    <div v-if="error" class="text-red-500">
      ❌ {{ error.data?.detail || error }}
    </div>

    <!-- no card available -->
    <div v-else-if="!card" class="text-center py-12">
      No cards due right now.
    </div>

    <!-- card UI -->
    <div v-else>
      <div @click="revealed = !revealed"
        class="border rounded-xl p-8 shadow-sm mb-6 cursor-pointer select-none transition duration-300 ease-in-out prose mx-auto"
        :class="{
          'bg-white hover:bg-gray-50': !revealed,
          'bg-amber-50 ring-2 ring-amber-400 text-center': revealed,
        }" v-html="revealed ? md.render(card.back) : md.render(card.front)" />

      <div v-if="revealed" class="flex justify-center gap-4">
        <button @click="recordResponse('easy')" class="px-4 py-2 bg-green-600 text-white rounded">
          I know it
        </button>
        <button @click="recordResponse('good')" class="px-4 py-2 bg-yellow-500 text-white rounded">
          Almost
        </button>
        <button @click="recordResponse('again')" class="px-4 py-2 bg-red-600 text-white rounded">
          Forgotten
        </button>
      </div>
    </div>
  </div>
</template>
