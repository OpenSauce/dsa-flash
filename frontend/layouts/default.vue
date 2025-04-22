<script setup lang="ts">
const { isLoggedIn, login, logout } = useAuth()
</script>

<template>
  <div class="min-h-screen flex flex-col font-sans">
    <!-- Header -->
    <header class="bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 text-white">
      <div class="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        <NuxtLink to="/" class="text-2xl sm:text-3xl font-bold tracking-wide">
          dsaflash.cards
        </NuxtLink>

        <!-- Right‑side nav -->
        <nav class="flex items-center gap-6 text-sm font-medium">
          <NuxtLink to="/about"                       class="hover:underline hidden sm:inline">About</NuxtLink>
          <NuxtLink to="https://github.com/OpenSauce/dsa-flash-cards" target="_blank" class="hover:underline hidden sm:inline">
            GitHub
          </NuxtLink>

<!-- 🔐 Auth area -->
<div v-if="!isLoggedIn" class="flex items-center gap-3">
  <NuxtLink to="/login"  class="px-3 py-1 rounded-md hover:bg-white/10">Log&nbsp;in</NuxtLink>
  <NuxtLink to="/signup" class="bg-white text-indigo-600 font-semibold px-3 py-1 rounded-md hover:bg-white/90">
    Sign&nbsp;up
  </NuxtLink>
</div>

<div v-else class="flex items-center gap-3">
  <NuxtLink to="/dashboard" class="hover:underline">Dashboard</NuxtLink>
  <button @click="user.value = null" class="px-3 py-1 rounded-md hover:bg-white/10">Log&nbsp;out</button>
</div>

        </nav>
      </div>
    </header>

    <main class="flex-1">
      <slot />
    </main>

    <footer class="border-t text-center py-4 text-gray-500 text-sm">
      © {{ new Date().getFullYear() }} dsaflash.cards • Built with Nuxt 3 & Tailwind
    </footer>
  </div>
</template>
