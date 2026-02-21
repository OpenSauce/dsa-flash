import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Card from '../../../components/study/Card.vue'

const defaultProps = {
  front: '**What is a hash table?**',
  back: 'A data structure that maps keys to values.',
  revealed: false,
  showFlipHint: true,
}

function mountCard(props: Partial<typeof defaultProps> = {}) {
  return mount(Card, { props: { ...defaultProps, ...props } })
}

describe('Card', () => {
  it('shows flip hint when not revealed and showFlipHint is true', () => {
    const wrapper = mountCard()
    expect(wrapper.text()).toContain('Tap to reveal answer')
  })

  it('hides flip hint when card is revealed', () => {
    const wrapper = mountCard({ revealed: true })
    expect(wrapper.text()).not.toContain('Tap to reveal answer')
  })

  it('hides flip hint when showFlipHint is false', () => {
    const wrapper = mountCard({ showFlipHint: false })
    expect(wrapper.text()).not.toContain('Tap to reveal answer')
  })

  it('hides flip hint when showFlipHint is not passed', () => {
    const wrapper = mount(Card, {
      props: {
        front: '**What is a hash table?**',
        back: 'A data structure that maps keys to values.',
        revealed: false,
      },
    })
    expect(wrapper.text()).not.toContain('Tap to reveal answer')
  })

  it('shows desktop Space hint only at sm+ breakpoint via class', () => {
    const wrapper = mountCard()
    const spaceHint = wrapper.find('.hidden.sm\\:block')
    expect(spaceHint.exists()).toBe(true)
    expect(spaceHint.text()).toContain('or press Space')
  })

  it('renders front content as markdown', () => {
    const wrapper = mountCard()
    expect(wrapper.find('strong').text()).toBe('What is a hash table?')
  })

  it('emits flip on click', async () => {
    const wrapper = mountCard()
    await wrapper.trigger('click')
    expect(wrapper.emitted('flip')).toBeTruthy()
  })

  it('shows subtle icon when not revealed and showFlipHint is false', () => {
    const wrapper = mountCard({ showFlipHint: false })
    const subtleIcon = wrapper.find('svg')
    expect(subtleIcon.exists()).toBe(true)
  })

  it('does not show subtle icon or hint when card is revealed', () => {
    const wrapper = mountCard({ revealed: true })
    expect(wrapper.text()).not.toContain('Tap to reveal answer')
    expect(wrapper.text()).not.toContain('or press Space')
    expect(wrapper.find('.mt-4').exists()).toBe(false)
  })
})
