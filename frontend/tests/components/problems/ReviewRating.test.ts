import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ReviewRating from '../../../components/problems/ReviewRating.vue'

const defaultProps = {
  suggested: 'easy' as const,
  hintsUsed: 0,
}

const globalStubs = {
  NuxtLink: { template: '<a><slot /></a>', props: ['to'] },
}

function mountRating(props = {}) {
  return mount(ReviewRating, { props: { ...defaultProps, ...props }, global: { stubs: globalStubs } })
}

describe('ReviewRating', () => {
  it('renders three rating buttons', () => {
    const wrapper = mountRating()
    const buttons = wrapper.findAll('button')
    expect(buttons).toHaveLength(3)
    expect(wrapper.text()).toContain('Again')
    expect(wrapper.text()).toContain('Good')
    expect(wrapper.text()).toContain('Easy')
  })

  it('emits rate with quality 1 when Again clicked', async () => {
    const wrapper = mountRating()
    const buttons = wrapper.findAll('button')
    const againBtn = buttons.find(b => b.text().includes('Again'))
    await againBtn!.trigger('click')
    expect(wrapper.emitted('rate')).toBeTruthy()
    expect(wrapper.emitted('rate')![0]).toEqual([1])
  })

  it('emits rate with quality 3 when Good clicked', async () => {
    const wrapper = mountRating()
    const buttons = wrapper.findAll('button')
    const goodBtn = buttons.find(b => b.text().includes('Good'))
    await goodBtn!.trigger('click')
    expect(wrapper.emitted('rate')![0]).toEqual([3])
  })

  it('emits rate with quality 5 when Easy clicked', async () => {
    const wrapper = mountRating()
    const buttons = wrapper.findAll('button')
    const easyBtn = buttons.find(b => b.text().includes('Easy'))
    await easyBtn!.trigger('click')
    expect(wrapper.emitted('rate')![0]).toEqual([5])
  })

  it('shows ring on suggested button (easy)', () => {
    const wrapper = mountRating({ suggested: 'easy' })
    const buttons = wrapper.findAll('button')
    const easyBtn = buttons.find(b => b.text().includes('Easy'))
    expect(easyBtn!.classes().some(c => c.includes('ring-2'))).toBe(true)
  })

  it('shows ring on suggested button (good)', () => {
    const wrapper = mountRating({ suggested: 'good' })
    const buttons = wrapper.findAll('button')
    const goodBtn = buttons.find(b => b.text().includes('Good'))
    expect(goodBtn!.classes().some(c => c.includes('ring-2'))).toBe(true)
  })

  it('shows hints used message when hints > 0', () => {
    const wrapper = mountRating({ hintsUsed: 2 })
    expect(wrapper.text()).toContain('2 hints used')
  })

  it('does not show hints message when hintsUsed is 0', () => {
    const wrapper = mountRating({ hintsUsed: 0 })
    expect(wrapper.text()).not.toContain('hint')
  })

  it('shows interval labels', () => {
    const wrapper = mountRating()
    expect(wrapper.text()).toContain('~1d')
    expect(wrapper.text()).toContain('~4d')
    expect(wrapper.text()).toContain('~10d')
  })

  it('hides rating buttons when rated is true', () => {
    const wrapper = mountRating({ rated: true, nextReviewDate: 'Apr 8' })
    const buttons = wrapper.findAll('button')
    const ratingButtons = buttons.filter(b =>
      b.text().includes('Again') || b.text().includes('Good') || b.text().includes('Easy')
    )
    expect(ratingButtons).toHaveLength(0)
  })

  it('shows next review date when rated', () => {
    const wrapper = mountRating({ rated: true, nextReviewDate: 'Apr 8' })
    expect(wrapper.text()).toContain('Apr 8')
    expect(wrapper.text()).toContain('Next review')
  })

  it('shows "Next problem" button when rated', () => {
    const wrapper = mountRating({ rated: true, nextReviewDate: 'Apr 8' })
    expect(wrapper.text()).toContain('Next problem')
  })

  it('emits next-problem when Next problem button clicked', async () => {
    const wrapper = mountRating({ rated: true, nextReviewDate: 'Apr 8' })
    const nextBtn = wrapper.findAll('button').find(b => b.text().includes('Next problem'))
    await nextBtn!.trigger('click')
    expect(wrapper.emitted('next-problem')).toBeTruthy()
  })

  it('shows fallback text when nextReviewDate is null', () => {
    const wrapper = mountRating({ rated: true, nextReviewDate: null })
    expect(wrapper.text()).toContain('Scheduled for review')
  })

  it('Easy button uses green color scheme', () => {
    const wrapper = mountRating({ suggested: 'again' })
    const buttons = wrapper.findAll('button')
    const easyBtn = buttons.find(b => b.text().includes('Easy'))
    expect(easyBtn!.classes().some(c => c.includes('green'))).toBe(true)
  })
})
