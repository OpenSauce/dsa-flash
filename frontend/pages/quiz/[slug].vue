<script setup lang="ts">
import { getCategoryDisplayName } from '@/utils/categoryMeta'
import { useAuth } from '@/composables/useAuth'

const route = useRoute()
const slug = route.params.slug as string
const { public: { apiBase } } = useRuntimeConfig()
const { tokenCookie } = useAuth()

interface QuizQuestion {
  id: number
  order: number
  question: string
  options: string[]
  correct_index: number
  explanation: string
}

interface QuizDetail {
  id: number
  title: string
  slug: string
  category: string | null
  lesson_slug: string | null
  questions: QuizQuestion[]
}

interface QuizAnswerResult {
  question_id: number
  correct: boolean
  correct_index: number
  explanation: string
}

interface QuizSubmitOut {
  score: number
  total: number
  results: QuizAnswerResult[]
}

const { data: quiz, error } = await useAsyncData<QuizDetail>(
  `quiz-${slug}`,
  () => $fetch<QuizDetail>(`${apiBase}/quizzes/${slug}`),
)

useSeoMeta({
  title: computed(() => quiz.value ? `${quiz.value.title} | dsaflash.cards` : 'Quiz | dsaflash.cards'),
  ogTitle: computed(() => quiz.value ? `${quiz.value.title} | dsaflash.cards` : 'Quiz | dsaflash.cards'),
  description: computed(() => quiz.value ? `Test your knowledge: ${quiz.value.title}` : ''),
  ogDescription: computed(() => quiz.value ? `Test your knowledge: ${quiz.value.title}` : ''),
})

useHead({
  link: computed(() => quiz.value ? [{ rel: 'canonical', href: `https://dsaflash.cards/quiz/${quiz.value.slug}` }] : []),
})

const currentIndex = ref(0)
const answers = ref<Record<number, number>>({})
const selectedForCurrent = ref<number | null>(null)
const showResult = ref(false)
const quizComplete = ref(false)
const submitResult = ref<QuizSubmitOut | null>(null)
const submitting = ref(false)
const retryQuestions = ref<QuizQuestion[]>([])
const inRetryRound = ref(false)
const firstPassAnswers = ref<Record<number, number>>({})

const categoryDisplayName = computed(() =>
  quiz.value?.category ? getCategoryDisplayName(quiz.value.category) : ''
)

const activeQuestions = computed(() =>
  inRetryRound.value ? retryQuestions.value : (quiz.value?.questions ?? [])
)

const currentQuestion = computed(() =>
  activeQuestions.value[currentIndex.value] ?? null
)

const totalQuestions = computed(() => activeQuestions.value.length)

const optionLabels = ['A', 'B', 'C', 'D']

function selectOption(optionIndex: number) {
  if (showResult.value) return
  selectedForCurrent.value = optionIndex
  showResult.value = true
  if (currentQuestion.value) {
    answers.value[currentQuestion.value.id] = optionIndex
  }
}

function isCorrectOption(optionIndex: number): boolean {
  if (!showResult.value || !currentQuestion.value) return false
  return optionIndex === currentQuestion.value.correct_index
}

function isWrongSelected(optionIndex: number): boolean {
  if (!showResult.value || !currentQuestion.value) return false
  return (
    optionIndex === selectedForCurrent.value &&
    optionIndex !== currentQuestion.value.correct_index
  )
}

async function nextQuestion() {
  if (!quiz.value) return

  if (currentIndex.value < activeQuestions.value.length - 1) {
    currentIndex.value++
    selectedForCurrent.value = null
    showResult.value = false
  } else if (!inRetryRound.value) {
    // First pass done — check for missed questions
    const missed = quiz.value.questions.filter(
      q => answers.value[q.id] !== q.correct_index
    )
    if (missed.length > 0) {
      firstPassAnswers.value = { ...answers.value }
      retryQuestions.value = missed
      inRetryRound.value = true
      currentIndex.value = 0
      selectedForCurrent.value = null
      showResult.value = false
    } else {
      await submitQuiz()
    }
  } else {
    // Retry round done
    await submitQuiz()
  }
}

