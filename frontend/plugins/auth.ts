// Rehydrate auth state on every fresh load (SSR + client).
// Runs before any page renders, so user state is available immediately.
export default defineNuxtPlugin(async () => {
  const { user, tokenCookie, authReady } = useAuth()
  const { apiFetch } = useApiFetch()

  if (tokenCookie.value && !user.value) {
    try {
      user.value = await apiFetch('/users/me')
    } catch {
      tokenCookie.value = null
      user.value = null
    }
  }

  authReady.value = true
})
