// Semantic colors for learning progress, mastery, and due
// SVG hex values (for inline SVG fill/stroke attributes)
export const LEARNED_HEX = '#22c55e'   // green-500
export const LEARNED_TEXT_HEX = '#16a34a' // green-600
export const MASTERED_HEX = '#9333ea'  // purple-600
export const DUE_HEX = '#3b82f6'       // blue-500

// Tailwind classes (for template class bindings)
export const LEARNED_TEXT_CLASS = 'text-green-600'
export const MASTERED_TEXT_CLASS = 'text-purple-600'
export const DUE_TEXT_CLASS = 'text-blue-600'

export function colorForPct(pct: number): string {
  if (pct === 0) return '#d1d5db'    // gray
  if (pct === 100) return MASTERED_HEX
  if (pct >= 50) return LEARNED_HEX
  return LEARNED_TEXT_HEX
}
