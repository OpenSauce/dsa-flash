export function colorForPct(pct: number): string {
  if (pct === 0) return '#d1d5db'    // gray
  if (pct === 100) return '#f59e0b'  // gold
  if (pct >= 50) return '#22c55e'    // green
  return '#6366f1'                   // indigo
}
