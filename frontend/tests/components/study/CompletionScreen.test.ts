import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import CompletionScreen from '../../../components/study/CompletionScreen.vue'

// Stub NuxtLink as a simple anchor so we don't need Nuxt router
const NuxtLinkStub = defineComponent({
  name: 'NuxtLink',
  props: ['to'],
  setup(props, { slots }) {
    return () => h('a', { href: props.to }, slots.default?.())
  },
})

const defaultProps = {
  categoryName: 'System Design',
  categoryEmoji: '🏗️',
  cardsReviewed: 7,
  newConcepts: 4,
  reviewedConcepts: 3,
  runningTotal: 42,
  categoryTotal: 60,
  remainingCards: 3,
  hasMoreCards: true,
  isLoggedIn: true,
  mode: 'due',
}

function mountScreen(props: Partial<typeof defaultProps> = {}) {
  return mount(CompletionScreen, {
    props: { ...defaultProps, ...props },
    global: {
      stubs: { NuxtLink: NuxtLinkStub },
    },
  })
}

describe('CompletionScreen', () => {
  it('shows category name in the studied message', () => {
    const wrapper = mountScreen()
    expect(wrapper.text()).toContain('System Design concepts')
  })

  it('shows cards reviewed count', () => {
    const wrapper = mountScreen()
    expect(wrapper.text()).toContain('7')
  })

  it('shows encouragement message for auth users', () => {
    const wrapper = mountScreen()
    // encouragement paragraph is italic — check it's non-empty
    const italicEl = wrapper.find('p.italic')
    expect(italicEl.exists()).toBe(true)
    expect(italicEl.text().length).toBeGreaterThan(0)
  })

  it('shows "Keep going" button when hasMoreCards is true', () => {
    const wrapper = mountScreen({ hasMoreCards: true })
    const btn = wrapper.find('button')
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toContain('Keep going')
  })

  it('hides "Keep going" button when hasMoreCards is false', () => {
    const wrapper = mountScreen({ hasMoreCards: false })
    expect(wrapper.find('button').exists()).toBe(false)
  })

  it('"Try another domain" links to home page', () => {
    const wrapper = mountScreen()
    const links = wrapper.findAll('a')
    const homeLink = links.find(l => l.attributes('href') === '/')
    expect(homeLink).toBeDefined()
    expect(homeLink!.text()).toContain('Try another domain')
  })

  it('no dashboard link in completion screen', () => {
    const wrapper = mountScreen({ isLoggedIn: true })
    const links = wrapper.findAll('a')
    const dashLink = links.find(l => l.attributes('href') === '/dashboard')
    expect(dashLink).toBeUndefined()
  })

  it('anon users see category name and card count but not breakdown or running total', () => {
    const wrapper = mountScreen({
      isLoggedIn: false,
      runningTotal: null,
    })
    expect(wrapper.text()).toContain('System Design concepts')
    expect(wrapper.text()).toContain('7')
    // no running total
    expect(wrapper.text()).not.toContain('You now know')
    // anon CTA
    expect(wrapper.text()).toContain('Sign up')
  })

  it('renders "no concepts due" state when cardsReviewed is 0', () => {
    const wrapper = mountScreen({
      cardsReviewed: 0,
      newConcepts: 0,
      reviewedConcepts: 0,
      runningTotal: 0,
      hasMoreCards: false,
    })
    expect(wrapper.text()).toContain('No concepts due right now')
    // no "You reviewed" text
    expect(wrapper.text()).not.toContain('You reviewed')
  })

  it('"Try another domain" appears in "no cards due" state', () => {
    const wrapper = mountScreen({
      cardsReviewed: 0,
      newConcepts: 0,
      reviewedConcepts: 0,
      runningTotal: 0,
      hasMoreCards: false,
    })
    const links = wrapper.findAll('a')
    const homeLink = links.find(l => l.attributes('href') === '/')
    expect(homeLink).toBeDefined()
  })

  it('shows category-complete celebration when all concepts learned', () => {
    const wrapper = mountScreen({
      isLoggedIn: true,
      runningTotal: 60,
      categoryTotal: 60,
      cardsReviewed: 5,
    })
    expect(wrapper.text()).toContain('System Design complete!')
    expect(wrapper.text()).toContain('60 / 60 learned')
    expect(wrapper.text()).toContain("You've learned all")
  })

  it('does not show celebration when category is not complete', () => {
    const wrapper = mountScreen({
      isLoggedIn: true,
      runningTotal: 42,
      categoryTotal: 60,
    })
    expect(wrapper.text()).not.toContain('complete!')
    expect(wrapper.text()).not.toContain('/ 60 learned')
  })

  it('does not show "Learn new concepts" button', () => {
    const wrapper = mountScreen({
      isLoggedIn: true,
      mode: 'due',
      hasMoreCards: false,
    })
    const switchBtn = wrapper.findAll('button').find(b => b.text().includes('Learn new concepts'))
    expect(switchBtn).toBeUndefined()
  })

  it('encouragement message is non-empty and varies — mount multiple times', () => {
    const messages = new Set<string>()
    for (let i = 0; i < 20; i++) {
      const wrapper = mountScreen()
      const el = wrapper.find('p.italic')
      if (el.exists()) {
        messages.add(el.text())
      }
    }
    // With 5 possible messages and 20 mounts, statistically we get more than 1 unique
    expect(messages.size).toBeGreaterThan(1)
    for (const msg of messages) {
      expect(msg.length).toBeGreaterThan(0)
    }
  })
})
