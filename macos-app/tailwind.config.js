/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/renderer/**/*.{js,jsx,ts,tsx,html}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        surface:  'var(--color-surface)',
        panel:    'var(--color-panel)',
        elevated: 'var(--color-elevated)',
        border:   'var(--color-border)',
        text:     'var(--color-text)',
        muted:    'var(--color-muted)',
        subtle:   'var(--color-subtle)',
        amber:    'var(--color-amber)',
        'amber-dim': 'var(--color-amber-dim)',
        green:    'var(--color-green)',
        red:      'var(--color-red)',
        blue:     'var(--color-blue)',
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', '"Fira Code"', 'Menlo', 'monospace'],
        ui:   ['-apple-system', 'BlinkMacSystemFont', '"Helvetica Neue"', 'sans-serif'],
      },
      keyframes: {
        'fade-slide': {
          '0%':   { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-slide': 'fade-slide 0.35s ease-out',
      },
    },
  },
  plugins: [],
}
