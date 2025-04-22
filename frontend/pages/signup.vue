<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from '#imports'

const router = useRouter()
const username = ref('')
const password = ref('')
const errorMsg = ref<string|null>(null)

async function onSignup() {
  errorMsg.value = null
  try {
    await $fetch('/api/signup', {
      method: 'POST',
      body: { username: username.value, password: password.value }
    })
    // after signup, redirect to login
    router.push('/login')
  } catch (err: any) {
    errorMsg.value = err.data?.detail || 'Signup failed'
  }
}
</script>

<template>
  <div class="max-w-md mx-auto py-20 px-6">
    <h1 class="text-3xl font-bold mb-6">Sign Up</h1>
    <div v-if="errorMsg" class="text-red-500 mb-4">{{ errorMsg }}</div>

    <form @submit.prevent="onSignup" class="space-y-4">
      <input
        v-model="username"
        type="text"
        placeholder="Username"
        required
        class="w-full border rounded px-3 py-2"
      />
      <input
        v-model="password"
        type="password"
        placeholder="Password"
        required
        class="w-full border rounded px-3 py-2"
      />
      <button
        type="submit"
        class="w-full bg-indigo-600 hover:bg-indigo-700 text-white rounded px-3 py-2"
      >
        Create Account
      </button>
    </form>

    <p class="mt-4 text-sm text-gray-600">
      Already have an account?
      <NuxtLink to="/login" class="text-indigo-600 hover:underline">Log in</NuxtLink>
    </p>
  </div>
</template>
