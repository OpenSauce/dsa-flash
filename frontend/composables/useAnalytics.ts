import { onMounted, onBeforeUnmount } from 'vue'
import { useCookie, useRuntimeConfig } from '#imports'

interface AnalyticsEvent {
  event_type: string
  payload: Record<string, unknown>
}

export const useAnalytics = () => {
  const sessionId = useCookie('session_id', {
    default: () => globalThis.crypto?.randomUUID() ?? Math.random().toString(36).slice(2),
    maxAge: 60 * 60 * 24 * 365,
  })
  const { public: { apiBase } } = useRuntimeConfig()
  const tokenCookie = useCookie<string | null>('token')

  const buffer: AnalyticsEvent[] = []
  let flushTimer: ReturnType<typeof setInterval> | null = null

  const track = (eventType: string, payload: Record<string, unknown> = {}) => {
    buffer.push({ event_type: eventType, payload })
  }

  const flush = async () => {
    if (buffer.length === 0) return
    const events = buffer.splice(0, buffer.length)
    try {
      await $fetch(`${apiBase}/events/batch`, {
        method: 'POST',
        body: { events },
        headers: tokenCookie.value
          ? { Authorization: `Bearer ${tokenCookie.value}` }
          : {},
      })
    } catch (err) {
      // Re-queue on failure
      buffer.unshift(...events)
      console.error('analytics flush failed', err)
    }
  }

  const flushBeacon = () => {
    if (buffer.length === 0) return
    const events = buffer.splice(0, buffer.length)
    const blob = new Blob(
      [JSON.stringify({ events })],
      { type: 'application/json' },
    )
    navigator.sendBeacon(`${apiBase}/events/batch`, blob)
  }

  const onVisibilityChange = () => {
    if (document.visibilityState === 'hidden') {
      flushBeacon()
    }
  }

  const onBeforeUnload = () => {
    flushBeacon()
  }

  onMounted(() => {
    flushTimer = setInterval(flush, 5000)
    document.addEventListener('visibilitychange', onVisibilityChange)
    window.addEventListener('beforeunload', onBeforeUnload)
  })

  onBeforeUnmount(() => {
    if (flushTimer) {
      clearInterval(flushTimer)
      flushTimer = null
    }
    document.removeEventListener('visibilitychange', onVisibilityChange)
    window.removeEventListener('beforeunload', onBeforeUnload)
    flush()
  })

  return { track, flush, flushBeacon, sessionId }
}
