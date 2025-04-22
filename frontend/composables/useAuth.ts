// composables/useAuth.ts
export const useAuth = () => {
  const user = useState('user', () => null)
  if (user.value === undefined) user.value = null   // always normalise
  const isLoggedIn = computed(() => !!user.value)
  const login  = (info = { name: 'demo' }) => (user.value = info)
  const logout = () => (user.value = null)
  return { user, isLoggedIn, login, logout }
}

