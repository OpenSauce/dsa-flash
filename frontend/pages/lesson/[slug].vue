<script setup lang="ts">
import { useMarkdown } from '@/composables/useMarkdown'
import { useAuth } from '@/composables/useAuth'
import { getCategoryDisplayName } from '@/utils/categoryMeta'

const route = useRoute()
const slug = route.params.slug as string
const { public: { apiBase } } = useRuntimeConfig()
const { isLoggedIn, tokenCookie } = useAuth()
const md = useMarkdown()

interface LessonDetail {
  id: number
  title: string
  slug: string
  category: string | null
  order: number
  summary: string
  reading_time_minutes: number
  content: string
  created_at: string
  updated_at: string
}

interface CategoryLessonInfo {
  slug: string
  title: string
  completed: boolean
}

const { data: lesson, error } = await useAsyncData<LessonDetail>(
  `lesson-${slug}`,
  () => $fetch<LessonDetail>(`${apiBase}/lessons/${slug}`),
)

useSeoMeta({
  title: computed(() => lesson.value ? `${lesson.value.title} | dsaflash.cards` : 'Lesson | dsaflash.cards'),
  ogTitle: computed(() => lesson.value ? `${lesson.value.title} | dsaflash.cards` : 'Lesson | dsaflash.cards'),
  description: computed(() => lesson.value?.summary || ''),
  ogDescription: computed(() => lesson.value?.summary || ''),
})

useHead({
  link: computed(() => lesson.value ? [{ rel: 'canonical', href: `https://dsaflash.cards/lesson/${lesson.value.slug}` }] : []),
})

const categoryLessons = ref<CategoryLessonInfo[]>([])
const isCompleted = ref(false)
const completing = ref(false)
const completionSuccess = ref(false)
const linkedQuiz = ref<{ slug: string; title: string } | null>(null)

const fetchCategoryLessons = async () => {
  if (!lesson.value?.category) return
  try {
    const headers = tokenCookie.value ? { Authorization: `Bearer ${tokenCookie.value}` } : {}
    const data = await $fetch<CategoryLessonInfo[]>(
      `${apiBase}/lessons/by-category/${lesson.value.category}`,
      { headers }
    )
    categoryLessons.value = data
    const thisLesson = data.find(l => l.slug === slug)
    if (thisLesson) {
      isCompleted.value = thisLesson.completed
      if (thisLesson.completed) completionSuccess.value = true
    }
  } catch {
    // non-fatal
  }
}

const fetchLinkedQuiz = async () => {
  try {
    const quizzes = await $fetch<Array<{ slug: string; title: string }>>(
      `${apiBase}/quizzes?lesson_slug=${slug}`
    )
    if (quizzes.length) linkedQuiz.value = quizzes[0]
  } catch {
    // non-fatal
  }
}

onMounted(async () => {
  await fetchCategoryLessons()
  await fetchLinkedQuiz()
})

const prevLesson = computed<CategoryLessonInfo | null>(() => {
  if (!lesson.value) return null
  const idx = categoryLessons.value.findIndex(l => l.slug === slug)
  return idx > 0 ? categoryLessons.value[idx - 1] : null
})

const nextLesson = computed<CategoryLessonInfo | null>(() => {
  if (!lesson.value) return null
  const idx = categoryLessons.value.findIndex(l => l.slug === slug)
  return idx >= 0 && idx < categoryLessons.value.length - 1
    ? categoryLessons.value[idx + 1]
    : null
})

const categoryDisplayName = computed(() =>
  lesson.value?.category ? getCategoryDisplayName(lesson.value.category) : ''
)

async function markComplete() {
  if (!lesson.value || completing.value || isCompleted.value) return
  completing.value = true
  try {
    await $fetch(`${apiBase}/lessons/${slug}/complete`, {
      method: 'POST',
      headers: tokenCookie.value ? { Authorization: `Bearer ${tokenCookie.value}` } : {},
    })
    isCompleted.value = true
    completionSuccess.value = true
  } catch {
    // non-fatal, user can retry
  } finally {
    completing.value = false
  }
}

const renderedContent = computed(() =>
  lesson.value ? md.render(lesson.value.content) : ''
)
</script>

