import { vi, describe, it, expect, beforeEach } from 'vitest'
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'

// --- Stub Nuxt auto-imports as globals ---

const mockApiFetch = vi.fn()
const mockIsLoggedIn = ref(false)
const mockAuthReady = ref(false)
const mockTrack = vi.fn()

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
vi.stubGlobal('useRoute', () => ({ params: {} }))
vi.stubGlobal('useRouter', () => ({ push: vi.fn() }))
vi.stubGlobal('ref', ref)
vi.stubGlobal('computed', computed)
vi.stubGlobal('watch', watch)
vi.stubGlobal('onMounted', onMounted)
vi.stubGlobal('onBeforeUnmount', onBeforeUnmount)

import ProblemsIndex from '../../../pages/problems/index.vue'

const MOCK_PROBLEMS = [
  { id: 1, title: 'Two Sum', difficulty: 'easy', category: 'Arrays', tags: ['hash-map'], due_status: 'due' },
  { id: 2, title: 'Merge Sort', difficulty: 'medium', category: 'Sorting', tags: ['divide-conquer'], due_status: null },
  { id: 3, title: 'LRU Cache', difficulty: 'hard', category: 'Arrays', tags: ['hash-map', 'linked-list'], due_status: 'new' },
]

const globalStubs = {
  Breadcrumb: { template: '<nav />' },
  ProblemsTagChip: { template: '<span class="tag-chip" @click="$emit(\'click\')"><slot /></span>', props: ['tag', 'active'] },
  ProblemsDifficultyBadge: { template: '<span class="badge" />', props: ['difficulty'] },
  NuxtLink: { template: '<a><slot /></a>', props: ['to'] },
}

function mountPage(opts: { loggedIn?: boolean } = {}) {
  mockIsLoggedIn.value = opts.loggedIn ?? false
  mockAuthReady.value = false
  return mount(ProblemsIndex, {
    global: { stubs: globalStubs },
  })
}

describe('Problems Index Page', () => {
  beforeEach(() => {
    mockApiFetch.mockReset()
    mockTrack.mockReset()
    mockIsLoggedIn.value = false
    mockAuthReady.value = false
  })

  it('shows loading state before auth is ready', () => {
    mockApiFetch.mockResolvedValue([])
    const wrapper = mountPage()
    expect(wrapper.text()).toContain('Loading problems...')
  })

  it('renders problem list after fetch', async () => {
    mockApiFetch.mockResolvedValue(MOCK_PROBLEMS)
    const wrapper = mountPage()

    mockAuthReady.value = true
    await flushPromises()

    expect(mockApiFetch).toHaveBeenCalledWith('/problems')
    expect(wrapper.text()).toContain('Two Sum')
    expect(wrapper.text()).toContain('Merge Sort')
    expect(wrapper.text()).toContain('LRU Cache')
  })

  it('shows error state on fetch failure', async () => {
    mockApiFetch.mockRejectedValue({ data: { detail: 'Server error' } })
    const wrapper = mountPage()

    mockAuthReady.value = true
    await flushPromises()

    expect(wrapper.text()).toContain('Server error')
  })

  it('shows empty state when no problems', async () => {
    mockApiFetch.mockResolvedValue([])
    const wrapper = mountPage()

    mockAuthReady.value = true
    await flushPromises()

    expect(wrapper.text()).toContain('No problems yet')
  })

  it('shows due count banner for logged-in user', async () => {
    mockApiFetch.mockResolvedValue(MOCK_PROBLEMS)
    const wrapper = mountPage({ loggedIn: true })

    mockAuthReady.value = true
    await flushPromises()

    expect(wrapper.text()).toContain('1 problem due today')
  })

  it('shows "no problems due" when logged in with zero due', async () => {
    const noDue = MOCK_PROBLEMS.map(p => ({ ...p, due_status: 'new' }))
    mockApiFetch.mockResolvedValue(noDue)
    const wrapper = mountPage({ loggedIn: true })

    mockAuthReady.value = true
    await flushPromises()

    expect(wrapper.text()).toContain('No problems due')
  })

  it('sorts due problems first', async () => {
    mockApiFetch.mockResolvedValue(MOCK_PROBLEMS)
    const wrapper = mountPage()

    mockAuthReady.value = true
    await flushPromises()

    const rows = wrapper.findAll('tr').filter(r => r.text().includes('Sum') || r.text().includes('Sort') || r.text().includes('LRU'))
    expect(rows[0].text()).toContain('Two Sum')
  })

  it('filters by difficulty', async () => {
    mockApiFetch.mockResolvedValue(MOCK_PROBLEMS)
    const wrapper = mountPage()

    mockAuthReady.value = true
    await flushPromises()

    const diffSelect = wrapper.findAll('select')[1]
    await diffSelect.setValue('hard')
    await nextTick()

    expect(wrapper.text()).toContain('LRU Cache')
    expect(wrapper.text()).not.toContain('Two Sum')
    expect(wrapper.text()).not.toContain('Merge Sort')
  })

  it('filters by category', async () => {
    mockApiFetch.mockResolvedValue(MOCK_PROBLEMS)
    const wrapper = mountPage()

    mockAuthReady.value = true
    await flushPromises()

    const catSelect = wrapper.findAll('select')[0]
    await catSelect.setValue('Sorting')
    await nextTick()

    expect(wrapper.text()).toContain('Merge Sort')
    expect(wrapper.text()).not.toContain('Two Sum')
  })

  it('shows "no match" when filters exclude everything', async () => {
    mockApiFetch.mockResolvedValue(MOCK_PROBLEMS)
    const wrapper = mountPage()

    mockAuthReady.value = true
    await flushPromises()

    const catSelect = wrapper.findAll('select')[0]
    await catSelect.setValue('Arrays')
    const diffSelect = wrapper.findAll('select')[1]
    await diffSelect.setValue('medium')
    await nextTick()

    expect(wrapper.text()).toContain('No problems match your filters')
  })

  it('shows status column only when logged in', async () => {
    mockApiFetch.mockResolvedValue(MOCK_PROBLEMS)

    // Anonymous: no status column
    const anonWrapper = mountPage({ loggedIn: false })
    mockAuthReady.value = true
    await flushPromises()
    const anonHeaders = anonWrapper.findAll('th').map(th => th.text())
    expect(anonHeaders).not.toContain('Status')

    // Logged in: status column present
    mockApiFetch.mockResolvedValue(MOCK_PROBLEMS)
    mockAuthReady.value = false
    const authWrapper = mountPage({ loggedIn: true })
    mockAuthReady.value = true
    await flushPromises()
    const authHeaders = authWrapper.findAll('th').map(th => th.text())
    expect(authHeaders).toContain('Status')
  })
})
