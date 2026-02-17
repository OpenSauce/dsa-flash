<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import { useAnalytics } from '@/composables/useAnalytics'

// Routing + auth
const route = useRoute()
const category = route.params.slug as string
const apiBase = useRuntimeConfig().public.apiBase
const { isLoggedIn, tokenCookie, logout } = useAuth()
const { refreshStreak } = useStreak()
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
}).disable('html_inline').disable('html_block')

// Optional language selector — determined from categories API
const categoryHasLang = ref(false)
const language = ref<string | null>(null)

const { data: categoriesData } = await useFetch<{ slug: string; has_language: boolean }[]>(
  `${apiBase}/categories`
)
if (categoriesData.value) {
  const match = categoriesData.value.find(c => c.slug === category)
  if (match) {
    categoryHasLang.value = match.has_language
    language.value = match.has_language ? 'go' : null
  }
}

// Build the "next card" endpoint URL
const url = computed(() => {
  const qs = new URLSearchParams({ category })
  if (language.value) qs.append('language', language.value)
  return `${apiBase}/flashcards?${qs.toString()}`
})

// Fetch cards (headers as getter so refresh() picks up token changes)
const { data: cards, pending, error, refresh } = await useFetch<
  { id: number; front: string; back: string }[]
>(url, {
  headers: () => tokenCookie.value
    ? { Authorization: `Bearer ${tokenCookie.value}` }
    : {},
})

// Card navigation — anonymous users browse by index, logged-in users use SM-2 refresh
const cardIndex = ref(0)

// Batch session state
const BATCH_SIZE = 10
const cardsReviewedInBatch = ref(0)
const sessionFinished = ref(false)
const currentBatchSize = ref(0)

watch(cards, (newCards) => {
  if (newCards && currentBatchSize.value === 0) {
    currentBatchSize.value = Math.min(BATCH_SIZE, newCards.length)
  }
}, { immediate: true })

const progressPercent = computed(() =>
  currentBatchSize.value > 0
    ? (cardsReviewedInBatch.value / currentBatchSize.value) * 100
    : 0
)

const remainingCards = computed(() => {
  if (isLoggedIn.value) return cards.value?.length ?? 0
  return (cards.value?.length ?? 0) - cardIndex.value
})

const hasMoreCards = computed(() => remainingCards.value > 0)

const card = computed(() => {
  if (sessionFinished.value) return null
  if (isLoggedIn.value) return cards.value?.[0] ?? null
  return cards.value?.[cardIndex.value] ?? null
})

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
  window.addEventListener('keydown', handleKeydown)
})

// Reveal state
const revealed = ref(false)
const buttonsEnabled = ref(false)
let buttonsTimer: ReturnType<typeof setTimeout> | null = null

function flipCard() {
  revealed.value = !revealed.value
  if (revealed.value) {
    flipTime.value = Date.now()
    track('card_flip', {
      card_id: card.value?.id,
      category,
      time_on_front_ms: Date.now() - frontShownAt.value,
    })
    // 400ms delay before buttons become clickable
    buttonsEnabled.value = false
    buttonsTimer = setTimeout(() => {
      buttonsEnabled.value = true
    }, 400)
  } else {
    buttonsEnabled.value = false
    if (buttonsTimer) {
      clearTimeout(buttonsTimer)
      buttonsTimer = null
    }
  }
}

