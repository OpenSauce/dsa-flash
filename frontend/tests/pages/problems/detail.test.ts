import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'

// --- Stub Nuxt auto-imports as globals ---

const mockApiFetch = vi.fn()
const mockIsLoggedIn = ref(false)
const mockAuthReady = ref(false)
const mockRouterPush = vi.fn()
const mockTrack = vi.fn()
const mockProblemId = ref('42')

vi.stubGlobal('useAuth', () => ({
  isLoggedIn: mockIsLoggedIn,
  authReady: mockAuthReady,
}))
vi.stubGlobal('useApiFetch', () => ({ apiFetch: mockApiFetch }))
vi.stubGlobal('useAnalytics', () => ({ track: mockTrack }))
vi.stubGlobal('useSeoMeta', vi.fn())
vi.stubGlobal('useState', (_key: string, init?: () => any) => ref(init ? init() : null))
vi.stubGlobal('useCookie', () => ref(null))
vi.stubGlobal('useRuntimeConfig', () => ({ public: { apiBase: '/api' } }))
vi.stubGlobal('useRoute', () => ({ params: { id: mockProblemId.value } }))
vi.stubGlobal('useRouter', () => ({ push: mockRouterPush }))
vi.stubGlobal('ref', ref)
vi.stubGlobal('computed', computed)
vi.stubGlobal('watch', watch)
vi.stubGlobal('onMounted', onMounted)
vi.stubGlobal('onBeforeUnmount', onBeforeUnmount)

// useMarkdown is an explicit import in [id].vue
vi.mock('@/composables/useMarkdown', () => ({
  useMarkdown: () => ({ render: (s: string) => `<p>${s}</p>` }),
}))

import ProblemDetail from '../../../pages/problems/[id].vue'

const MOCK_PROBLEM = {
  id: 42,
  title: 'Two Sum',
  difficulty: 'easy' as const,
  category: 'Arrays',
  tags: ['hash-map'],
  due_status: 'due' as const,
  description: 'Given an array of integers...',
  examples: [
    { input: 'nums = [2,7,11,15], target = 9', output: '[0,1]', explanation: '2 + 7 = 9' },
  ],
  constraints: ['2 <= nums.length <= 10^4'],
  starter_code: { python: 'def two_sum(nums, target):' },
  hints_count: 2,
  created_at: '2026-04-01T00:00:00Z',
  updated_at: '2026-04-01T00:00:00Z',
}

const MOCK_SUBMISSION_PASS = {
  passed: true,
  test_results: [
    { input: '[2,7,11,15], 9', expected: '[0,1]', actual: '[0,1]', passed: true },
  ],
  stdout: '',
  stderr: '',
  status: 'accepted',
  solve_time_ms: 1234,
}

const MOCK_SUBMISSION_FAIL = {
  passed: false,
  test_results: [
    { input: '[2,7,11,15], 9', expected: '[0,1]', actual: '[1,0]', passed: false },
  ],
  stdout: '',
  stderr: '',
  status: 'wrong_answer',
  solve_time_ms: 567,
}

const globalStubs = {
  Breadcrumb: { template: '<nav />' },
  ProblemsDifficultyBadge: { template: '<span class="badge" />', props: ['difficulty'] },
  ProblemsHintButton: {
    template: '<button class="hint-btn" @click="$emit(\'request-hint\')">Hint</button>',
    props: ['hintsCount', 'hintsRevealed', 'loading'],
  },
  ProblemsCodeEditor: {
    template: '<div class="code-editor" />',
    props: ['modelValue', 'language'],
    emits: ['update:modelValue', 'run', 'submit'],
  },
  ProblemsTestResults: {
    template: '<div class="test-results">Test Results</div>',
    props: ['results', 'passed', 'solveTime'],
  },
  ProblemsReviewRating: {
    template: '<div class="review-rating"><button class="rate-btn" @click="$emit(\'rate\', 5)">Easy</button></div>',
    props: ['suggested', 'hintsUsed'],
  },
  NuxtLink: { template: '<a><slot /></a>', props: ['to'] },
  Transition: { template: '<div><slot /></div>' },
}

