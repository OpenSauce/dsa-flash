<script setup lang="ts">
import type { CodingProblemDetailOut, SubmissionOut, HintOut } from '@/types/problem'
import { useMarkdown } from '@/composables/useMarkdown'

const route = useRoute()
const router = useRouter()
const problemId = computed(() => Number(route.params.id))

const { isLoggedIn, authReady } = useAuth()
const { apiFetch } = useApiFetch()
const md = useMarkdown()

// Problem data
const problem = ref<CodingProblemDetailOut | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

// Editor state
const code = ref('')
const submitting = ref(false)
const running = ref(false)
const submission = ref<SubmissionOut | null>(null)

// Hints
const hints = ref<string[]>([])
const hintLoading = ref(false)

// Timer
const startTime = ref<number>(0)
const solveTimeMs = ref<number | null>(null)

// Rating state
const rated = ref(false)
const showLoginPrompt = ref(false)

// Toast
const toast = ref<string | null>(null)
let toastTimeout: ReturnType<typeof setTimeout> | null = null
let autoAdvanceTimeout: ReturnType<typeof setTimeout> | null = null

function showToast(message: string) {
  toast.value = message
  if (toastTimeout) clearTimeout(toastTimeout)
  toastTimeout = setTimeout(() => { toast.value = null }, 3000)
}

onBeforeUnmount(() => {
  if (toastTimeout) clearTimeout(toastTimeout)
  if (autoAdvanceTimeout) clearTimeout(autoAdvanceTimeout)
})

async function fetchProblem() {
  loading.value = true
  error.value = null
  try {
    problem.value = await apiFetch<CodingProblemDetailOut>(`/problems/${problemId.value}`)
    code.value = problem.value.starter_code?.python || ''
    startTime.value = Date.now()
    // Reset state
    submission.value = null
    hints.value = []
    rated.value = false
    solveTimeMs.value = null
    showLoginPrompt.value = false
  } catch (e: any) {
    error.value = e?.data?.detail || 'Failed to load problem'
  } finally {
    loading.value = false
  }
}

watch([authReady, problemId], ([ready]) => {
  if (ready) fetchProblem()
}, { immediate: true })

// Submit code
async function submitCode() {
  if (!isLoggedIn.value) {
    showLoginPrompt.value = true
    return
  }
  submitting.value = true
  try {
    const result = await apiFetch<SubmissionOut>(`/problems/${problemId.value}/submit`, {
      method: 'POST',
      body: { code: code.value },
    })
    submission.value = result
    if (result.solve_time_ms != null) {
      solveTimeMs.value = result.solve_time_ms
    } else {
      solveTimeMs.value = Date.now() - startTime.value
    }
  } catch (e: any) {
    // Show inline error
    submission.value = {
      passed: false,
      test_results: [],
      stdout: '',
      stderr: e?.data?.detail || 'Submission failed',
      status: 'error',
      solve_time_ms: 0,
    }
  } finally {
    submitting.value = false
  }
}

// Run (same as submit for now — backend decides behavior)
async function runCode() {
  running.value = true
  try {
    await submitCode()
  } finally {
    running.value = false
  }
}

// Request hint
async function requestHint() {
  if (!problem.value) return
  hintLoading.value = true
  try {
    const result = await apiFetch<HintOut>(`/problems/${problemId.value}/hints/${hints.value.length}`)
    hints.value.push(result.hint)
  } catch {
    // ignore hint errors
  } finally {
    hintLoading.value = false
  }
}

// SM-2 rating suggestion
const suggestedRating = computed<'again' | 'good' | 'easy'>(() => {
  if (!submission.value || !submission.value.passed) return 'again'
  if (hints.value.length > 0) return 'good'
  return 'easy'
})

// Rate
async function rate(quality: number) {
  try {
    await apiFetch(`/problems/${problemId.value}/review`, {
      method: 'POST',
      body: { quality },
    })
    rated.value = true

    // Calculate projected next review date
    const daysMap: Record<number, number> = { 1: 1, 3: 4, 5: 10 }
    const days = daysMap[quality] || 4
    const nextDate = new Date()
    nextDate.setDate(nextDate.getDate() + days)
    const dateStr = nextDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    showToast(`Scheduled for ${dateStr}`)

    // Auto-advance to next due problem after delay
    autoAdvanceTimeout = setTimeout(async () => {
      try {
        const problems = await apiFetch<Array<{ id: number }>>('/problems/due')
        const next = problems.find(p => p.id !== problemId.value)
        if (next) {
          router.push(`/problems/${next.id}`)
        } else {
          router.push('/problems')
        }
      } catch {
        router.push('/problems')
      }
    }, 1500)
  } catch {
    // ignore rating errors
  }
}

// SEO
useSeoMeta({
  title: computed(() => problem.value ? `${problem.value.title} | dsaflash.cards` : 'Problem | dsaflash.cards'),
})
</script>

