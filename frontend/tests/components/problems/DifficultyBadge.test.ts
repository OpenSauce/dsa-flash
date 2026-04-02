import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DifficultyBadge from '../../../components/problems/DifficultyBadge.vue'

describe('DifficultyBadge', () => {
  it('renders the difficulty text', () => {
    const wrapper = mount(DifficultyBadge, { props: { difficulty: 'easy' } })
    expect(wrapper.text()).toBe('easy')
  })

  it('applies green classes for easy', () => {
    const wrapper = mount(DifficultyBadge, { props: { difficulty: 'easy' } })
    expect(wrapper.find('span').classes()).toContain('bg-green-100')
    expect(wrapper.find('span').classes()).toContain('text-green-700')
  })

  it('applies yellow classes for medium', () => {
    const wrapper = mount(DifficultyBadge, { props: { difficulty: 'medium' } })
    expect(wrapper.find('span').classes()).toContain('bg-yellow-100')
    expect(wrapper.find('span').classes()).toContain('text-yellow-700')
  })

  it('applies red classes for hard', () => {
    const wrapper = mount(DifficultyBadge, { props: { difficulty: 'hard' } })
    expect(wrapper.find('span').classes()).toContain('bg-red-100')
    expect(wrapper.find('span').classes()).toContain('text-red-700')
  })
})
