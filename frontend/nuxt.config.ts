export default defineNuxtConfig({
  app: {
    head: {
      title: 'Flashcards for Engineers – dsaflash.cards',
      meta: [
        { name: 'description', content: 'Spaced repetition flashcards for engineers. Master data structures, algorithms, system design, AWS, Kubernetes, Docker, networking, and Big O — concepts that stick.' },
        // open-graph
        { property: 'og:title', content: 'Flashcards for Engineers – dsaflash.cards' },
        { property: 'og:description', content: 'Spaced repetition flashcards for engineers. Master data structures, algorithms, system design, AWS, Kubernetes, Docker, networking, and Big O.' },
        { property: 'og:image', content: 'https://dsaflash.cards/social-preview.png' },
        { property: 'og:url', content: 'https://dsaflash.cards' },
        { name: 'twitter:card', content: 'summary_large_image' },
        { name: 'twitter:title', content: 'Flashcards for Engineers – dsaflash.cards' },
        { name: 'twitter:description', content: 'Spaced repetition flashcards for engineers. Master data structures, algorithms, system design, AWS, Kubernetes, Docker, and networking.' },
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
    '/api/**': { proxy: { to: `${process.env.API_BASE || 'http://backend:8000'}/**` } },
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
