// composables/useAuth.ts
import { computed, onMounted } from 'vue'
import { useCookie, useRuntimeConfig } from '#imports'

interface UserInfo {
  name: string
}

interface TokenResponse {
  access_token: string
}

export const useAuth = () => {
  const user = useState<UserInfo | null>('user', () => null)
  const tokenCookie = useCookie<string | null>('token')

  const { public: { apiBase } } = useRuntimeConfig()

  const isLoggedIn = computed(() => !!user.value)

  onMounted(async () => {
    if (tokenCookie.value && !user.value) {
      try {
        const me = await $fetch<UserInfo>(
          `${apiBase}/users/me`,
          {
            headers: {
              Authorization: `Bearer ${tokenCookie.value}`,
            },
          }
        )
        user.value = me
      } catch {
        tokenCookie.value = null
        user.value = null
      }
    }
  })

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
    user.value = { name: username }
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
    await $fetch(
      `${apiBase}/auth/logout`,
      { method: 'POST' }
    )
  }

  return { user, isLoggedIn, login, signup, logout }
}
