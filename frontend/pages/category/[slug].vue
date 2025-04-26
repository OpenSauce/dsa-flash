<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import { useCookie } from '#imports'

/* ─── runtime + routing ──────────────────────────────────────── */
const route = useRoute()
const apiBase = useRuntimeConfig().public.apiBase
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

const category = route.params.slug as string
if (!category) throw createError({ statusCode: 404, statusMessage: 'Category not found' })

/* ─── reactive state ─────────────────────────────────────────── */
const categoryHasLang = computed(() => category !== 'big-o-notation')
const language = ref(categoryHasLang.value ? 'go' : null)
const page = ref(1)
const pageSize = 20

interface Flashcard {
  id: number
  front: string
  back: string
}

/* url & key as computeds so they stay in‑sync */
const url = computed(() => {
  const qs = new URLSearchParams({
    category,
    page: String(page.value),
    page_size: String(pageSize),
    //random: "true",
  })
  if (language.value) qs.append('language', language.value)
  return `${apiBase}/flashcards?${qs.toString()}`
})
console.log('[flashcard] apiBase =', apiBase, '| full url =', url.value)
const fetchKey = computed(() =>
  `flashcards-${category}-${language.value}-${page.value}`
)

const token = useCookie('token')

const { data: cards, pending, error, refresh } = await useFetch<Flashcard[]>(url, {
  key: fetchKey.value,      // plain string
  server: true,
  headers: token.value
    ? { Authorization: `Bearer ${token.value}` }
    : {}
})

/* refresh when language or page changes */
watch([language, page], () => refresh())

/* ─── flash‑card player state ───────────────────────────────── */
const index = ref(0)
const revealed = ref(false)

/* currentCard is null until data is ready */
const currentCard = computed(() =>
  cards.value?.length ? cards.value[index.value] : null
)

/* reset index/revealed whenever cards batch changes */
watch(cards, () => {
  index.value = 0
  revealed.value = false
})

function nextCard() {
  if (!currentCard.value) return
  revealed.value = false
  if (cards.value && index.value < cards.value?.length - 1) {
    index.value += 1
  } else {
    page.value += 1        // auto‑advance page
  }
}
const frontHtml = computed(() =>
  currentCard.value ? md.render(currentCard.value.front) : ''
)
const backHtml = computed(() =>
  currentCard.value ? md.render(currentCard.value.back) : ''
)

const qualityMap: Record<'easy' | 'good' | 'again', number> = {
  easy: 5,          // perfect recall
  good: 3,          // got it with effort
  again: 1,         // wrong / forgot
}

async function recordResponse(grade: 'easy' | 'good' | 'again') {
  if (!currentCard.value) return
  const quality = qualityMap[grade]

  try {
    await $fetch(`${apiBase}/flashcards/${currentCard.value.id}/review`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token.value ? { Authorization: `Bearer ${token.value}` } : {}),
      },
      body: { quality },
    })
  } catch (err) {
    console.error('review failed', err)
  }

  nextCard()
}
</script>

<template>
  <div class="max-w-4xl mx-auto p-6">
    <NuxtLink to="/" class="text-blue-600 hover:underline mb-4 inline-block">← Back to categories</NuxtLink>

    <!-- Title + language selector -->
    <div class="flex flex-wrap items-center justify-between mb-6 gap-4">
      <h1 class="text-3xl font-bold capitalize">{{ category.replace(/-/g, ' ') }}</h1>

      <select v-if="categoryHasLang" v-model="language" class="border rounded py-1 px-2 bg-white text-sm">
        <option value="go">Go</option>
        <!-- plug more options later -->
      </select>
    </div>

    <!-- states -->
    <div v-if="pending">Loading flashcards…</div>
    <div v-else-if="error" class="text-red-500">❌ {{ error.data?.detail || error }}</div>
    <div v-else-if="!currentCard">No flashcards found.</div>

    <!-- flash‑card player -->
    <div v-else>
      <div @click="revealed = !revealed"
        class="border rounded-xl p-8 shadow-sm mb-6 cursor-pointer select-none transition duration-300 ease-in-out prose mx-auto"
        :class="{
          'bg-white hover:bg-gray-50': !revealed,
          'bg-amber-50 ring-2 ring-amber-400 text-center': revealed,  // 👈 only center on back
        }" v-html="revealed ? backHtml : frontHtml" />

      <div v-if="revealed" class="flex flex-wrap gap-3 justify-center mt-4">
        <button @click="recordResponse('easy')"
          class="bg-emerald-600 hover:bg-emerald-700 text-white rounded px-4 py-2">
          I&nbsp;know&nbsp;it
        </button>
        <button @click="recordResponse('good')" class="bg-yellow-500 hover:bg-yellow-600 text-white rounded px-4 py-2">
          Almost
        </button>
        <button @click="recordResponse('again')" class="bg-red-600 hover:bg-red-700 text-white rounded px-4 py-2">
          Forgotten
        </button>
      </div>
    </div>
  </div>
</template>