<template>
  <div>
    <!-- Toast notification -->
    <Transition name="toast">
      <div
        v-if="toast"
        class="fixed top-4 right-4 z-50 bg-gray-900 text-white text-sm px-4 py-2.5 rounded-lg shadow-lg"
      >
        {{ toast }}
      </div>
    </Transition>

    <!-- Login prompt modal -->
    <div
      v-if="showLoginPrompt"
      class="fixed inset-0 z-40 flex items-center justify-center bg-black/40"
      @click.self="showLoginPrompt = false"
    >
      <div class="bg-white rounded-xl shadow-xl p-6 max-w-sm mx-4">
        <h3 class="text-lg font-semibold text-gray-900 mb-2">Sign in to submit</h3>
        <p class="text-sm text-gray-600 mb-4">Create a free account to submit solutions and track your progress.</p>
        <div class="flex gap-3">
          <NuxtLink
            to="/login"
            class="flex-1 text-center px-4 py-2 text-sm font-semibold border border-gray-300 rounded-lg hover:bg-gray-50 transition"
          >
            Log in
          </NuxtLink>
          <NuxtLink
            to="/signup"
            class="flex-1 text-center px-4 py-2 text-sm font-semibold bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition"
          >
            Sign up
          </NuxtLink>
        </div>
        <button
          class="mt-3 w-full text-xs text-gray-400 hover:text-gray-600"
          @click="showLoginPrompt = false"
        >
          Cancel
        </button>
      </div>
    </div>

    <Breadcrumb :items="[
      { label: 'Home', to: '/' },
      { label: 'Problems', to: '/problems' },
      { label: problem?.title || 'Loading...' },
    ]" />

    <!-- Loading skeleton (only show after auth is ready to avoid double-flash) -->
    <div v-if="!authReady || loading" class="flex flex-col md:flex-row gap-4 md:gap-6 animate-pulse">
      <div class="w-full md:w-2/5 space-y-4">
        <div class="h-7 bg-gray-200 rounded w-48" />
        <div class="flex gap-2">
          <div class="h-5 bg-gray-200 rounded w-14" />
          <div class="h-5 bg-gray-200 rounded w-20" />
        </div>
        <div class="space-y-2">
          <div class="h-4 bg-gray-200 rounded w-full" />
          <div class="h-4 bg-gray-200 rounded w-5/6" />
          <div class="h-4 bg-gray-200 rounded w-4/6" />
        </div>
        <div class="h-24 bg-gray-100 rounded-lg border border-gray-200" />
        <div class="space-y-2">
          <div class="h-4 bg-gray-200 rounded w-full" />
          <div class="h-4 bg-gray-200 rounded w-3/4" />
        </div>
      </div>
      <div class="w-full md:w-3/5">
        <div class="h-[400px] bg-[#1e1e1e] rounded-lg" />
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="py-16 text-center text-red-500 text-sm">
      {{ error }}
    </div>

    <!-- Problem detail -->
    <div v-else-if="problem" class="flex flex-col md:flex-row gap-4 md:gap-6">
      <!-- Left pane: problem statement -->
      <div class="w-full md:w-2/5 md:max-h-[calc(100vh-160px)] md:overflow-y-auto md:pr-2 max-h-[40vh] overflow-y-auto">
        <!-- Header -->
        <div class="mb-4">
          <div class="flex items-center gap-3 flex-wrap mb-2">
            <h1 class="text-xl font-tektur font-bold text-gray-900">{{ problem.title }}</h1>
            <ProblemsDifficultyBadge :difficulty="problem.difficulty" />
            <span
              v-if="problem.due_status === 'due'"
              class="inline-block px-2 py-0.5 text-xs font-semibold bg-amber-100 text-amber-700 rounded"
            >
              Due today
            </span>
          </div>
          <div class="flex flex-wrap gap-1.5 mb-3">
            <span
              v-for="tag in problem.tags"
              :key="tag"
              class="inline-block px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded"
            >
              {{ tag }}
            </span>
          </div>
        </div>

        <!-- Description -->
        <div class="prose prose-sm max-w-none mb-6" v-html="md.render(problem.description)" />

        <!-- Examples -->
        <div v-if="problem.examples.length > 0" class="mb-6">
          <h3 class="text-sm font-semibold text-gray-700 mb-3">Examples</h3>
          <div
            v-for="(ex, i) in problem.examples"
            :key="i"
            class="mb-4 bg-gray-50 rounded-lg border border-gray-200 p-3 font-mono text-sm"
          >
            <div class="mb-1"><span class="text-gray-500 font-sans text-xs">Input:</span> {{ ex.input }}</div>
            <div class="mb-1"><span class="text-gray-500 font-sans text-xs">Output:</span> {{ ex.output }}</div>
            <div v-if="ex.explanation" class="text-gray-500 font-sans text-xs mt-1">
              <span class="font-semibold">Explanation:</span> {{ ex.explanation }}
            </div>
          </div>
        </div>

        <!-- Constraints -->
        <div v-if="problem.constraints.length > 0" class="mb-6">
          <h3 class="text-sm font-semibold text-gray-700 mb-2">Constraints</h3>
          <ul class="list-disc list-inside text-sm text-gray-600 space-y-1">
            <li v-for="(c, i) in problem.constraints" :key="i">{{ c }}</li>
          </ul>
        </div>

        <!-- Hints -->
        <div class="mb-4">
          <ProblemsHintButton
            :hints-count="problem.hints_count"
            :hints-revealed="hints.length"
            :loading="hintLoading"
            @request-hint="requestHint"
          />
          <div v-if="hints.length > 0" class="mt-3 space-y-2">
            <div
              v-for="(hint, i) in hints"
              :key="i"
              class="bg-amber-50 border border-amber-200 rounded-md px-3 py-2 text-sm text-amber-800"
            >
              <span class="font-semibold text-xs text-amber-600">Hint {{ i + 1 }}:</span>
              {{ hint }}
            </div>
          </div>
        </div>
      </div>

      <!-- Right pane: editor + results -->
      <div class="w-full md:w-3/5 flex flex-col">
        <!-- Editor -->
        <div class="rounded-lg overflow-hidden border border-gray-700 bg-[#1e1e1e] flex-1 min-h-[300px] md:min-h-[400px]">
          <ProblemsCodeEditor
            v-model="code"
            language="python"
            @run="runCode"
            @submit="submitCode"
          />
        </div>

        <!-- Action buttons -->
        <div class="flex items-center gap-3 mt-3">
          <button
            class="px-4 py-2 text-sm font-semibold bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors border border-gray-200"
            :disabled="running || submitting"
            @click="runCode"
          >
            <span v-if="running" class="inline-flex items-center gap-1.5">
              <svg class="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" /><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" /></svg>
              Running...
            </span>
            <span v-else>Run <kbd class="text-[10px] bg-gray-200 px-1 rounded ml-1">&#x2318;'</kbd></span>
          </button>
          <button
            class="px-4 py-2 text-sm font-semibold bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors"
            :disabled="submitting || running"
            @click="submitCode"
          >
            <span v-if="submitting" class="inline-flex items-center gap-1.5">
              <svg class="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" /><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" /></svg>
              Submitting...
            </span>
            <span v-else>Submit <kbd class="text-[10px] bg-purple-500 px-1 rounded ml-1">&#x2318;&#x23CE;</kbd></span>
          </button>
        </div>

        <!-- Test results (only when we have actual test data) -->
        <div v-if="submission && submission.test_results.length > 0" class="mt-4">
          <ProblemsTestResults
            :results="submission.test_results"
            :passed="submission.passed"
            :solve-time="solveTimeMs"
          />

          <!-- Stderr output -->
          <div v-if="submission.stderr" class="mt-3 bg-red-50 border border-red-200 rounded-md p-3">
            <p class="text-xs font-semibold text-red-600 mb-1">Error output</p>
            <pre class="text-xs text-red-800 font-mono whitespace-pre-wrap">{{ submission.stderr }}</pre>
          </div>

          <!-- Stdout output -->
          <div v-if="submission.stdout" class="mt-3 bg-gray-50 border border-gray-200 rounded-md p-3">
            <p class="text-xs font-semibold text-gray-600 mb-1">Console output</p>
            <pre class="text-xs text-gray-800 font-mono whitespace-pre-wrap">{{ submission.stdout }}</pre>
          </div>

          <!-- SM-2 Rating (only after successful submission, when logged in) -->
          <div v-if="submission.passed && isLoggedIn && !rated" class="mt-5 pt-4 border-t border-gray-200">
            <ProblemsReviewRating
              :suggested="suggestedRating"
              :hints-used="hints.length"
              @rate="rate"
            />
          </div>

          <!-- Rated confirmation -->
          <div v-if="rated" class="mt-4 text-center text-sm text-gray-500">
            Loading next problem...
          </div>
        </div>

        <!-- Submission error (Judge0 down, runtime error, TLE, etc.) -->
        <div v-else-if="submission" class="mt-4">
          <div class="bg-red-50 border border-red-200 rounded-md p-4">
            <p class="text-sm font-semibold text-red-700 mb-1">{{ submission.status === 'error' ? 'Submission failed' : submission.status }}</p>
            <p class="text-sm text-red-600">{{ submission.stderr || 'Something went wrong. Please try again.' }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.toast-enter-active {
  transition: all 200ms ease-out;
}
.toast-leave-active {
  transition: all 150ms ease-in;
}
.toast-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}
.toast-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
