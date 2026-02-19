<script setup lang="ts">
import { definePageMeta, useHead, watch } from '#imports'

const { isLoggedIn, isAdmin, logout, authReady } = useAuth()
const { streak, fetchStreak } = useStreak()
const route = useRoute()

const mobileMenuOpen = ref(false)

watch(
  [authReady, isLoggedIn],
  async ([ready, loggedIn]) => {
    if (!ready) return // don't clear streak while auth is initializing
    if (loggedIn) {
      if (!streak.value) await fetchStreak() // skip if already hydrated from SSR
    } else {
      streak.value = null
    }
  },
  { immediate: true }
)

watch(
  () => route.path,
  () => {
    mobileMenuOpen.value = false
  }
)

function closeMobileMenu() {
  mobileMenuOpen.value = false
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && mobileMenuOpen.value) closeMobileMenu()
}

</script>

<template>
  <div class="min-h-screen flex flex-col font-sans overflow-x-hidden" @keydown="onKeydown">
    <!-- Header -->
    <header class="bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 text-white shadow-md">
      <div class="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        <NuxtLink to="/" class="text-2xl sm:text-3xl font-tektur font-bold tracking-tighter drop-shadow-lg">
          📚 dsaflash.cards
        </NuxtLink>

        <!-- Right‑side nav -->
        <nav class="flex items-center gap-6 text-sm font-medium h-8">
          <NuxtLink to="https://github.com/OpenSauce/dsa-flash-cards" target="_blank"
            class="flex items-center hidden sm:inline text-white hover:opacity-80 transition-opacity">
            <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path
                d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.726-4.042-1.61-4.042-1.61C4.422 17.07 3.633 16.7 3.633 16.7c-1.087-.744.083-.729.083-.729 1.205.084 1.84 1.236 1.84 1.236 1.07 1.834 2.809 1.304 3.495.997.108-.776.418-1.304.76-1.604-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.47-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23a11.5 11.5 0 013.003-.404c1.02.005 2.045.137 3.003.404 2.285-1.552 3.29-1.23 3.29-1.23.645 1.653.24 2.873.12 3.176.77.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.48 5.92.43.372.81 1.102.81 2.222 0 1.606-.015 2.896-.015 3.286 0 .322.21.694.825.577C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
            </svg>
          </NuxtLink>

          <!-- 🔐 Auth area -->
          <div>
            <div v-if="authReady">
              <div v-if="!isLoggedIn" class="flex items-center gap-3">
                <NuxtLink to="/login"
                  class="px-3 py-1 rounded-md transition-transform hover:scale-105 hover:bg-white/10">Log&nbsp;in
                </NuxtLink>
                <NuxtLink to="/signup"
                  class="bg-white text-indigo-600 font-semibold px-3 py-1 rounded-md transition-transform hover:scale-105 hover:bg-white/90">
                  Sign&nbsp;up
                </NuxtLink>
              </div>
              <div v-else>
                <!-- Desktop nav (sm and up) -->
                <div class="hidden sm:flex items-center gap-3">
                  <span
                    v-if="streak && streak.current_streak > 0"
                    class="flex items-center gap-1 text-sm font-medium"
                    :title="streak ? `${streak.current_streak} day streak` : ''"
                  >
                    <svg class="w-4 h-4 text-orange-300" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                      <path d="M12 23c-3.866 0-7-3.134-7-7 0-3.037 2.5-6.5 5-9 .396-.396 1.058-.104 1.058.464 0 1.5 1.5 3.5 3 3.5-.442-2-1-4.5 0-7.5.167-.5.833-.5 1 0 1.5 4.5 4.942 6.5 4.942 9.536 0 3.866-3.134 7-7 7z" />
                    </svg>
                    <span>{{ streak.current_streak }}</span>
                  </span>
                  <NuxtLink to="/dashboard" class="hover:underline">Dashboard</NuxtLink>
                  <NuxtLink v-if="isAdmin" to="/admin" class="hover:underline">Admin</NuxtLink>
                  <button @click="logout().then(() => window.location.href = '/')" class="px-3 py-1 rounded-md hover:bg-white/10">Log&nbsp;out</button>
                </div>

                <!-- Mobile hamburger button -->
                <button
                  class="sm:hidden flex items-center justify-center w-8 h-8 rounded-md hover:bg-white/10 transition-colors"
                  :aria-expanded="mobileMenuOpen"
                  aria-label="Toggle navigation menu"
                  @click="mobileMenuOpen = !mobileMenuOpen"
                >
                  <svg v-if="!mobileMenuOpen" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                  <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <div v-else class="flex items-center gap-3 min-h-[36px]">
              <!-- Empty spacer div matching the expected height -->
              <span class="invisible">Loading</span>
            </div>
          </div>

        </nav>
      </div>

      <!-- Mobile dropdown menu (logged-in only) -->
      <div
        v-if="mobileMenuOpen && isLoggedIn"
        class="sm:hidden bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 shadow-lg"
      >
        <div class="px-4 py-3 flex flex-col gap-1 text-sm font-medium">
          <div v-if="streak && streak.current_streak > 0" class="flex items-center gap-2 px-3 py-2 text-white/80">
            <svg class="w-4 h-4 text-orange-300" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M12 23c-3.866 0-7-3.134-7-7 0-3.037 2.5-6.5 5-9 .396-.396 1.058-.104 1.058.464 0 1.5 1.5 3.5 3 3.5-.442-2-1-4.5 0-7.5.167-.5.833-.5 1 0 1.5 4.5 4.942 6.5 4.942 9.536 0 3.866-3.134 7-7 7z" />
            </svg>
            <span>{{ streak.current_streak }} day streak</span>
          </div>
          <NuxtLink
            to="/dashboard"
            class="px-3 py-2 rounded-md hover:bg-white/10 transition-colors"
            @click="closeMobileMenu"
          >
            Dashboard
          </NuxtLink>
          <NuxtLink
            v-if="isAdmin"
            to="/admin"
            class="px-3 py-2 rounded-md hover:bg-white/10 transition-colors"
            @click="closeMobileMenu"
          >
            Admin
          </NuxtLink>
          <button
            class="text-left px-3 py-2 rounded-md hover:bg-white/10 transition-colors"
            @click="closeMobileMenu(); logout().then(() => window.location.href = '/')"
          >
            Log&nbsp;out
          </button>
        </div>
      </div>
    </header>

    <main class="flex-1 bg-gray-50">
      <div class="max-w-5xl mx-auto px-4 pt-6 pb-10">
        <slot />
      </div>
    </main>

    <footer class="border-t text-center py-4 text-sm text-gray-600">
      © {{ new Date().getFullYear() }}
      <br class="block sm:hidden" />
      <span class="bg-clip-text text-transparent bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500">Technical knowledge that sticks</span>
      <span class="mx-2 text-gray-300 hidden sm:inline" aria-hidden="true">·</span>
      <NuxtLink to="/about" class="hover:underline hidden sm:inline">Learn more</NuxtLink>
    </footer>
  </div>
</template>