async function submitQuiz() {
  if (!quiz.value) return
  submitting.value = true
  try {
    // Submit first-pass answers for scoring (not retry-corrected ones)
    const scoreAnswers = inRetryRound.value ? firstPassAnswers.value : answers.value
    const answersPayload: Record<string, number> = {}
    for (const [qId, idx] of Object.entries(scoreAnswers)) {
      answersPayload[String(qId)] = idx
    }
    const headers: Record<string, string> = {}
    if (tokenCookie.value) {
      headers['Authorization'] = `Bearer ${tokenCookie.value}`
    }
    const result = await $fetch<QuizSubmitOut>(`${apiBase}/quizzes/${slug}/submit`, {
      method: 'POST',
      body: { answers: answersPayload },
      headers,
    })
    submitResult.value = result
  } catch {
    // non-fatal — show score based on local state
    if (quiz.value) {
      const fallbackAnswers = inRetryRound.value ? firstPassAnswers.value : answers.value
      const results: QuizAnswerResult[] = quiz.value.questions.map(q => {
        const selected = fallbackAnswers[q.id]
        return {
          question_id: q.id,
          correct: selected === q.correct_index,
          correct_index: q.correct_index,
          explanation: q.explanation || '',
        }
      })
      const score = results.filter(r => r.correct).length
      submitResult.value = { score, total: quiz.value.questions.length, results }
    }
  } finally {
    submitting.value = false
    quizComplete.value = true
  }
}

function tryAgain() {
  currentIndex.value = 0
  answers.value = {}
  selectedForCurrent.value = null
  showResult.value = false
  quizComplete.value = false
  submitResult.value = null
  submitting.value = false
  retryQuestions.value = []
  inRetryRound.value = false
  firstPassAnswers.value = {}
}

function resultForQuestion(questionId: number): QuizAnswerResult | undefined {
  return submitResult.value?.results.find(r => r.question_id === questionId)
}
</script>

