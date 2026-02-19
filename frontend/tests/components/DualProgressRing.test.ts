import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DualProgressRing from '../../components/DualProgressRing.vue'

const INNER_CIRC = 75.398

describe('DualProgressRing', () => {
  it('renders an SVG with correct aria-label for partial progress', () => {
    const wrapper = mount(DualProgressRing, {
      props: { learnedPct: 38, masteredPct: 0 },
    })
    const svg = wrapper.find('svg')
    expect(svg.exists()).toBe(true)
    expect(svg.attributes('aria-label')).toBe('38% learned, 0% mastered')
  })

  it('shows aria-label "100% mastered" when fully mastered', () => {
    const wrapper = mount(DualProgressRing, {
      props: { learnedPct: 100, masteredPct: 100 },
    })
    const svg = wrapper.find('svg')
    expect(svg.attributes('aria-label')).toBe('100% mastered')
  })

  it('outer arc stroke-dashoffset reflects learnedPct', () => {
    const wrapper = mount(DualProgressRing, {
      props: { learnedPct: 50, masteredPct: 0 },
    })
    // The outer arc is the second circle (index 1, after the track circle)
    const circles = wrapper.findAll('circle')
    // circles[0] = outer track, circles[1] = outer arc, circles[2] = inner track, circles[3] = inner arc
    const outerArc = circles[1]
    expect(outerArc.attributes('stroke-dashoffset')).toBe('50')
  })

  it('inner arc stroke-dashoffset reflects masteredPct', () => {
    const wrapper = mount(DualProgressRing, {
      props: { learnedPct: 100, masteredPct: 50 },
    })
    const circles = wrapper.findAll('circle')
    const innerArc = circles[3]
    const expectedOffset = (INNER_CIRC - (50 / 100) * INNER_CIRC).toFixed(3)
    // dashoffset should be approximately INNER_CIRC * 0.5
    const actualOffset = parseFloat(innerArc.attributes('stroke-dashoffset') ?? '0')
    expect(actualOffset).toBeCloseTo(parseFloat(expectedOffset), 1)
  })

  it('shows gold checkmark when masteredPct is 100', () => {
    const wrapper = mount(DualProgressRing, {
      props: { learnedPct: 100, masteredPct: 100 },
    })
    const texts = wrapper.findAll('text')
    const checkmark = texts.find(t => t.text().includes('✓'))
    expect(checkmark).toBeDefined()
  })

  it('shows learnedPct as center text by default', () => {
    const wrapper = mount(DualProgressRing, {
      props: { learnedPct: 38, masteredPct: 0 },
    })
    const texts = wrapper.findAll('text')
    const centerText = texts.find(t => t.text().includes('38%'))
    expect(centerText).toBeDefined()
  })

  it('shows learnedPct even when learnedPct is 100 (mastery only on hover)', () => {
    const wrapper = mount(DualProgressRing, {
      props: { learnedPct: 100, masteredPct: 19 },
    })
    const texts = wrapper.findAll('text')
    const centerText = texts.find(t => t.text().includes('100%'))
    expect(centerText).toBeDefined()
  })

  it('shows masteredPct on hover with purple color', async () => {
    const wrapper = mount(DualProgressRing, {
      props: { learnedPct: 60, masteredPct: 20 },
    })
    await wrapper.find('svg').trigger('mouseenter')
    const texts = wrapper.findAll('text')
    const centerText = texts.find(t => t.text().includes('20%'))
    expect(centerText).toBeDefined()
    expect(centerText?.attributes('fill')).toBe('#9333ea')
  })

  it('shows learned color when not hovered', () => {
    const wrapper = mount(DualProgressRing, {
      props: { learnedPct: 60, masteredPct: 20 },
    })
    const texts = wrapper.findAll('text')
    const centerText = texts.find(t => t.text().includes('60%'))
    expect(centerText).toBeDefined()
    expect(centerText?.attributes('fill')).toBe('#16a34a')
  })

  it('0% learned shows outer arc dashoffset of 100 (no arc visible)', () => {
    const wrapper = mount(DualProgressRing, {
      props: { learnedPct: 0, masteredPct: 0 },
    })
    const circles = wrapper.findAll('circle')
    const outerArc = circles[1]
    expect(outerArc.attributes('stroke-dashoffset')).toBe('100')
  })

  it('applies default size class w-14 h-14 to SVG', () => {
    const wrapper = mount(DualProgressRing, {
      props: { learnedPct: 50, masteredPct: 25 },
    })
    const svg = wrapper.find('svg')
    expect(svg.classes()).toContain('w-14')
    expect(svg.classes()).toContain('h-14')
  })

  it('applies custom size class when provided', () => {
    const wrapper = mount(DualProgressRing, {
      props: { learnedPct: 50, masteredPct: 25, size: 'w-20 h-20' },
    })
    const svg = wrapper.find('svg')
    expect(svg.classes()).toContain('w-20')
    expect(svg.classes()).toContain('h-20')
  })

  it('clamps mastered arc to not exceed learned arc', () => {
    const wrapper = mount(DualProgressRing, {
      props: { learnedPct: 30, masteredPct: 80 },
    })
    const circles = wrapper.findAll('circle')
    const innerArc = circles[3]
    // mastered should be clamped to learnedPct=30, offset = INNER_CIRC * (1 - 0.30)
    const expectedOffset = INNER_CIRC - (30 / 100) * INNER_CIRC
    const actualOffset = parseFloat(innerArc.attributes('stroke-dashoffset') ?? '0')
    expect(actualOffset).toBeCloseTo(expectedOffset, 1)
  })
})