// Keyboard shortcuts
function handleKeydown(e: KeyboardEvent) {
  if (e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return
  if (!(e.target instanceof Element)) return
  if (e.target.closest('button,a,input,textarea,select,[role="button"],[contenteditable]')) return
  if (!card.value || sessionFinished.value) return

  if (!revealed.value) {
    if (e.code === 'Space' || e.code === 'Enter') {
      e.preventDefault()
      flipCard()
    }
  } else {
    if (isLoggedIn.value) {
      if (e.key === '1') { e.preventDefault(); if (buttonsEnabled.value) recordResponse('again') }
      else if (e.key === '2') { e.preventDefault(); if (buttonsEnabled.value) recordResponse('good') }
      else if (e.key === '3') { e.preventDefault(); if (buttonsEnabled.value) recordResponse('easy') }
    } else {
      if (e.key === '1' || e.key === '2' || e.key === '3' || e.code === 'Space' || e.code === 'Enter') {
        e.preventDefault()
        nextCard()
      }
    }
  }
}

// Anonymous: advance to next card without review
function nextCard() {
  cardsReviewedInSession.value++
  cardsReviewedInBatch.value++
  cardIndex.value++
  revealed.value = false
  frontShownAt.value = Date.now()
  if (cardsReviewedInBatch.value >= currentBatchSize.value) {
    sessionFinished.value = true
  }
  if (!cards.value?.[cardIndex.value]) {
    emitSessionEnd('completed')
  }
}

// Reset "revealed" whenever a new card arrives (for logged-in refresh flow)
watch(card, (newCard) => {
  if (isLoggedIn.value) {
    revealed.value = false
    buttonsEnabled.value = false
    if (buttonsTimer) { clearTimeout(buttonsTimer); buttonsTimer = null }
    frontShownAt.value = Date.now()
  }
  if (!newCard && !sessionFinished.value) {
    finishSession('completed')
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
  window.removeEventListener('keydown', handleKeydown)
  if (buttonsTimer) clearTimeout(buttonsTimer)
  emitSessionEnd('navigated_away')
})

function finishSession(reason: 'completed' | 'user_ended') {
  emitSessionEnd(reason)
  if (cardsReviewedInSession.value === 0) {
    navigateTo('/')
    return
  }
  sessionFinished.value = true
}

function keepGoing() {
  track('keep_going', { category, cards_reviewed: cardsReviewedInSession.value })
  cardsReviewedInBatch.value = 0
  sessionFinished.value = false
  if (isLoggedIn.value) {
    currentBatchSize.value = Math.min(BATCH_SIZE, cards.value?.length ?? 0)
  } else {
    const remaining = (cards.value?.length ?? 0) - cardIndex.value
    currentBatchSize.value = Math.min(BATCH_SIZE, remaining)
  }
  revealed.value = false
  frontShownAt.value = Date.now()
}


// SM-2 grading map
const qualityMap = { easy: 5, good: 3, again: 1 } as const
const isSubmitting = ref(false)

async function recordResponse(grade: keyof typeof qualityMap) {
  if (!card.value || isSubmitting.value) return
  isSubmitting.value = true

  const now = Date.now()
  track('card_review', {
    card_id: card.value.id,
    category,
    grade,
    quality: qualityMap[grade],
    time_on_back_ms: now - flipTime.value,
    time_total_ms: now - frontShownAt.value,
  })
  try {
    await $fetch(`${apiBase}/flashcards/${card.value.id}/review`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(tokenCookie.value && { Authorization: `Bearer ${tokenCookie.value}` }),
      },
      body: { quality: qualityMap[grade] },
    })
    cardsReviewedInSession.value++
    cardsReviewedInBatch.value++
    if (cardsReviewedInBatch.value >= currentBatchSize.value) {
      sessionFinished.value = true
    }
    await refresh()
    refreshStreak()
  } catch (err: any) {
    if (err?.response?.status === 401 || err?.status === 401 || err?.statusCode === 401) {
      await logout()
      navigateTo('/')
    } else {
      console.error('review failed', err)
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto p-6">
    <button v-if="card" @click="finishSession('user_ended')" class="text-blue-600 hover:underline mb-4 inline-block">
      Stop reviewing
    </button>

    <!-- error -->
    <div v-if="error" class="text-red-500">
      {{ error.data?.detail || error }}
    </div>

    <!-- completion / empty state -->
    <div v-else-if="sessionFinished || !card" class="text-center py-16">
      <template v-if="cardsReviewedInSession > 0">
        <h2 class="text-2xl font-bold mb-2 font-heading">Batch complete!</h2>
        <p class="text-gray-600 mb-2">You reviewed {{ cardsReviewedInSession }} cards</p>
        <p v-if="remainingCards > 0" class="text-gray-500 text-sm mb-8">{{ remainingCards }} cards remaining in this category</p>
        <p v-else-if="isLoggedIn" class="text-gray-500 text-sm mb-8">Come back tomorrow for your next review</p>
        <p v-else class="text-gray-500 text-sm mb-8">You've seen all the cards in this category!</p>
        <div class="flex justify-center gap-4">
          <NuxtLink to="/" class="px-6 py-2 border border-gray-300 rounded hover:bg-gray-50">
            &larr; Back to categories
          </NuxtLink>
          <button v-if="hasMoreCards" @click="keepGoing()"
                  class="px-6 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700">
            Keep going
          </button>
        </div>
      </template>
      <template v-else>
        <p class="text-gray-500">No cards due right now.</p>
        <NuxtLink to="/" class="text-blue-600 hover:underline mt-4 inline-block">
          &larr; Back to categories
        </NuxtLink>
      </template>
    </div>

    <!-- card UI -->
    <div v-else>
      <!-- Anonymous: progress not saved notice -->
      <div v-if="!isLoggedIn"
           class="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
        Your progress won't be saved.
        <NuxtLink to="/signup" class="underline font-medium">Sign up</NuxtLink> to track your learning.
      </div>

      <!-- Progress bar -->
      <div class="mb-4">
        <div class="flex justify-between text-sm text-gray-500 mb-1">
          <span>Card {{ cardsReviewedInBatch + 1 }} of {{ currentBatchSize }}</span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2">
          <div class="bg-indigo-500 h-2 rounded-full transition-all duration-300"
               role="progressbar"
               :aria-valuenow="cardsReviewedInBatch"
               aria-valuemin="0"
               :aria-valuemax="currentBatchSize"
               :aria-label="`Card ${cardsReviewedInBatch} of ${currentBatchSize} reviewed`"
               :style="{ width: progressPercent + '%' }" />
        </div>
      </div>

      <div @click="flipCard()"
        class="border rounded-xl p-8 shadow-sm mb-6 cursor-pointer select-none transition duration-300 ease-in-out prose mx-auto"
        :class="{
          'bg-white hover:bg-gray-50': !revealed,
          'bg-amber-50 ring-2 ring-amber-400': revealed,
        }" v-html="revealed ? md.render(card.back) : md.render(card.front)" />

      <!-- Logged-in: review buttons -->
      <div v-if="revealed && isLoggedIn" class="text-center">
        <div class="flex justify-center gap-4 rating-buttons" :class="{ 'rating-buttons--visible': buttonsEnabled }">
          <button @click="buttonsEnabled && recordResponse('again')"
                  :disabled="!buttonsEnabled"
                  class="px-5 py-3 bg-red-600 text-white rounded-lg transition-opacity disabled:cursor-not-allowed">
            <span class="font-semibold">Again</span>
            <span class="block text-xs opacity-80 mt-0.5">Review again soon</span>
          </button>
          <button @click="buttonsEnabled && recordResponse('good')"
                  :disabled="!buttonsEnabled"
                  class="px-5 py-3 bg-yellow-500 text-white rounded-lg transition-opacity disabled:cursor-not-allowed">
            <span class="font-semibold">Almost</span>
            <span class="block text-xs opacity-80 mt-0.5">Review later</span>
          </button>
          <button @click="buttonsEnabled && recordResponse('easy')"
                  :disabled="!buttonsEnabled"
                  class="px-5 py-3 bg-green-600 text-white rounded-lg transition-opacity disabled:cursor-not-allowed">
            <span class="font-semibold">I know it</span>
            <span class="block text-xs opacity-80 mt-0.5">I could explain this</span>
          </button>
        </div>
        <p class="text-xs text-gray-400 mt-3">Press 1, 2, or 3</p>
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

<style scoped>
.rating-buttons {
  opacity: 0;
  transition: opacity 400ms ease-out;
}
.rating-buttons--visible {
  opacity: 1;
}
</style>
