import { vi, describe, it, expect, beforeEach } from 'vitest'
import { ref, computed, watch, onMounted, nextTick, Suspense, h } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'

// Stub Nuxt auto-imports as globals
const mockFetch = vi.fn()
const mockApiFetch = vi.fn()
const mockIsLoggedIn = ref(false)
const mockTrack = vi.fn()

vi.stubGlobal('useAuth', () => ({ isLoggedIn: mockIsLoggedIn }))
vi.stubGlobal('useApiFetch', () => ({ apiFetch: mockApiFetch }))
vi.stubGlobal('useAnalytics', () => ({ track: mockTrack }))
vi.stubGlobal('useSeoMeta', vi.fn())
vi.stubGlobal('useHead', vi.fn())
vi.stubGlobal('useState', (_key: string, init?: () => unknown) => ref(init ? init() : null))
vi.stubGlobal('useCookie', () => ref(null))
vi.stubGlobal('useRuntimeConfig', () => ({ public: { apiBase: '/api' } }))
vi.stubGlobal('useRoute', () => ({ params: { slug: 'arrays-quiz' } }))
vi.stubGlobal('useRouter', () => ({ push: vi.fn() }))
vi.stubGlobal('$fetch', mockFetch)
vi.stubGlobal('ref', ref)
vi.stubGlobal('computed', computed)
vi.stubGlobal('watch', watch)
vi.stubGlobal('onMounted', onMounted)
vi.stubGlobal('nextTick', nextTick)

vi.stubGlobal('useAsyncData', (_key: string, fetcher: () => Promise<unknown>) => {
  const data = ref<unknown>(null)
  const error = ref<unknown>(null)
  fetcher()
    .then((v) => { data.value = v })
    .catch((e) => { error.value = e })
  return { data, error }
})

// Mock composables that use #imports to avoid resolution errors in vitest
vi.mock('@/composables/useAnalytics', () => ({
  useAnalytics: () => ({ track: mockTrack }),
}))
vi.mock('@/utils/categoryMeta', () => ({
  getCategoryDisplayName: (cat: string) => cat,
}))

import QuizPage from '../../../pages/quiz/[slug].vue'

const MOCK_QUIZ = {
  id: 1,
  title: 'Arrays Quiz',
  slug: 'arrays-quiz',
  category: 'arrays',
  lesson_slug: 'arrays-intro',
  questions: [
    {
      id: 10,
      order: 1,
      question: 'What is an array?',
      options: ['A sequence', 'A tree', 'A graph', 'A hash'],
      correct_index: 0,
      explanation: 'An array is a sequence of elements.',
    },
  ],
}

const MOCK_SUBMIT_RESULT = {
  score: 1,
  total: 1,
  results: [{ question_id: 10, correct: true, correct_index: 0, explanation: 'An array is a sequence of elements.' }],
}

const MOCK_PROBLEMS = [
  { id: 1, title: 'Two Sum', difficulty: 'easy', category: 'arrays', tags: [], due_status: null },
  { id: 2, title: 'Three Sum', difficulty: 'medium', category: 'arrays', tags: [], due_status: null },
  { id: 3, title: 'Valid Palindrome', difficulty: 'easy', category: 'arrays', tags: [], due_status: null },
  { id: 4, title: 'Extra Problem', difficulty: 'hard', category: 'arrays', tags: [], due_status: null },
]

const globalStubs = {
  Breadcrumb: { template: '<nav />' },
  NuxtLink: {
    template: '<a :href="to"><slot /></a>',
    props: ['to'],
  },
}

function mountQuiz() {
  return mount(
    { render: () => h(Suspense, null, { default: () => h(QuizPage) }) },
    { global: { stubs: globalStubs } },
  )
}

async function mountAndComplete(problems: typeof MOCK_PROBLEMS) {
  mockFetch.mockImplementation((url: string) => {
    if (url.includes('/quizzes/arrays-quiz')) return Promise.resolve(MOCK_QUIZ)
    if (url.includes('/problems')) return Promise.resolve(problems)
    return Promise.resolve(null)
  })

  mockApiFetch.mockImplementation((path: string) => {
    if (path.includes('/quizzes/arrays-quiz/submit')) return Promise.resolve(MOCK_SUBMIT_RESULT)
    if (path.includes('/lessons/by-category')) return Promise.resolve([])
    return Promise.resolve(null)
  })

  const wrapper = mountQuiz()
  await flushPromises()

  // Click the correct answer ('A sequence') so we skip the retry round and go straight to results
  const buttons = wrapper.findAll('button')
  const correctBtn = buttons.find(b => b.text().includes('A sequence'))
  if (correctBtn) {
    await correctBtn.trigger('click')
    await nextTick()
    const seeResults = wrapper.findAll('button').find(b => b.text().includes('See results'))
    if (seeResults) await seeResults.trigger('click')
  }
  await flushPromises()

  return wrapper
}

describe('Quiz page — Ready to code? section', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockIsLoggedIn.value = false
  })

  it('hides Ready to code section when category has no problems', async () => {
    const wrapper = await mountAndComplete([])
    expect(wrapper.text()).not.toContain('Ready to code?')
  })

  it('shows Ready to code section when problems exist', async () => {
    const wrapper = await mountAndComplete(MOCK_PROBLEMS)
    expect(wrapper.text()).toContain('Ready to code?')
  })

  it('shows up to 3 problem suggestions', async () => {
    const wrapper = await mountAndComplete(MOCK_PROBLEMS)
    expect(wrapper.text()).toContain('Two Sum')
    expect(wrapper.text()).toContain('Three Sum')
    expect(wrapper.text()).toContain('Valid Palindrome')
    expect(wrapper.text()).not.toContain('Extra Problem')
  })

  it('renders problem links with correct href', async () => {
    const wrapper = await mountAndComplete(MOCK_PROBLEMS.slice(0, 3))
    const link = wrapper.find('a[href="/problems/1"]')
    expect(link.exists()).toBe(true)
    expect(link.text()).toBe('Two Sum')
  })

  it('fetches problems using the quiz category', async () => {
    let capturedUrl = ''
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/quizzes/arrays-quiz')) return Promise.resolve(MOCK_QUIZ)
      if (url.includes('/problems')) {
        capturedUrl = url
        return Promise.resolve(MOCK_PROBLEMS)
      }
      return Promise.resolve(null)
    })
    mockApiFetch.mockImplementation((path: string) => {
      if (path.includes('/quizzes/arrays-quiz/submit')) return Promise.resolve(MOCK_SUBMIT_RESULT)
      if (path.includes('/lessons/by-category')) return Promise.resolve([])
      return Promise.resolve(null)
    })

    const wrapper = mountQuiz()
    await flushPromises()

    // Click the correct answer to avoid retry round
    const buttons = wrapper.findAll('button')
    const correctBtn = buttons.find(b => b.text().includes('A sequence'))
    if (correctBtn) {
      await correctBtn.trigger('click')
      await nextTick()
      const seeResults = wrapper.findAll('button').find(b => b.text().includes('See results'))
      if (seeResults) await seeResults.trigger('click')
    }
    await flushPromises()

    expect(capturedUrl).toContain('category=arrays')
  })
})
