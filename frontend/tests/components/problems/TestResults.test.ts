import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import TestResults from '../../../components/problems/TestResults.vue'

const passedResults = [
  { input: '[1,2,3]', expected: '6', actual: '6', passed: true },
  { input: '[0]', expected: '0', actual: '0', passed: true },
]

const mixedResults = [
  { input: '[1,2,3]', expected: '6', actual: '6', passed: true },
  { input: '[4,5]', expected: '9', actual: '8', passed: false },
]

describe('TestResults', () => {
  it('shows "All tests passed" when all pass', () => {
    const wrapper = mount(TestResults, {
      props: { results: passedResults, passed: true },
    })
    expect(wrapper.text()).toContain('All tests passed')
    expect(wrapper.text()).toContain('2/2')
  })

  it('shows "Tests failed" when some fail', () => {
    const wrapper = mount(TestResults, {
      props: { results: mixedResults, passed: false },
    })
    expect(wrapper.text()).toContain('Tests failed')
    expect(wrapper.text()).toContain('1/2')
  })

  it('shows solve time when provided', () => {
    const wrapper = mount(TestResults, {
      props: { results: passedResults, passed: true, solveTime: 272000 },
    })
    expect(wrapper.text()).toContain('Solved in 4:32')
  })

  it('does not show solve time when not provided', () => {
    const wrapper = mount(TestResults, {
      props: { results: passedResults, passed: true },
    })
    expect(wrapper.text()).not.toContain('Solved in')
  })

  it('shows actual output for failed tests', () => {
    const wrapper = mount(TestResults, {
      props: { results: mixedResults, passed: false },
    })
    expect(wrapper.text()).toContain('Actual:')
    expect(wrapper.text()).toContain('8')
  })

  it('applies green styling to passed tests', () => {
    const wrapper = mount(TestResults, {
      props: { results: passedResults, passed: true },
    })
    const cards = wrapper.findAll('.rounded-md.border')
    expect(cards[0].classes()).toContain('border-green-200')
  })

  it('applies red styling to failed tests', () => {
    const wrapper = mount(TestResults, {
      props: { results: mixedResults, passed: false },
    })
    const cards = wrapper.findAll('.rounded-md.border.p-3')
    const failedCard = cards.find(c => c.classes().includes('border-red-200'))
    expect(failedCard).toBeDefined()
  })
})