<template>
  <div class="max-w-3xl mx-auto px-4 sm:px-6 pb-16">

    <div v-if="error" class="text-center text-red-500 py-16">
      Quiz not found. <NuxtLink to="/" class="underline text-blue-600">Back to home</NuxtLink>
    </div>

    <template v-else-if="quiz">
      <!-- Breadcrumb -->
      <nav class="text-sm text-gray-500 mb-6 pt-2">
        <NuxtLink to="/" class="hover:text-gray-700">Home</NuxtLink>
        <span class="mx-2">/</span>
        <NuxtLink
          v-if="quiz.category"
          :to="`/category/${quiz.category}`"
          class="hover:text-gray-700"
        >{{ categoryDisplayName }}</NuxtLink>
        <span v-if="quiz.category" class="mx-2">/</span>
        <span class="text-gray-700">{{ quiz.title }}</span>
      </nav>

      <!-- Score summary screen -->
      <template v-if="quizComplete && submitResult">
        <div class="text-center py-8">
          <div class="inline-flex items-center justify-center w-20 h-20 rounded-full mb-4"
            :class="submitResult.score === submitResult.total
              ? 'bg-green-100 text-green-700'
              : submitResult.score >= submitResult.total / 2
                ? 'bg-yellow-100 text-yellow-700'
                : 'bg-red-100 text-red-700'"
          >
            <span class="text-2xl font-bold">{{ submitResult.score }}/{{ submitResult.total }}</span>
          </div>
          <h1 class="text-2xl font-bold text-gray-900 mb-2">
            {{ submitResult.score === submitResult.total ? 'Perfect score!' : `You got ${submitResult.score} of ${submitResult.total} correct` }}
          </h1>
          <p class="text-gray-500 text-sm mb-8">
            {{ submitResult.score === submitResult.total
              ? 'Excellent work — you nailed every question.'
              : submitResult.score >= submitResult.total / 2
                ? 'Good effort! Review the ones you missed below.'
                : 'Keep studying and try again!' }}
          </p>

          <!-- Per-question review -->
          <div class="text-left space-y-4 mb-8">
            <div
              v-for="(q, idx) in quiz.questions"
              :key="q.id"
              class="border rounded-xl p-4"
              :class="resultForQuestion(q.id)?.correct ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'"
            >
              <div class="flex items-start gap-3">
                <span class="mt-0.5 flex-shrink-0">
                  <svg v-if="resultForQuestion(q.id)?.correct" class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  <svg v-else class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </span>
                <div class="flex-1">
                  <p class="font-medium text-gray-900 mb-1">{{ idx + 1 }}. {{ q.question }}</p>
                  <p class="text-sm text-gray-600 mb-1">
                    Correct answer: <span class="font-medium">{{ optionLabels[q.correct_index] }}. {{ q.options[q.correct_index] }}</span>
                  </p>
                  <p v-if="resultForQuestion(q.id)?.explanation" class="text-sm text-gray-500 italic">
                    {{ resultForQuestion(q.id)?.explanation }}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- CTAs -->
          <div class="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              @click="tryAgain"
              class="px-6 py-3 border border-gray-300 text-gray-700 font-semibold rounded-xl hover:bg-gray-50 transition"
            >
              Try again
            </button>
            <NuxtLink
              v-if="quiz.lesson_slug"
              :to="`/lesson/${quiz.lesson_slug}`"
              class="px-6 py-3 border border-indigo-300 text-indigo-700 font-semibold rounded-xl hover:bg-indigo-50 transition text-center"
            >
              Back to lesson
            </NuxtLink>
            <NuxtLink
              v-if="quiz.category"
              :to="`/category/${quiz.category}`"
              class="px-6 py-3 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition text-center"
            >
              Review with flashcards
            </NuxtLink>
          </div>
        </div>
      </template>

      <!-- Quiz in progress -->
      <template v-else-if="quiz.questions.length === 0">
        <div class="text-center py-16 text-gray-400">This quiz has no questions yet.</div>
      </template>

      <template v-else>
        <!-- Header -->
        <header class="mb-8">
          <h1 class="text-2xl sm:text-3xl font-bold text-gray-900 mb-2">{{ quiz.title }}</h1>
          <p v-if="inRetryRound" class="text-sm text-amber-600 font-medium">
            Let's retry the ones you missed — {{ currentIndex + 1 }} of {{ totalQuestions }} remaining
          </p>
          <p v-else class="text-sm text-gray-500">Question {{ currentIndex + 1 }} of {{ totalQuestions }}</p>

          <!-- Progress bar -->
          <div class="mt-3 h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              class="h-full bg-indigo-500 rounded-full transition-all duration-300"
              :style="{ width: `${((currentIndex + (showResult ? 1 : 0)) / totalQuestions) * 100}%` }"
            />
          </div>
        </header>

        <!-- Question card -->
        <div v-if="currentQuestion" class="mb-6">
          <p class="text-lg font-medium text-gray-900 mb-6">{{ currentQuestion.question }}</p>

          <!-- Options -->
          <div class="space-y-3">
            <button
              v-for="(option, idx) in currentQuestion.options"
              :key="idx"
              @click="selectOption(idx)"
              :disabled="showResult"
              class="w-full text-left px-4 py-3 rounded-xl border-2 font-medium transition flex items-start gap-3"
              :class="[
                isCorrectOption(idx)
                  ? 'border-green-500 bg-green-50 text-green-800'
                  : isWrongSelected(idx)
                    ? 'border-red-400 bg-red-50 text-red-800'
                    : showResult
                      ? 'border-gray-200 bg-gray-50 text-gray-500 cursor-default'
                      : 'border-gray-200 hover:border-indigo-400 hover:bg-indigo-50 text-gray-800 cursor-pointer'
              ]"
            >
              <span class="flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center text-xs font-bold"
                :class="[
                  isCorrectOption(idx) ? 'border-green-500 bg-green-500 text-white' :
                  isWrongSelected(idx) ? 'border-red-400 bg-red-400 text-white' :
                  'border-gray-300 text-gray-500'
                ]"
              >
                {{ optionLabels[idx] }}
              </span>
              <span>{{ option }}</span>
            </button>
          </div>

          <!-- Explanation + Next button -->
          <div v-if="showResult" class="mt-6">
            <div
              v-if="currentQuestion.explanation"
              class="rounded-lg px-4 py-3 mb-4 text-sm"
              :class="selectedForCurrent === currentQuestion.correct_index
                ? 'bg-green-50 border border-green-200 text-green-800'
                : 'bg-amber-50 border border-amber-200 text-amber-800'"
            >
              {{ currentQuestion.explanation }}
            </div>

            <div class="flex justify-end">
              <button
                v-if="!submitting"
                @click="nextQuestion"
                class="px-6 py-2.5 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition"
              >
                {{ currentIndex < totalQuestions - 1 ? 'Next question' : 'See results' }}
              </button>
              <span v-else class="px-6 py-2.5 text-gray-400 text-sm">Submitting...</span>
            </div>
          </div>
        </div>
      </template>
    </template>

    <div v-else class="py-16 text-center text-gray-400">Loading...</div>
  </div>
</template>
