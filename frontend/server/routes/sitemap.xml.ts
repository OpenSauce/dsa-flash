import { defineEventHandler, setResponseHeader } from 'h3'

const SITE_URL = 'https://dsaflash.cards'

const STATIC_PAGES = [
  { loc: '/', changefreq: 'weekly', priority: '1.0' },
  { loc: '/about', changefreq: 'monthly', priority: '0.6' },
]

export default defineEventHandler(async (event) => {
  const apiBase = process.env.API_BASE || 'http://backend:8000'
  let categories: Array<{ slug: string }> = []

  try {
    categories = await $fetch<Array<{ slug: string }>>(`${apiBase}/categories`)
  } catch (e) {
    console.error('Sitemap: failed to fetch categories', e)
  }

  const categoryPages = categories.map((cat) => ({
    loc: `/category/${cat.slug}`,
    changefreq: 'weekly',
    priority: '0.8',
  }))

  const allPages = [...STATIC_PAGES, ...categoryPages]

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${allPages
  .map(
    (page) => `  <url>
    <loc>${SITE_URL}${page.loc}</loc>
    <changefreq>${page.changefreq}</changefreq>
    <priority>${page.priority}</priority>
  </url>`
  )
  .join('\n')}
</urlset>`

  setResponseHeader(event, 'content-type', 'application/xml; charset=utf-8')
  return xml
})
