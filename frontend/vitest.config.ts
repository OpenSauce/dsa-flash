import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, '.'),
      '#imports': resolve(__dirname, './.nuxt/imports.d.ts'),
    },
  },
  test: {
    environment: 'happy-dom',
  },
})
