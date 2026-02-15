// Rehydrate auth state on every fresh load (SSR + client).
// Runs before any page renders, so user state is available immediately.
export default defineNuxtPlugin(async () => {
  const { user, tokenCookie, authReady } = useAuth()

  if (tokenCookie.value && !user.value) {
    try {
      user.value = await $fetch('/api/users/me', {
        headers: { Authorization: `Bearer ${tokenCookie.value}` },
      })
    } catch {
      tokenCookie.value = null
      user.value = null
    }
  }

  authReady.value = true
})
