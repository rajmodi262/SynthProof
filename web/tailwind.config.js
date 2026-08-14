/** @type {import('tailwindcss').Config} */

// The two accents are not decoration: `proved` is the formal upper bound and `audited` is
// the empirical lower bound. The distance between them is what this project measures, so
// the palette encodes the thesis rather than illustrating it.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bone: { DEFAULT: '#F0EFEA', deep: '#E4E2DA', edge: '#D2CFC4' },
        graphite: { DEFAULT: '#22242E', soft: '#4A4D5C', faint: '#7C8093' },
        stage: { DEFAULT: '#14151C', deep: '#0D0E13', line: '#2A2C38' },
        proved: { DEFAULT: '#4B46C4', lift: '#8F8AF0', wash: '#EAE9FA' },
        audited: { DEFAULT: '#C2622A', lift: '#E8964C', wash: '#FAEFE6' },
        signal: { ok: '#1D7A4C', warn: '#B5851C', bad: '#B2382F' },
      },
      fontFamily: {
        display: ['"Instrument Serif"', 'Georgia', 'serif'],
        sans: ['"Geist Sans"', 'system-ui', 'sans-serif'],
        mono: ['"Geist Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem', letterSpacing: '0.08em' }],
      },
      boxShadow: {
        // A recessed display sunk into an instrument casing, not a floating card.
        inset: 'inset 0 1px 3px rgba(0,0,0,0.55), inset 0 0 0 1px rgba(255,255,255,0.04)',
        panel: '0 1px 2px rgba(34,36,46,0.06), 0 8px 24px -12px rgba(34,36,46,0.18)',
      },
      keyframes: {
        sweep: { '0%': { transform: 'translateX(-100%)' }, '100%': { transform: 'translateX(300%)' } },
        blink: { '0%,100%': { opacity: '1' }, '50%': { opacity: '0.25' } },
      },
      animation: {
        sweep: 'sweep 1.6s cubic-bezier(0.4,0,0.2,1) infinite',
        blink: 'blink 1.4s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
