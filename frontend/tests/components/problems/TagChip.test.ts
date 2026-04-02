import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import TagChip from '../../../components/problems/TagChip.vue'

describe('TagChip', () => {
  it('renders the tag text', () => {
    const wrapper = mount(TagChip, { props: { tag: 'Two Pointers' } })
    expect(wrapper.text()).toBe('Two Pointers')
  })

  it('applies active styles when active', () => {
    const wrapper = mount(TagChip, { props: { tag: 'DFS', active: true } })
    expect(wrapper.find('button').classes()).toContain('bg-purple-100')
  })

  it('applies inactive styles when not active', () => {
    const wrapper = mount(TagChip, { props: { tag: 'DFS', active: false } })
    expect(wrapper.find('button').classes()).toContain('bg-gray-50')
  })

  it('emits click on button press', async () => {
    const wrapper = mount(TagChip, { props: { tag: 'BFS' } })
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('click')).toBeTruthy()
  })
})
