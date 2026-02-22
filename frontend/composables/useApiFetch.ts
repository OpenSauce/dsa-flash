import { useCookie, useRuntimeConfig } from '#imports'

export const useApiFetch = () => {
  const { public: { apiBase } } = useRuntimeConfig()
  const tokenCookie = useCookie<string | null>('token')

  const apiFetch = <T>(path: string, opts: Omit<Parameters<typeof $fetch>[1], 'baseURL'> & {} = {}) => {
    const headers: Record<string, string> = {}
    if (opts.headers) {
      const incoming = opts.headers as Record<string, string>
      Object.assign(headers, incoming)
    }
    if (tokenCookie.value) {
      headers['Authorization'] = `Bearer ${tokenCookie.value}`
    }
    return $fetch<T>(`${apiBase}${path}`, { ...opts, headers })
  }

  return { apiFetch, tokenCookie, apiBase }
}
