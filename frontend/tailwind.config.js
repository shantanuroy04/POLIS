/** POLIS design tokens — UX §Appendix A. Implementation Plan task 1.7.
 *
 * Components compose from these. A raw hex value in a component is a review
 * failure: it breaks the light/dark token swap and the validated chart palette.
 */
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: {
          page: 'var(--surface-page)',
          card: 'var(--surface-card)',
          sunken: 'var(--surface-sunken)',
          hover: 'var(--surface-hover)',
        },
        ink: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          muted: 'var(--text-muted)',
          inverse: 'var(--text-inverse)',
        },
        line: { DEFAULT: 'var(--border)', strong: 'var(--border-strong)' },
        accent: {
          DEFAULT: 'var(--accent)',
          hover: 'var(--accent-hover)',
          subtle: 'var(--accent-subtle)',
        },
        // Severity — STATUS tokens, reserved (UX §4.3).
        // Never used for a chart series; never the sole carrier of meaning
        // (always icon + uppercase text + colour).
        sev: {
          normal: '#898781',
          info: 'var(--accent)',
          low: '#fab219',
          medium: '#ec835a',
          high: '#d03b3b',
          critical: '#d03b3b', // distinguished from `high` by inverted fill + icon
        },
        // Chart series — slots 1..3 ONLY, then "other" (UX §6.1).
        // This palette was validated with the dataviz validator against POLIS's
        // own surfaces (all-pairs CVD deltaE 9.2 light / 9.4 dark). Do not extend
        // to a 4th hue: fold the tail into `other` or facet into small multiples.
        series: {
          1: 'var(--series-1)',
          2: 'var(--series-2)',
          3: 'var(--series-3)',
          other: 'var(--border-strong)',
        },
        chart: {
          grid: 'var(--chart-grid)',
          axis: 'var(--chart-axis)',
          label: 'var(--chart-label)',
        },
      },
      fontFamily: {
        sans: ['system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['ui-monospace', 'Cascadia Code', 'Source Code Pro', 'monospace'],
      },
      fontSize: {
        display: ['40px', { lineHeight: '44px', fontWeight: '600' }],
        h1: ['28px', { lineHeight: '36px', fontWeight: '600' }],
        h2: ['20px', { lineHeight: '28px', fontWeight: '600' }],
        h3: ['16px', { lineHeight: '24px', fontWeight: '600' }],
        body: ['14px', { lineHeight: '22px' }],
        // Ingested article text: read for minutes, not seconds.
        content: ['16px', { lineHeight: '26px' }],
        small: ['13px', { lineHeight: '20px' }],
        micro: ['11px', { lineHeight: '16px', fontWeight: '600', letterSpacing: '0.04em' }],
      },
      borderRadius: { sm: '4px', md: '6px', lg: '8px' },
    },
  },
  plugins: [],
};
