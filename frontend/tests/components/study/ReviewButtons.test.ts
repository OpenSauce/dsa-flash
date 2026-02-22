import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ReviewButtons from '../../../components/study/ReviewButtons.vue'

const defaultProps = {
  revealed: true,
  buttonsEnabled: true,
  mode: 'due',
}

type ReviewButtonsProps = Partial<typeof defaultProps> & {
  projectedIntervals?: Record<string, string> | null
}
function mountButtons(props: ReviewButtonsProps = {}) {
  return mount(ReviewButtons, { props: { ...defaultProps, ...props } })
}

describe('ReviewButtons', () => {
  it('shows rating buttons when revealed', () => {
    const wrapper = mountButtons()
    expect(wrapper.text()).toContain('Again')
    expect(wrapper.text()).toContain('Almost')
    expect(wrapper.text()).toContain('I know it')
  })

  it('hides buttons when not revealed', () => {
    const wrapper = mountButtons({ revealed: false })
    expect(wrapper.text()).not.toContain('Again')
    expect(wrapper.text()).not.toContain('Almost')
    expect(wrapper.text()).not.toContain('I know it')
  })

  it('emits rate with "again" when Again button is clicked', async () => {
    const wrapper = mountButtons()
    const buttons = wrapper.findAll('button')
    const againBtn = buttons.find(b => b.text().includes('Again'))
    expect(againBtn).toBeDefined()
    await againBtn!.trigger('click')
    expect(wrapper.emitted('rate')).toBeTruthy()
    expect(wrapper.emitted('rate')![0]).toEqual(['again'])
  })

  it('emits rate with "good" when Almost button is clicked', async () => {
    const wrapper = mountButtons()
    const buttons = wrapper.findAll('button')
    const almostBtn = buttons.find(b => b.text().includes('Almost'))
    expect(almostBtn).toBeDefined()
    await almostBtn!.trigger('click')
    expect(wrapper.emitted('rate')).toBeTruthy()
    expect(wrapper.emitted('rate')![0]).toEqual(['good'])
  })

  it('emits rate with "easy" when "I know it" button is clicked', async () => {
    const wrapper = mountButtons()
    const buttons = wrapper.findAll('button')
    const knowItBtn = buttons.find(b => b.text().includes('I know it'))
    expect(knowItBtn).toBeDefined()
    await knowItBtn!.trigger('click')
    expect(wrapper.emitted('rate')).toBeTruthy()
    expect(wrapper.emitted('rate')![0]).toEqual(['easy'])
  })

  it('does not emit rate when buttonsEnabled is false', async () => {
    const wrapper = mountButtons({ buttonsEnabled: false })
    const buttons = wrapper.findAll('button')
    for (const btn of buttons) {
      await btn.trigger('click')
    }
    expect(wrapper.emitted('rate')).toBeFalsy()
  })

  it('buttons have disabled attribute when buttonsEnabled is false', () => {
    const wrapper = mountButtons({ buttonsEnabled: false })
    const buttons = wrapper.findAll('button')
    for (const btn of buttons) {
      expect(btn.attributes('disabled')).toBeDefined()
    }
  })

  it('shows keyboard hint "Press 1, 2, or 3"', () => {
    const wrapper = mountButtons()
    expect(wrapper.text()).toContain('Press 1, 2, or 3')
  })

  it('shows "Again", "Almost", "I know it" labels in due mode', () => {
    const wrapper = mountButtons({ mode: 'due' })
    expect(wrapper.text()).toContain('Again')
    expect(wrapper.text()).toContain('Almost')
    expect(wrapper.text()).toContain('I know it')
    expect(wrapper.text()).not.toContain('Tricky')
  })

  it('does not have isLoggedIn prop — works for all users regardless of auth state', () => {
    // ReviewButtons no longer takes isLoggedIn prop — verify it renders fine without it
    const wrapper = mountButtons()
    expect(wrapper.text()).toContain('Again')
    expect(wrapper.text()).toContain('Almost')
    expect(wrapper.text()).toContain('I know it')
  })

  // ── projectedIntervals tests ──────────────────────────────────────────

  it('shows projected intervals on all three buttons when projectedIntervals is provided', () => {
    const projectedIntervals = { '1': '1d', '3': '4d', '5': '16d' }
    const wrapper = mountButtons({ projectedIntervals })
    expect(wrapper.text()).toContain('1d')
    expect(wrapper.text()).toContain('4d')
    expect(wrapper.text()).toContain('16d')
  })

  it('does not show interval text when projectedIntervals is null', () => {
    const wrapper = mountButtons({ projectedIntervals: null })
    // No interval-formatted text like "1d", "4d" etc should appear
    expect(wrapper.text()).not.toMatch(/\d+d/)
    expect(wrapper.text()).not.toMatch(/\d+w/)
    expect(wrapper.text()).not.toMatch(/\d+mo/)
  })

  it('does not show interval text when projectedIntervals is not provided', () => {
    const wrapper = mountButtons()
    expect(wrapper.text()).not.toMatch(/\d+d/)
    expect(wrapper.text()).not.toMatch(/\d+w/)
    expect(wrapper.text()).not.toMatch(/\d+mo/)
  })

  it('maps quality 1 interval to Again button', () => {
    const projectedIntervals = { '1': '1d', '3': '4d', '5': '16d' }
    const wrapper = mountButtons({ projectedIntervals })
    const buttons = wrapper.findAll('button')
    const againBtn = buttons.find(b => b.text().includes('Again'))
    expect(againBtn).toBeDefined()
    expect(againBtn!.text()).toContain('1d')
    expect(againBtn!.text()).not.toContain('4d')
    expect(againBtn!.text()).not.toContain('16d')
  })

  it('maps quality 3 interval to Almost button', () => {
    const projectedIntervals = { '1': '1d', '3': '4d', '5': '16d' }
    const wrapper = mountButtons({ projectedIntervals })
    const buttons = wrapper.findAll('button')
    const almostBtn = buttons.find(b => b.text().includes('Almost'))
    expect(almostBtn).toBeDefined()
    expect(almostBtn!.text()).toContain('4d')
    expect(almostBtn!.text()).not.toContain('1d')
    expect(almostBtn!.text()).not.toContain('16d')
  })

  it('maps quality 5 interval to "I know it" button', () => {
    const projectedIntervals = { '1': '1d', '3': '4d', '5': '16d' }
    const wrapper = mountButtons({ projectedIntervals })
    const buttons = wrapper.findAll('button')
    const knowItBtn = buttons.find(b => b.text().includes('I know it'))
    expect(knowItBtn).toBeDefined()
    expect(knowItBtn!.text()).toContain('16d')
    expect(knowItBtn!.text()).not.toContain('4d')
  })
})
