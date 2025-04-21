import { defineNuxtConfig } from 'nuxt'
export default defineNuxtConfig({
  modules: ['@pinia/nuxt'],
  css: ['@/assets/css/tailwind.css'],
  vite: { server: { host: true } },
  runtimeConfig: {
    public: {
      apiBase: process.env.API_BASE || 'http://localhost:8000'
    }
  }
})
