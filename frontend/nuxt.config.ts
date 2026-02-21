export default defineNuxtConfig({
  app: {
    head: {
      title: 'dsaflash.cards – Flashcards for Engineers',
      meta: [
        { name: 'description', content: 'Free spaced repetition flashcards for engineers. Master data structures, algorithms, system design, AWS, Kubernetes, Docker, networking, and Big O — no signup required.' },
        { property: 'og:image', content: 'https://dsaflash.cards/social-preview.png' },
        { name: 'twitter:card', content: 'summary_large_image' },
        { name: 'twitter:image', content: 'https://dsaflash.cards/social-preview.png' }
      ],
      link: [
        { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' },
        { rel: 'apple-touch-icon', sizes: '180x180', href: '/apple-touch-icon.png' },
        { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/favicon-32x32.png' },
        { rel: 'icon', type: 'image/png', sizes: '16x16', href: '/favicon-16x16.png' },
        { rel: 'manifest', href: '/site.webmanifest' },
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