function mountPage(opts: { loggedIn?: boolean } = {}) {
  mockIsLoggedIn.value = opts.loggedIn ?? false
  mockAuthReady.value = false
  return mount(ProblemDetail, {
    global: { stubs: globalStubs },
  })
}

describe('Problem Detail Page', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  beforeEach(() => {
    mockApiFetch.mockReset()
    mockRouterPush.mockReset()
    mockTrack.mockReset()
    mockIsLoggedIn.value = false
    mockAuthReady.value = false
    mockProblemId.value = '42'
  })

  it('shows loading skeleton before auth is ready', () => {
    mockApiFetch.mockResolvedValue(MOCK_PROBLEM)
    const wrapper = mountPage()
    expect(wrapper.find('.animate-pulse').exists()).toBe(true)
  })

  it('renders problem detail after fetch', async () => {
    mockApiFetch.mockResolvedValue(MOCK_PROBLEM)
    const wrapper = mountPage()

    mockAuthReady.value = true
    await flushPromises()

    expect(mockApiFetch).toHaveBeenCalledWith('/problems/42')
    expect(wrapper.text()).toContain('Two Sum')
    expect(wrapper.text()).toContain('Given an array of integers...')
    expect(wrapper.text()).toContain('Due today')
  })

  it('renders examples', async () => {
    mockApiFetch.mockResolvedValue(MOCK_PROBLEM)
    const wrapper = mountPage()

    mockAuthReady.value = true
    await flushPromises()

    expect(wrapper.text()).toContain('Examples')
    expect(wrapper.text()).toContain('nums = [2,7,11,15], target = 9')
    expect(wrapper.text()).toContain('[0,1]')
    expect(wrapper.text()).toContain('2 + 7 = 9')
  })

  it('renders constraints', async () => {
    mockApiFetch.mockResolvedValue(MOCK_PROBLEM)
    const wrapper = mountPage()

    mockAuthReady.value = true
    await flushPromises()

    expect(wrapper.text()).toContain('Constraints')
    expect(wrapper.text()).toContain('2 <= nums.length <= 10^4')
  })

  it('shows error state on fetch failure', async () => {
    mockApiFetch.mockRejectedValue({ data: { detail: 'Not found' } })
    const wrapper = mountPage()

    mockAuthReady.value = true
    await flushPromises()

    expect(wrapper.text()).toContain('Not found')
  })

  it('shows login prompt when anonymous user clicks submit', async () => {
    mockApiFetch.mockResolvedValue(MOCK_PROBLEM)
    const wrapper = mountPage({ loggedIn: false })

    mockAuthReady.value = true
    await flushPromises()

    const submitBtn = wrapper.findAll('button').find(b => b.text().includes('Submit'))
    await submitBtn!.trigger('click')
    await nextTick()

    expect(wrapper.text()).toContain('Sign in to submit')
    expect(wrapper.text()).toContain('Log in')
    expect(wrapper.text()).toContain('Sign up')
  })

  it('submits code and shows test results for logged-in user', async () => {
    mockApiFetch.mockImplementation((path: string) => {
      if (path === '/problems/42') return Promise.resolve(MOCK_PROBLEM)
      if (path === '/problems/42/submit') return Promise.resolve(MOCK_SUBMISSION_PASS)
      return Promise.resolve(undefined)
    })
    const wrapper = mountPage({ loggedIn: true })

    mockAuthReady.value = true
    await flushPromises()

    const submitBtn = wrapper.findAll('button').find(b => b.text().includes('Submit'))
    await submitBtn!.trigger('click')
    await flushPromises()

    expect(mockApiFetch).toHaveBeenCalledWith('/problems/42/submit', {
      method: 'POST',
      body: { code: 'def two_sum(nums, target):' },
    })
    expect(wrapper.find('.test-results').exists()).toBe(true)
  })

  it('shows review rating after passing submission for logged-in user', async () => {
    mockApiFetch.mockImplementation((path: string) => {
      if (path === '/problems/42') return Promise.resolve(MOCK_PROBLEM)
      if (path === '/problems/42/submit') return Promise.resolve(MOCK_SUBMISSION_PASS)
      return Promise.resolve(undefined)
    })
    const wrapper = mountPage({ loggedIn: true })

    mockAuthReady.value = true
    await flushPromises()

    const submitBtn = wrapper.findAll('button').find(b => b.text().includes('Submit'))
    await submitBtn!.trigger('click')
    await flushPromises()

    expect(wrapper.find('.review-rating').exists()).toBe(true)
  })

  it('does not show review rating after failed submission', async () => {
    mockApiFetch.mockImplementation((path: string) => {
      if (path === '/problems/42') return Promise.resolve(MOCK_PROBLEM)
      if (path === '/problems/42/submit') return Promise.resolve(MOCK_SUBMISSION_FAIL)
      return Promise.resolve(undefined)
    })
    const wrapper = mountPage({ loggedIn: true })

    mockAuthReady.value = true
    await flushPromises()

    const submitBtn = wrapper.findAll('button').find(b => b.text().includes('Submit'))
    await submitBtn!.trigger('click')
    await flushPromises()

    expect(wrapper.find('.review-rating').exists()).toBe(false)
  })

  it('shows submission error when API throws', async () => {
    mockApiFetch.mockImplementation((path: string) => {
      if (path === '/problems/42') return Promise.resolve(MOCK_PROBLEM)
      if (path === '/problems/42/submit') return Promise.reject({ data: { detail: 'Judge0 unavailable' } })
      return Promise.resolve(undefined)
    })
    const wrapper = mountPage({ loggedIn: true })

    mockAuthReady.value = true
    await flushPromises()

    const submitBtn = wrapper.findAll('button').find(b => b.text().includes('Submit'))
    await submitBtn!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Submission failed')
    expect(wrapper.text()).toContain('Judge0 unavailable')
  })

  it('requests hints via API', async () => {
    mockApiFetch.mockImplementation((path: string) => {
      if (path === '/problems/42') return Promise.resolve(MOCK_PROBLEM)
      if (path === '/problems/42/hints/0') return Promise.resolve({ hint: 'Try using a hash map', total: 2, index: 0 })
      return Promise.resolve(undefined)
    })
    const wrapper = mountPage()

    mockAuthReady.value = true
    await flushPromises()

    const hintBtn = wrapper.find('.hint-btn')
    await hintBtn.trigger('click')
    await flushPromises()

    expect(mockApiFetch).toHaveBeenCalledWith('/problems/42/hints/0')
    expect(wrapper.text()).toContain('Try using a hash map')
  })

  it('rating calls review API and shows confirmation', async () => {
    vi.useFakeTimers()
    mockApiFetch.mockImplementation((path: string) => {
      if (path === '/problems/42') return Promise.resolve(MOCK_PROBLEM)
      if (path === '/problems/42/submit') return Promise.resolve(MOCK_SUBMISSION_PASS)
      if (path === '/problems/42/review') return Promise.resolve(undefined)
      return Promise.resolve(undefined)
    })
    const wrapper = mountPage({ loggedIn: true })

    mockAuthReady.value = true
    await vi.advanceTimersByTimeAsync(0)
    await flushPromises()

    // Submit first
    const submitBtn = wrapper.findAll('button').find(b => b.text().includes('Submit'))
    await submitBtn!.trigger('click')
    await flushPromises()

    // Rate
    const rateBtn = wrapper.find('.rate-btn')
    await rateBtn.trigger('click')
    await flushPromises()

    expect(mockApiFetch).toHaveBeenCalledWith('/problems/42/review', {
      method: 'POST',
      body: { quality: 5 },
    })
    expect(wrapper.text()).toContain('Loading next problem')
  })

  it('hides review rating for anonymous users', async () => {
    mockApiFetch.mockResolvedValueOnce(MOCK_PROBLEM)
    const wrapper = mountPage({ loggedIn: false })

    mockAuthReady.value = true
    await flushPromises()

    expect(wrapper.find('.review-rating').exists()).toBe(false)
  })
})
