<template>
  <div class="p-4 max-w-xl mx-auto">
    <h1 class="text-2xl font-bold mb-4">DSA Flashcards</h1>
    <ul>
      <li v-for="card in flashcards" :key="card.id" class="mb-2">
        <div class="p-4 border rounded">
          <p class="font-semibold">Q: {{ card.question }}</p>
          <p class="mt-2">A: {{ card.answer }}</p>
        </div>
      </li>
    </ul>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'
const flashcards = ref([])
const config = useRuntimeConfig()
onMounted(async () => {
  const { data } = await axios.get(`${config.public.apiBase}/flashcards`)
  flashcards.value = data
})
</script>