<template>
  <div class="max-w-3xl mx-auto px-4 sm:px-6 pb-16">

    <div v-if="error" class="text-center text-red-500 py-16">
      Lesson not found. <NuxtLink to="/" class="underline text-blue-600">Back to home</NuxtLink>
    </div>

    <template v-else-if="lesson">
      <Breadcrumb :items="[
        { label: 'Home', to: '/' },
        ...(lesson.category ? [{ label: categoryDisplayName, to: `/category/${lesson.category}` }] : []),
        { label: lesson.title },
      ]" />

      <!-- Header -->
      <header class="mb-8">
        <h1 class="text-3xl sm:text-4xl font-bold text-gray-900 mb-3">{{ lesson.title }}</h1>
        <p class="text-gray-600 text-lg mb-3">{{ lesson.summary }}</p>
        <div class="flex items-center gap-3 text-sm text-gray-500">
          <span>{{ lesson.reading_time_minutes }} min read</span>
          <span v-if="isCompleted" class="inline-flex items-center gap-1 text-green-600 font-medium">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            Completed
          </span>
        </div>
      </header>

      <!-- Lesson content -->
      <article class="prose prose-gray max-w-none mb-12" v-html="renderedContent" />

      <!-- Completion section -->
      <div class="border-t border-gray-200 pt-8">
        <!-- Quiz exists: quiz is the completion mechanism -->
        <template v-if="linkedQuiz">
          <div v-if="completionSuccess" class="rounded-lg bg-green-50 border border-green-200 px-5 py-4 mb-6">
            <p class="font-semibold text-green-800 mb-1">Lesson complete!</p>
            <p class="text-green-700 text-sm">
              Great work! Your flashcards are unlocked and will appear in your reviews.
            </p>
          </div>

          <div v-else class="flex flex-col items-center gap-3 mb-6">
            <NuxtLink
              :to="`/quiz/${linkedQuiz.slug}`"
              class="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition"
            >
              Take the quiz
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </NuxtLink>
            <p v-if="isLoggedIn" class="text-sm text-gray-500">Complete the quiz to unlock flashcards</p>
            <p v-else class="text-sm text-gray-500">
              <NuxtLink to="/signup" class="underline font-medium text-indigo-600">Sign up</NuxtLink>
              to save your progress
            </p>
          </div>
        </template>

        <!-- No quiz: mark-as-complete is the completion mechanism -->
        <template v-else>
          <div v-if="completionSuccess" class="rounded-lg bg-green-50 border border-green-200 px-5 py-4 mb-6">
            <p class="font-semibold text-green-800 mb-1">Lesson complete!</p>
            <p class="text-green-700 text-sm">
              Great work! Check back tomorrow for flashcard reviews.
            </p>
          </div>

          <div v-else-if="isLoggedIn" class="flex justify-center mb-6">
            <button
              @click="markComplete"
              :disabled="completing"
              class="px-6 py-3 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 disabled:opacity-60 transition"
            >
              {{ completing ? 'Saving...' : 'Mark as complete' }}
            </button>
          </div>

          <div v-else class="text-center text-sm text-gray-500 mb-6">
            <NuxtLink to="/signup" class="underline font-medium text-indigo-600">Sign up</NuxtLink>
            to track your progress.
          </div>
        </template>

        <!-- Prev / Next navigation -->
        <div v-if="categoryLessons.length > 1" class="flex justify-between gap-4 mt-4">
          <NuxtLink
            v-if="prevLesson"
            :to="`/lesson/${prevLesson.slug}`"
            class="flex-1 text-left px-4 py-3 border border-gray-200 rounded-xl hover:bg-gray-50 transition text-sm"
          >
            <span class="text-gray-400 text-xs block mb-0.5">Previous</span>
            <span class="font-medium text-gray-800">{{ prevLesson.title }}</span>
          </NuxtLink>
          <div v-else class="flex-1" />

          <NuxtLink
            v-if="nextLesson"
            :to="`/lesson/${nextLesson.slug}`"
            class="flex-1 text-right px-4 py-3 border border-gray-200 rounded-xl hover:bg-gray-50 transition text-sm"
          >
            <span class="text-gray-400 text-xs block mb-0.5">Next</span>
            <span class="font-medium text-gray-800">{{ nextLesson.title }}</span>
          </NuxtLink>
          <div v-else class="flex-1" />
        </div>
        <NuxtLink to="/" class="block text-sm text-gray-400 hover:text-gray-600 mt-8 text-center">&larr; Back to categories</NuxtLink>
      </div>
    </template>

    <div v-else class="py-16 text-center text-gray-400">Loading...</div>
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
