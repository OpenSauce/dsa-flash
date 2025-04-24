<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from '#imports'
import { useAuth } from '~/composables/useAuth'

const { login } = useAuth()
const router = useRouter()

const username = ref('')
const password = ref('')
const errorMsg = ref<string | null>(null)

async function onLogin() {
  errorMsg.value = null

  try {
    // now all HTTP + cookie logic is in useAuth.login()
    await login(username.value, password.value)

    // redirect on success
    router.push('/')
  } catch (err: any) {
    // surfacing any API error
    errorMsg.value = err.data?.detail || 'Login failed'
  }
}
</script>

<template>
  <div class="max-w-md mx-auto py-20 px-6">
    <h1 class="text-3xl font-bold mb-6">Log In</h1>
    <div v-if="errorMsg" class="text-red-500 mb-4">{{ errorMsg }}</div>

    <form @submit.prevent="onLogin" class="space-y-4">
      <input v-model="username" type="text" placeholder="Username" required class="w-full border rounded px-3 py-2" />
      <input v-model="password" type="password" placeholder="Password" required
        class="w-full border rounded px-3 py-2" />
      <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white rounded px-3 py-2">
        Continue
      </button>
    </form>

    <p class="mt-4 text-sm text-gray-600">
      Need an account?
      <NuxtLink to="/signup" class="text-indigo-600 hover:underline">Sign up</NuxtLink>
    </p>
  </div>
</template>
