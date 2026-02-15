// composables/useAuth.ts
import { computed } from 'vue'
import { useCookie, useRuntimeConfig } from '#imports'

interface UserInfo {
  name: string
  is_admin: boolean
}

interface TokenResponse {
  access_token: string
}

export const useAuth = () => {
  const user = useState<UserInfo | null>('user', () => null)
  const tokenCookie = useCookie<string | null>('token', {
    maxAge: 60 * 60 * 24 * 7, // 7 days
    path: '/',
    sameSite: 'lax' as const,
  })
  const authReady = useState<boolean>('authReady', () => false)

  const { public: { apiBase } } = useRuntimeConfig()

  const isLoggedIn = computed(() => !!user.value)
  const isAdmin = computed(() => !!user.value?.is_admin)

  const login = async (username: string, password: string): Promise<void> => {
    const form = new URLSearchParams({ username, password })
    const { access_token } = await $fetch<TokenResponse>(
      `${apiBase}/token`,
      {
        method: 'POST',
        body: form,
      }
    )
    tokenCookie.value = access_token
    user.value = await $fetch<UserInfo>(`${apiBase}/users/me`, {
      headers: { Authorization: `Bearer ${access_token}` },
    })
  }

  const signup = async (username: string, password: string): Promise<void> => {
    await $fetch(
      `${apiBase}/signup`,
      {
        method: 'POST',
        body: { username, password },
      }
    )
  }

  const logout = async () => {
    tokenCookie.value = null
    user.value = null
    try {
      await $fetch(`${apiBase}/auth/logout`, { method: 'POST' })
    } catch {
      // best-effort — token may already be invalid
    }
  }

  return { user, isLoggedIn, isAdmin, login, signup, logout, authReady, tokenCookie }
}
