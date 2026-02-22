<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from '#imports'
import { useAuth } from '~/composables/useAuth'

useSeoMeta({
  title: 'Sign Up | dsaflash.cards',
  description: 'Create a free account on dsaflash.cards to track your learning progress with spaced repetition.',
  robots: 'noindex, nofollow',
})

const { signup } = useAuth()
const router = useRouter()

const username = ref('')
const password = ref('')
const errorMsg = ref<string | null>(null)

async function onSignup() {
  errorMsg.value = null

  if (username.value.length < 3) {
    errorMsg.value = 'Username must be at least 3 characters'
    return
  }
  if (!/^[a-zA-Z0-9_]+$/.test(username.value)) {
    errorMsg.value = 'Username can only contain letters, numbers, and underscores'
    return
  }
  if (password.value.length < 8) {
    errorMsg.value = 'Password must be at least 8 characters'
    return
  }

  try {
    await signup(username.value, password.value)
    router.push('/')
  } catch (err: any) {
    const detail = err.data?.detail
    if (Array.isArray(detail)) {
      errorMsg.value = detail.map((e: any) => {
        const field = e.loc?.at(-1)
        return field ? `${field}: ${e.msg}` : e.msg
      }).join('. ')
    } else {
      errorMsg.value = detail || err.message || 'Signup failed'
    }
  }
}
</script>

<template>
  <div class="max-w-md mx-auto py-20 px-6">
    <h1 class="text-3xl font-bold mb-6">Sign Up</h1>
    <div v-if="errorMsg" class="text-red-500 mb-4">{{ errorMsg }}</div>

    <form @submit.prevent="onSignup" class="space-y-4">
      <div>
        <input v-model="username" type="text" placeholder="Username" required class="w-full border rounded px-3 py-2" />
        <p class="text-xs text-gray-400 mt-1">Letters, numbers, and underscores only</p>
      </div>
      <div>
        <input v-model="password" type="password" placeholder="Password" required
          class="w-full border rounded px-3 py-2" />
        <p class="text-xs text-gray-400 mt-1">At least 8 characters</p>
      </div>
      <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white rounded px-3 py-2">
        Create Account
      </button>
    </form>

    <p class="mt-4 text-sm text-gray-600">
      Already have an account?
      <NuxtLink to="/login" class="text-indigo-600 hover:underline">Log in</NuxtLink>
    </p>
  </div>
</template>
