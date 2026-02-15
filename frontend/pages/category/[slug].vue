<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import { useCookie } from '#imports'
import { useAnalytics } from '@/composables/useAnalytics'

// Routing + auth
const route = useRoute()
const category = route.params.slug as string
const apiBase = useRuntimeConfig().public.apiBase
const token = useCookie('token')
const isLoggedIn = computed(() => !!token.value)
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

// Build the "next card" endpoint URL
const url = computed(() => {
  const qs = new URLSearchParams({ category })
  if (language.value) qs.append('language', language.value)
  return `${apiBase}/flashcards?${qs.toString()}`
})

// Fetch cards
const { data: cards, pending, error, refresh } = await useFetch<
  { id: number; front: string; back: string }[]
>(url, {
  headers: token.value
    ? { Authorization: `Bearer ${token.value}` }
    : {}
})

// Card navigation — anonymous users browse by index, logged-in users use SM-2 refresh
const cardIndex = ref(0)
const card = computed(() => {
  if (isLoggedIn.value) return cards.value?.[0] ?? null
  return cards.value?.[cardIndex.value] ?? null
})

// Signup CTA for anonymous users
const flipCount = ref(0)
const ctaDismissed = ref(false)
const showSignupCta = computed(
  () => !isLoggedIn.value && flipCount.value >= 5 && !ctaDismissed.value
)

// Analytics
const { track, flushBeacon } = useAnalytics()
const frontShownAt = ref(Date.now())
const flipTime = ref(0)
const sessionStartTime = Date.now()
const cardsReviewedInSession = ref(0)
let sessionEndEmitted = false

function emitSessionEnd(reason: string) {
  if (sessionEndEmitted) return
  sessionEndEmitted = true
  track('session_end', {
    category,
    reason,
    cards_reviewed: cardsReviewedInSession.value,
    duration_ms: Date.now() - sessionStartTime,
  })
}

function handleBeforeUnload() {
  emitSessionEnd('navigated_away')
  flushBeacon()
}

onMounted(() => {
  track('page_view', { page: `/category/${category}`, referrer: document.referrer })
  track('session_start', { category })
  window.addEventListener('beforeunload', handleBeforeUnload)
})

// Reveal state
const revealed = ref(false)

function flipCard() {
  revealed.value = !revealed.value
  if (revealed.value) {
    flipTime.value = Date.now()
    flipCount.value++
    track('card_flip', {
      card_id: card.value?.id,
      category,
      time_on_front_ms: Date.now() - frontShownAt.value,
    })
  }
}

// Anonymous: advance to next card without review
function nextCard() {
  cardsReviewedInSession.value++
  cardIndex.value++
  revealed.value = false
  frontShownAt.value = Date.now()
  if (!cards.value?.[cardIndex.value]) {
    emitSessionEnd('completed')
  }
}

// Reset "revealed" whenever a new card arrives (for logged-in refresh flow)
watch(card, (newCard) => {
  if (isLoggedIn.value) {
    revealed.value = false
    frontShownAt.value = Date.now()
  }
  if (!newCard) {
    emitSessionEnd('completed')
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
  emitSessionEnd('navigated_away')
})

// SM-2 grading map
const qualityMap = { easy: 5, good: 3, again: 1 } as const

async function recordResponse(grade: keyof typeof qualityMap) {
  if (!card.value) return

  const now = Date.now()
  track('card_review', {
    card_id: card.value.id,
    category,
    grade,
    quality: qualityMap[grade],
    time_on_back_ms: now - flipTime.value,
    time_total_ms: now - frontShownAt.value,
  })
  cardsReviewedInSession.value++

  try {
    await $fetch(`${apiBase}/flashcards/${card.value.id}/review`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token.value && { Authorization: `Bearer ${token.value}` }),
      },
      body: { quality: qualityMap[grade] },
    })
    await refresh()
  } catch (err) {
    console.error('review failed', err)
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto p-6">
    <NuxtLink to="/" class="text-blue-600 hover:underline mb-4 inline-block">
      &larr; Back to categories
    </NuxtLink>

    <!-- error -->
    <div v-if="error" class="text-red-500">
      {{ error.data?.detail || error }}
    </div>

    <!-- no card available -->
    <div v-else-if="!card" class="text-center py-12">
      No cards due right now.
    </div>

    <!-- card UI -->
    <div v-else>
      <!-- Signup CTA for anonymous users -->
      <div
        v-if="showSignupCta"
        class="mb-6 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 flex items-center justify-between"
      >
        <p class="text-sm text-blue-800">
          Sign up to save your progress and track what you've learned.
        </p>
        <div class="flex items-center gap-2 ml-4 shrink-0">
          <NuxtLink
            to="/signup"
            class="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
          >
            Sign up
          </NuxtLink>
          <button
            @click="ctaDismissed = true"
            class="text-blue-400 hover:text-blue-600 text-lg leading-none"
            aria-label="Dismiss"
          >
            &times;
          </button>
        </div>
      </div>

      <div @click="flipCard()"
        class="border rounded-xl p-8 shadow-sm mb-6 cursor-pointer select-none transition duration-300 ease-in-out prose mx-auto"
        :class="{
          'bg-white hover:bg-gray-50': !revealed,
          'bg-amber-50 ring-2 ring-amber-400 text-center': revealed,
        }" v-html="revealed ? md.render(card.back) : md.render(card.front)" />

      <!-- Logged-in: review buttons -->
      <div v-if="revealed && isLoggedIn" class="flex justify-center gap-4">
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

      <!-- Anonymous: next card button -->
      <div v-if="revealed && !isLoggedIn" class="flex justify-center">
        <button @click="nextCard()" class="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          Next card &rarr;
        </button>
      </div>
    </div>
  </div>
</template>
