export default defineNuxtConfig({
  runtimeConfig: {
    public: {
      apiBase: '/api',         // keep the nice short path
    },
  },

  routeRules: {
    '/api/**': { proxy: { to: 'http://backend:8000/**' } },
  },

  modules: [
    '@nuxtjs/tailwindcss',
    '@nuxtjs/google-fonts',
  ],

  css: [
    'highlight.js/styles/github.min.css'
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
