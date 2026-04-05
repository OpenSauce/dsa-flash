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
vi.stubGlobal('useRoute', () => ({ params: { slug: 'arrays-intro' } }))
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
vi.mock('@/composables/useMarkdown', () => ({
  useMarkdown: () => ({ render: (s: string) => `<p>${s}</p>` }),
}))
vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({ isLoggedIn: mockIsLoggedIn }),
}))
vi.mock('@/composables/useAnalytics', () => ({
  useAnalytics: () => ({ track: mockTrack }),
}))
vi.mock('@/utils/categoryMeta', () => ({
  getCategoryDisplayName: (cat: string) => cat,
}))

import LessonPage from '../../../pages/lesson/[slug].vue'

const MOCK_LESSON = {
  id: 1,
  title: 'Introduction to Arrays',
  slug: 'arrays-intro',
  category: 'arrays',
  order: 1,
  summary: 'Learn about arrays',
  reading_time_minutes: 5,
  content: '# Arrays\n\nArrays are...',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  user_rating: null,
}

const MOCK_PROBLEMS = [
  { id: 1, title: 'Two Sum', difficulty: 'easy', category: 'arrays', tags: [], due_status: null },
  { id: 2, title: 'Three Sum', difficulty: 'medium', category: 'arrays', tags: [], due_status: null },
  { id: 3, title: 'Valid Palindrome', difficulty: 'easy', category: 'arrays', tags: [], due_status: null },
]

const globalStubs = {
  Breadcrumb: { template: '<nav />' },
  LessonRating: { template: '<div class="lesson-rating" />' },
  FeedbackLink: { template: '<div class="feedback-link" />' },
  NuxtLink: {
    template: '<a :href="to"><slot /></a>',
    props: ['to'],
  },
}

function mountPage() {
  const wrapper = mount(
    { render: () => h(Suspense, null, { default: () => h(LessonPage) }) },
    { global: { stubs: globalStubs } },
  )
  return wrapper
}

describe('Lesson page — Related Problems section', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockIsLoggedIn.value = false

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/lessons/arrays-intro')) return Promise.resolve(MOCK_LESSON)
      if (url.includes('/quizzes')) return Promise.resolve([])
      return Promise.resolve(null)
    })

    mockApiFetch.mockImplementation((path: string) => {
      if (path.includes('/lessons/by-category')) return Promise.resolve([])
      if (path.includes('/problems')) return Promise.resolve([])
      return Promise.resolve(null)
    })
  })

  it('hides the Related Problems section when there are no problems', async () => {
    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.text()).not.toContain('Related Problems')
  })

  it('renders the Related Problems section when problems exist', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/lessons/arrays-intro')) return Promise.resolve(MOCK_LESSON)
      if (url.includes('/quizzes')) return Promise.resolve([])
      return Promise.resolve(null)
    })
    mockApiFetch.mockImplementation((path: string) => {
      if (path.includes('/lessons/by-category')) return Promise.resolve([])
      if (path.includes('/problems')) return Promise.resolve(MOCK_PROBLEMS)
      return Promise.resolve(null)
    })

    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.text()).toContain('Related Problems')
    expect(wrapper.text()).toContain('Two Sum')
    expect(wrapper.text()).toContain('Three Sum')
    expect(wrapper.text()).toContain('Valid Palindrome')
  })

  it('renders correct href links for each problem', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/lessons/arrays-intro')) return Promise.resolve(MOCK_LESSON)
      if (url.includes('/quizzes')) return Promise.resolve([])
      return Promise.resolve(null)
    })
    mockApiFetch.mockImplementation((path: string) => {
      if (path.includes('/lessons/by-category')) return Promise.resolve([])
      if (path.includes('/problems')) return Promise.resolve(MOCK_PROBLEMS)
      return Promise.resolve(null)
    })

    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.find('a[href="/problems/1"]').exists()).toBe(true)
    expect(wrapper.find('a[href="/problems/2"]').exists()).toBe(true)
    expect(wrapper.find('a[href="/problems/3"]').exists()).toBe(true)
  })

  it('shows difficulty badges for each problem', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/lessons/arrays-intro')) return Promise.resolve(MOCK_LESSON)
      if (url.includes('/quizzes')) return Promise.resolve([])
      return Promise.resolve(null)
    })
    mockApiFetch.mockImplementation((path: string) => {
      if (path.includes('/lessons/by-category')) return Promise.resolve([])
      if (path.includes('/problems')) return Promise.resolve(MOCK_PROBLEMS)
      return Promise.resolve(null)
    })

    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.text()).toContain('easy')
    expect(wrapper.text()).toContain('medium')
  })

  it('caps displayed problems at 6 and shows "See all" link when there are more', async () => {
    const manyProblems = Array.from({ length: 8 }, (_, i) => ({
      id: i + 1,
      title: `Problem ${i + 1}`,
      difficulty: 'easy',
      category: 'arrays',
      tags: [],
      due_status: null,
    }))

    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/lessons/arrays-intro')) return Promise.resolve(MOCK_LESSON)
      if (url.includes('/quizzes')) return Promise.resolve([])
      return Promise.resolve(null)
    })
    mockApiFetch.mockImplementation((path: string) => {
      if (path.includes('/lessons/by-category')) return Promise.resolve([])
      if (path.includes('/problems')) return Promise.resolve(manyProblems)
      return Promise.resolve(null)
    })

    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.text()).toContain('Problem 1')
    expect(wrapper.text()).toContain('Problem 6')
    expect(wrapper.text()).not.toContain('Problem 7')
    expect(wrapper.text()).toContain('See all 8 problems')
  })

  it('does not show "See all" link when problems are 6 or fewer', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/lessons/arrays-intro')) return Promise.resolve(MOCK_LESSON)
      if (url.includes('/quizzes')) return Promise.resolve([])
      return Promise.resolve(null)
    })
    mockApiFetch.mockImplementation((path: string) => {
      if (path.includes('/lessons/by-category')) return Promise.resolve([])
      if (path.includes('/problems')) return Promise.resolve(MOCK_PROBLEMS)
      return Promise.resolve(null)
    })

    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.text()).not.toContain('See all')
  })

  it('fetches problems using the lesson category', async () => {
    let capturedUrl = ''
    mockApiFetch.mockImplementation((path: string) => {
      if (path.includes('/lessons/by-category')) return Promise.resolve([])
      if (path.includes('/problems')) {
        capturedUrl = path
        return Promise.resolve(MOCK_PROBLEMS)
      }
      return Promise.resolve(null)
    })

    const wrapper = mountPage()
    await flushPromises()

    expect(capturedUrl).toContain('category=arrays')
  })
})
