// composables/useAuth.ts
import { computed } from 'vue'

// 1) Define your user shape
interface UserInfo {
  name: string
  // …add other fields here as needed
}

export const useAuth = () => {
  // 2) Tell useState that `user.value` will be UserInfo or null
  const user = useState<UserInfo | null>('user', () => null)

  // normalize any `undefined` into `null`
  if (user.value === undefined) user.value = null

  const isLoggedIn = computed(() => !!user.value)

  // 3) Annotate `info` so TS knows it must be a UserInfo
  const login = (info: UserInfo) => {
    user.value = info
  }

  const logout = () => {
    user.value = null
  }

  return { user, isLoggedIn, login, logout }
}
