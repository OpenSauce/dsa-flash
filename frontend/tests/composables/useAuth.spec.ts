import { vi, describe, it, expect, beforeAll, beforeEach } from 'vitest'
import { ref } from 'vue'

const mockUseCookie = vi.fn()
vi.mock('#imports', () => ({ useCookie: mockUseCookie }))

const mockUseState = vi.fn()
const mockFetch = vi.fn()

let useAuth: typeof import('../../composables/useAuth').useAuth

beforeAll(async () => {
  vi.stubGlobal('useState', mockUseState)
  vi.stubGlobal('useCookie', mockUseCookie)
  vi.stubGlobal('$fetch', mockFetch)

    ; ({ useAuth } = await import('../../composables/useAuth'))
})

describe('useAuth composable', () => {
  let userRef: ReturnType<typeof ref>
  let cookieRef: ReturnType<typeof ref>

  beforeEach(() => {
    userRef = ref(null)
    cookieRef = ref(null)

    mockUseState.mockReturnValue(userRef)
    mockUseCookie.mockReturnValue(cookieRef)
    mockFetch.mockReset()
  })

  it('login sets token cookie and user state', async () => {
    mockFetch.mockResolvedValue({ access_token: 'token123' })
    const { login } = useAuth()

    await login('alice', 'secret')

    expect(cookieRef.value).toBe('token123')
    expect(userRef.value).toEqual({ name: 'alice' })
  })

  it('signup calls the signup endpoint without logging in', async () => {
    mockFetch.mockResolvedValue(undefined)
    const { signup, user } = useAuth()

    await signup('bob', 'hunter2')

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/signup',
      { method: 'POST', body: { username: 'bob', password: 'hunter2' } }
    )
    expect(user.value).toBe(null)
  })

  it('logout clears both cookie and user', () => {
    userRef.value = { name: 'carol' }
    cookieRef.value = 'tokenXYZ'

    const { logout } = useAuth()
    logout()

    expect(userRef.value).toBe(null)
    expect(cookieRef.value).toBe(null)
  })

  it('isLoggedIn reflects user state', () => {
    const { isLoggedIn } = useAuth()

    userRef.value = null
    expect(isLoggedIn.value).toBe(false)

    userRef.value = { name: 'dave' }
    expect(isLoggedIn.value).toBe(true)
  })
})
