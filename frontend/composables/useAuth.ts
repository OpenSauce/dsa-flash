// composables/useAuth.ts
import { computed } from 'vue'
import { useCookie } from '#imports'

interface UserInfo {
  name: string
}

interface TokenResponse {
  access_token: string
}

export const useAuth = () => {
  const user = useState<UserInfo | null>('user', () => null)
  if (user.value === undefined) user.value = null

  const isLoggedIn = computed(() => !!user.value)
  const tokenCookie = useCookie('token')

  const login = async (username: string, password: string): Promise<void> => {
    const form = new URLSearchParams({ username, password })
    const { access_token } = await $fetch<TokenResponse>('/api/token', {
      method: 'POST',
      body: form,
    })
    tokenCookie.value = access_token
    user.value = { name: username }
  }

  const signup = async (username: string, password: string): Promise<void> => {
    await $fetch('/api/signup', {
      method: 'POST',
      body: { username, password },
    })
    // note: we do NOT log in here
  }

  const logout = () => {
    tokenCookie.value = null
    user.value = null
  }

  return { user, isLoggedIn, login, signup, logout }
}
