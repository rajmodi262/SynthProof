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
        stage: { DEFAULT: '#0C0D12', deep: '#07080B', line: '#1F222E' },
        proved: { DEFAULT: '#4F46E5', lift: '#818CF8', wash: '#EEF2FF' },
        audited: { DEFAULT: '#D97706', lift: '#FBBF24', wash: '#FFFBEB' },
        signal: { ok: '#10B981', warn: '#F59E0B', bad: '#EF4444' },
        cyber: {
          neon: '#06B6D4',
          violet: '#8B5CF6',
          pink: '#EC4899',
          amber: '#F59E0B',
          emerald: '#10B981',
          grid: 'rgba(99, 102, 241, 0.08)',
        },
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
        inset: 'inset 0 1px 3px rgba(0,0,0,0.65), inset 0 0 0 1px rgba(255,255,255,0.06)',
        panel: '0 4px 20px -2px rgba(0,0,0,0.25), 0 0 0 1px rgba(255,255,255,0.05)',
        glowProved: '0 0 25px -4px rgba(79, 70, 229, 0.45)',
        glowAudited: '0 0 25px -4px rgba(217, 119, 6, 0.45)',
        glowNeon: '0 0 25px -4px rgba(6, 182, 212, 0.45)',
        glowBad: '0 0 25px -4px rgba(239, 68, 68, 0.45)',
      },
      keyframes: {
        sweep: { '0%': { transform: 'translateX(-100%)' }, '100%': { transform: 'translateX(300%)' } },
        blink: { '0%,100%': { opacity: '1' }, '50%': { opacity: '0.25' } },
        laserScan: {
          '0%': { transform: 'translateY(-100%)', opacity: '0' },
          '15%': { opacity: '0.8' },
          '85%': { opacity: '0.8' },
          '100%': { transform: 'translateY(100%)', opacity: '0' },
        },
        pulseGlow: {
          '0%, 100%': { opacity: '0.6', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.04)' },
        },
        glitch: {
          '0%': { transform: 'translate(0)' },
          '20%': { transform: 'translate(-2px, 2px)' },
          '40%': { transform: 'translate(-2px, -2px)' },
          '60%': { transform: 'translate(2px, 2px)' },
          '80%': { transform: 'translate(2px, -2px)' },
          '100%': { transform: 'translate(0)' },
        },
      },
      animation: {
        sweep: 'sweep 1.6s cubic-bezier(0.4,0,0.2,1) infinite',
        blink: 'blink 1.4s ease-in-out infinite',
        laserScan: 'laserScan 3s ease-in-out infinite',
        pulseGlow: 'pulseGlow 2.5s ease-in-out infinite',
        glitch: 'glitch 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94) both',
      },
    },
  },
  plugins: [],
}
