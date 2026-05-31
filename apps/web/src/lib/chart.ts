/** Shared chart theme tokens for Recharts, derived from the current theme. */
export function chartTokens(isDark: boolean) {
  return {
    grid: isDark ? 'oklch(0.28 0.02 250)' : 'oklch(0.92 0.005 240)',
    axis: isDark ? 'oklch(0.7 0.02 240)' : 'oklch(0.45 0.02 250)',
    line1: 'var(--color-chart-1)',
    line2: 'var(--color-chart-2)',
    bg: isDark ? 'oklch(0.2 0.015 250)' : 'white',
    fg: isDark ? 'oklch(0.96 0.005 240)' : 'oklch(0.18 0.02 250)',
  };
}
