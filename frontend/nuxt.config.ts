export default defineNuxtConfig({
  app: {
    head: {
      title: 'Learn DSA with Flashcards – dsaflash.cards',
      meta: [
        { name: 'description', content: 'Master data structures, algorithms, and Big O notation through efficient flashcards. Built for DSA learners and coding interview preparation.' },
        // open-graph
        { property: 'og:title', content: 'Learn DSA with Flashcards' },
        { property: 'og:description', content: 'Boost your DSA skills with beautifully crafted flashcards covering data structures, algorithms, and Big O concepts.' },
        { property: 'og:image', content: 'https://dsaflash.cards/social-preview.png' },
        { property: 'og:url', content: 'https://dsaflash.cards' },
        { name: 'twitter:card', content: 'summary_large_image' },
        { name: 'twitter:title', content: 'Learn DSA with Flashcards' },
        { name: 'twitter:description', content: 'Master data structures, algorithms, and Big O notation through efficient flashcards.' },
        { name: 'twitter:image', content: 'https://dsaflash.cards/social-preview.png' }
      ],
      link: [
        { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' },
        { rel: 'apple-touch-icon', sizes: '180x180', href: '/apple-touch-icon.png' },
        { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/favicon-32x32.png' },
        { rel: 'icon', type: 'image/png', sizes: '16x16', href: '/favicon-16x16.png' },
        { rel: 'manifest', href: '/site.webmanifest' },
        { rel: 'canonical', href: 'https://dsaflash.cards' }
      ],
    }
  },
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
      'Tektur': [700, 800],
    },
    display: 'swap',
    inject: true,
    download: true,
  },
})
