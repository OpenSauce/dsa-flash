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
  // persisted state across pages
  const user = useState<UserInfo | null>('user', () => null)
  const tokenCookie = useCookie<string | null>('token')

  // grab your API base URL from runtime config
  const { public: { apiBase } } = useRuntimeConfig()

  const isLoggedIn = computed(() => !!user.value)

  // 1) On mount, if we have a token but no user yet, fetch /users/me
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
        // token might be invalid/expired
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
    // set the user right away so UI updates immediately
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
    // inform backend to clear any server‐side session or cookie if needed
    await $fetch(
      `${apiBase}/auth/logout`,
      { method: 'POST' }
    )
  }

  return { user, isLoggedIn, login, signup, logout }
}
