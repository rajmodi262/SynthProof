/** @type {import('tailwindcss').Config} */

function withOpacity(variableName) {
  return ({ opacityValue }) => {
    if (opacityValue !== undefined) {
      return `rgba(var(${variableName}), ${opacityValue})`
    }
    return `rgb(var(${variableName}))`
  }
}

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        paper: {
          DEFAULT: 'var(--paper)',
          2: 'var(--paper-2)',
        },
        card: {
          DEFAULT: 'var(--card)',
        },
        ink: {
          DEFAULT: withOpacity('--ink-rgb'),
        },
        muted: {
          DEFAULT: withOpacity('--muted-rgb'),
        },
        faint: {
          DEFAULT: withOpacity('--faint-rgb'),
        },
        line: {
          DEFAULT: withOpacity('--line-rgb'),
        },
        brass: {
          DEFAULT: withOpacity('--brass-rgb'),
          deep: 'var(--brass-deep)',
        },
        seal: {
          DEFAULT: withOpacity('--seal-rgb'),
          bg: 'var(--seal-bg)',
        },
        verify: {
          DEFAULT: withOpacity('--verify-rgb'),
          bg: 'var(--verify-bg)',
        },
        // Backward compatibility mappings for test suite and legacy components
        bone: { DEFAULT: 'var(--paper)', deep: 'var(--paper-2)', edge: 'var(--line)' },
        graphite: { DEFAULT: withOpacity('--ink-rgb'), soft: withOpacity('--muted-rgb'), faint: withOpacity('--faint-rgb') },
        stage: { DEFAULT: 'var(--paper-2)', deep: 'var(--paper)', line: 'var(--line)' },
        proved: { DEFAULT: withOpacity('--brass-rgb'), lift: withOpacity('--brass-rgb'), wash: 'var(--paper-2)' },
        audited: { DEFAULT: withOpacity('--brass-rgb'), lift: withOpacity('--brass-rgb'), wash: 'var(--paper-2)' },
        signal: { ok: withOpacity('--verify-rgb'), warn: '#D97706', bad: withOpacity('--seal-rgb') },
      },
      fontFamily: {
        display: ['"Instrument Serif"', 'Georgia', 'serif'],
        sans: ['"Geist Sans"', 'system-ui', 'sans-serif'],
        mono: ['"Geist Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem', letterSpacing: '0.08em' }],
      },
      borderRadius: {
        'sm': '4px',
        'md': '8px',
        'lg': '12px',
        'xl': '16px',
        'pill': '999px',
      },
      boxShadow: {
        e0: 'var(--shadow-e0)',
        e1: 'var(--shadow-e1)',
        e2: 'var(--shadow-e2)',
        inset: 'var(--shadow-inset)',
        brass: 'var(--shadow-brass)',
      },
      spacing: {
        '0': '0px',
        '1': '4px',
        '2': '8px',
        '3': '12px',
        '4': '16px',
        '5': '20px',
        '6': '24px',
        '8': '32px',
        '10': '40px',
        '12': '48px',
        '16': '64px',
        '20': '80px',
        '24': '96px',
      },
    },
  },
  plugins: [],
}
