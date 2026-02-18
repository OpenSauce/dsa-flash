import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import type { Ref, ComputedRef } from 'vue'
import { getCategoryDisplayName } from '@/utils/categoryMeta'

interface StudyCard {
  id: number
  front: string
  back: string
}

interface CategoryAPIItem {
  slug: string
  has_language: boolean
  new: number | null
  due: number | null
  learned: number | null
  total: number
}

interface UseStudySessionOptions {
  category: string
  apiBase: string
  isLoggedIn: Ref<boolean>
  tokenCookie: Ref<string | null>
  track: (event: string, payload: Record<string, unknown>) => void
  flushBeacon: () => void
  refreshStreak: () => void
  logout: () => Promise<void>
  mode: Ref<string>
}

interface UseStudySessionReturn {
  cards: Ref<StudyCard[] | null>
  pending: Ref<boolean>
  error: Ref<any>
  language: Ref<string | null>
  card: ComputedRef<StudyCard | null>
  sessionFinished: Ref<boolean>
  cardsReviewedInBatch: Ref<number>
  cardsReviewedInSession: Ref<number>
  currentBatchSize: Ref<number>
  remainingCards: ComputedRef<number>
  hasMoreCards: ComputedRef<boolean>
  progressPercent: ComputedRef<number>
  revealed: Ref<boolean>
  buttonsEnabled: Ref<boolean>
  isSubmitting: Ref<boolean>
  categoryDisplayName: string
  categoryLearnedCount: Ref<number>
  categoryTotal: Ref<number>
  newConceptsInSession: ComputedRef<number>
  reviewedConceptsInSession: ComputedRef<number>
  mode: Ref<string>
  flipCard: () => void
  nextCard: () => void
  recordResponse: (grade: 'again' | 'good' | 'easy') => Promise<void>
  keepGoing: () => void
  finishSession: (reason: 'completed' | 'user_ended') => void
}

export async function useStudySession(options: UseStudySessionOptions): Promise<UseStudySessionReturn> {
  const { category, apiBase, isLoggedIn, tokenCookie, track, flushBeacon, refreshStreak, logout, mode } = options

  // Optional language selector — determined from categories API
  const language = ref<string | null>(null)

  // Category metadata captured at session start
  const categoryLearnedCount = ref(0)
  const categoryTotal = ref(0)
  const categoryNewCount = ref(0)
  const categoryDueCount = ref(0)

  const { data: categoriesData } = await useFetch<CategoryAPIItem[]>(
    `${apiBase}/categories`
  )
  if (categoriesData.value) {
    const match = categoriesData.value.find(c => c.slug === category)
    if (match) {
      language.value = match.has_language ? 'go' : null
      categoryLearnedCount.value = match.learned ?? 0
      categoryTotal.value = match.total ?? 0
      categoryNewCount.value = match.new ?? 0
      categoryDueCount.value = match.due ?? 0
    }
  }

  const categoryDisplayName = getCategoryDisplayName(category)

  // Build the "next card" endpoint URL
  const url = computed(() => {
    const qs = new URLSearchParams({ category })
    if (language.value) qs.append('language', language.value)
    if (isLoggedIn.value && mode.value !== 'all') {
      qs.append('mode', mode.value)
    }
    return `${apiBase}/flashcards?${qs.toString()}`
  })

  // Fetch cards (headers as getter so refresh() picks up token changes)
  const { data: cards, pending, error, refresh } = await useFetch<StudyCard[]>(url, {
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
      if (mode.value === 'due') {
        currentBatchSize.value = newCards.length
      } else {
        currentBatchSize.value = Math.min(BATCH_SIZE, newCards.length)
      }
    }
  }, { immediate: true })

  // Reset batch state when mode changes
  watch(mode, () => {
    cardsReviewedInBatch.value = 0
    currentBatchSize.value = 0
    sessionFinished.value = false
    cardIndex.value = 0
    cards.value = []
  })

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

  // Analytics timing
  const frontShownAt = ref(Date.now())
  const flipTime = ref(0)
  const sessionStartTime = Date.now()
  const cardsReviewedInSession = ref(0)
  let sessionEndEmitted = false

  // New vs reviewed breakdown: ratio-based estimate from initial category stats.
  // This is approximate — the backend serves a mixed queue so we can't know per-card
  // whether it was new or due without a server-side session. Task 5 (session modes)
  // will make this exact once the API distinguishes new from review cards.
  const newConceptsInSession = computed(() => {
    const total = categoryNewCount.value + categoryDueCount.value
    if (total === 0) return 0
    return Math.round(cardsReviewedInSession.value * categoryNewCount.value / total)
  })

  const reviewedConceptsInSession = computed(() =>
    cardsReviewedInSession.value - newConceptsInSession.value
  )

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

  onMounted(() => {
    track('page_view', { page: `/category/${category}`, referrer: document.referrer })
    track('session_start', { category })
    window.addEventListener('beforeunload', handleBeforeUnload)
    window.addEventListener('keydown', handleKeydown)
  })

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
    if (mode.value === 'due') {
      currentBatchSize.value = cards.value?.length ?? 0
    } else if (isLoggedIn.value) {
      currentBatchSize.value = Math.min(BATCH_SIZE, cards.value?.length ?? 0)
    } else {
      const remaining = (cards.value?.length ?? 0) - cardIndex.value
      currentBatchSize.value = Math.min(BATCH_SIZE, remaining)
    }
    revealed.value = false
    frontShownAt.value = Date.now()
  }

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

  return {
    cards,
    pending,
    error,
    language,
    card,
    sessionFinished,
    cardsReviewedInBatch,
    cardsReviewedInSession,
    currentBatchSize,
    remainingCards,
    hasMoreCards,
    progressPercent,
    revealed,
    buttonsEnabled,
    isSubmitting,
    categoryDisplayName,
    categoryLearnedCount,
    categoryTotal,
    newConceptsInSession,
    reviewedConceptsInSession,
    mode,
    flipCard,
    nextCard,
    recordResponse,
    keepGoing,
    finishSession,
  }
}
