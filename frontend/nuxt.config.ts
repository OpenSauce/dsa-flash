export default defineNuxtConfig({
  runtimeConfig: {
    public: {
      apiBase: '/api',         // keep the nice short path
    },
  },

  routeRules: {
    '/api/**': { proxy: { to: 'http://backend:8000/**' } },
    // e.g. /api/flashcards → http://localhost:8000/flashcards
  },

  modules: [
    '@nuxtjs/tailwindcss',
    '@nuxtjs/google-fonts',
  ],

  googleFonts: {
    families: {
      'Space Grotesk': [400, 500, 600, 700],
    },
    display: 'swap',   // avoids FOIT
    inject: true,      // <link> is injected during SSR
    download: true,    // fonts cached locally at build time
  },
})
