<script setup lang="ts">
import type { CodingProblemOut } from '@/types/problem'

useSeoMeta({
  title: 'Coding Problems | dsaflash.cards',
  description: 'Practice coding problems with spaced repetition. Track your progress and review due problems.',
})

const { isLoggedIn, authReady } = useAuth()
const { apiFetch } = useApiFetch()
const { track } = useAnalytics()

const problems = ref<CodingProblemOut[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

// Filters
const selectedCategory = ref<string>('')
const selectedDifficulty = ref<string>('')
const selectedTag = ref<string>('')

let tracked = false

async function fetchProblems() {
  loading.value = true
  error.value = null
  try {
    problems.value = await apiFetch<CodingProblemOut[]>('/problems')
    if (!tracked) {
      track('problem_list_view', { category: selectedCategory.value })
      tracked = true
    }
  } catch (e: any) {
    error.value = e?.data?.detail || 'Failed to load problems'
  } finally {
    loading.value = false
  }
}

watch(authReady, (ready) => {
  if (ready) fetchProblems()
}, { immediate: true })

// Derived filter options
const categories = computed(() => {
  const cats = new Set(problems.value.map(p => p.category))
  return Array.from(cats).sort()
})

const allTags = computed(() => {
  const tags = new Set(problems.value.flatMap(p => p.tags))
  return Array.from(tags).sort()
})

// Filtered list
const filtered = computed(() => {
  let list = problems.value
  if (selectedCategory.value) {
    list = list.filter(p => p.category === selectedCategory.value)
  }
  if (selectedDifficulty.value) {
    list = list.filter(p => p.difficulty === selectedDifficulty.value)
  }
  if (selectedTag.value) {
    list = list.filter(p => p.tags.includes(selectedTag.value))
  }
  return list
})

// Due problems first
const sorted = computed(() => {
  return [...filtered.value].sort((a, b) => {
    const order: Record<string, number> = { due: 0, review: 1, new: 2 }
    const aOrder = a.due_status ? (order[a.due_status] ?? 3) : 3
    const bOrder = b.due_status ? (order[b.due_status] ?? 3) : 3
    return aOrder - bOrder
  })
})

const dueCount = computed(() => {
  return problems.value.filter(p => p.due_status === 'due').length
})

function toggleTag(tag: string) {
  selectedTag.value = selectedTag.value === tag ? '' : tag
}

function formatDueStatus(status: string | null): string {
  if (!status) return ''
  const map: Record<string, string> = { due: 'Due today', review: 'Review', new: 'New' }
  return map[status] || ''
}
</script>

<template>
  <div>
    <Breadcrumb :items="[{ label: 'Home', to: '/' }, { label: 'Problems' }]" />

    <h1 class="text-2xl font-tektur font-bold text-gray-900 mb-1">Coding Problems</h1>

    <!-- Due count banner -->
    <p v-if="isLoggedIn && dueCount > 0" class="text-sm text-amber-700 font-medium mb-4">
      {{ dueCount }} problem{{ dueCount !== 1 ? 's' : '' }} due today
    </p>
    <p v-else-if="isLoggedIn && !loading && problems.length > 0 && dueCount === 0" class="text-sm text-gray-500 mb-4">
      No problems due. Nice work!
    </p>

    <!-- Filters -->
    <div class="flex flex-wrap items-center gap-3 mb-4">
      <select
        v-model="selectedCategory"
        class="text-sm border border-gray-200 rounded-md px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-purple-300"
      >
        <option value="">All categories</option>
        <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
      </select>

      <select
        v-model="selectedDifficulty"
        class="text-sm border border-gray-200 rounded-md px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-purple-300"
      >
        <option value="">All difficulties</option>
        <option value="easy">Easy</option>
        <option value="medium">Medium</option>
        <option value="hard">Hard</option>
      </select>
    </div>

    <!-- Tag chips -->
    <div v-if="allTags.length > 0" class="flex flex-wrap gap-1.5 mb-5">
      <ProblemsTagChip
        v-for="tag in allTags"
        :key="tag"
        :tag="tag"
        :active="selectedTag === tag"
        @click="toggleTag(tag)"
      />
    </div>

    <!-- Loading -->
    <div v-if="loading" class="py-16 text-center text-gray-400 text-sm">
      Loading problems...
    </div>

    <!-- Error -->
    <div v-else-if="error" class="py-16 text-center text-red-500 text-sm">
      {{ error }}
    </div>

    <!-- Empty state -->
    <div v-else-if="problems.length === 0" class="py-16 text-center">
      <p class="text-gray-400 text-sm">No problems yet. Check back soon.</p>
    </div>

    <!-- No filter results -->
    <div v-else-if="sorted.length === 0" class="py-16 text-center">
      <p class="text-gray-400 text-sm">No problems match your filters.</p>
    </div>

    <!-- Problem table -->
    <div v-else>
      <!-- Desktop table -->
      <div class="hidden sm:block overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-200 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">
              <th class="pb-2 pr-3 w-8"></th>
              <th class="pb-2 pr-3">Title</th>
              <th class="pb-2 pr-3 w-24">Difficulty</th>
              <th class="pb-2 pr-3">Pattern</th>
              <th v-if="isLoggedIn" class="pb-2 pr-3 w-28">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="problem in sorted"
              :key="problem.id"
              class="border-b border-gray-100 hover:bg-gray-50 transition-colors duration-100 cursor-pointer"
              @click="$router.push(`/problems/${problem.id}`)"
            >
              <td class="py-2.5 pr-3">
                <span
                  v-if="problem.due_status === 'due'"
                  class="block w-2.5 h-2.5 rounded-full bg-amber-400"
                  title="Due today"
                />
                <span
                  v-else-if="problem.due_status === 'review'"
                  class="block w-2.5 h-2.5 rounded-full bg-blue-400"
                  title="In review"
                />
                <span
                  v-else-if="problem.due_status === 'new'"
                  class="block w-2.5 h-2.5 rounded-full bg-gray-300"
                  title="New"
                />
              </td>
              <td class="py-2.5 pr-3 font-medium text-gray-900">
                {{ problem.title }}
              </td>
              <td class="py-2.5 pr-3">
                <ProblemsDifficultyBadge :difficulty="problem.difficulty" />
              </td>
              <td class="py-2.5 pr-3">
                <span
                  v-for="tag in problem.tags"
                  :key="tag"
                  class="inline-block mr-1 px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded"
                >
                  {{ tag }}
                </span>
              </td>
              <td v-if="isLoggedIn" class="py-2.5 pr-3">
                <span
                  v-if="problem.due_status === 'due'"
                  class="inline-block px-2 py-0.5 text-xs font-semibold bg-amber-100 text-amber-700 rounded"
                >
                  Due today
                </span>
                <span
                  v-else-if="problem.due_status"
                  class="text-xs text-gray-400 capitalize"
                >
                  {{ formatDueStatus(problem.due_status) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Mobile list -->
      <div class="sm:hidden space-y-2">
        <NuxtLink
          v-for="problem in sorted"
          :key="problem.id"
          :to="`/problems/${problem.id}`"
          class="block border border-gray-200 rounded-lg px-4 py-3 bg-white hover:bg-gray-50 transition-colors"
        >
          <div class="flex items-center gap-2 mb-1">
            <span
              v-if="problem.due_status === 'due'"
              class="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0"
            />
            <span class="font-medium text-gray-900 text-sm">{{ problem.title }}</span>
          </div>
          <div class="flex items-center gap-2 flex-wrap">
            <ProblemsDifficultyBadge :difficulty="problem.difficulty" />
            <span
              v-for="tag in problem.tags.slice(0, 2)"
              :key="tag"
              class="text-[10px] px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded"
            >
              {{ tag }}
            </span>
            <span
              v-if="isLoggedIn && problem.due_status === 'due'"
              class="text-[10px] font-semibold text-amber-600 ml-auto"
            >
              Due today
            </span>
          </div>
        </NuxtLink>
      </div>
    </div>
  </div>
</template>
