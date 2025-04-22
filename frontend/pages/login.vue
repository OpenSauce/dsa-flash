<script setup lang="ts">
const user = useState('user')

async function demoLogin () {
  user.value = { name: 'demo' }
  await navigateTo('/')
}
</script>

<template>
  <div class="max-w-md mx-auto py-20 px-6">
    <h1 class="text-3xl font-bold mb-6">Log in</h1>
    <p class="mb-8 text-gray-600">Auth coming soon. Click below to fake‑login for now.</p>
    <button @click="demoLogin" class="bg-indigo-600 text-white w-full py-2 rounded hover:bg-indigo-700">
      Continue as demo user
    </button>
  </div>
</template>

