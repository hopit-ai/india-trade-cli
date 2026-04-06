/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/renderer/**/*.{js,jsx,ts,tsx,html}'],
  theme: {
    extend: {
      colors: {
        surface:  '#0d0d0d',
        panel:    '#111111',
        elevated: '#161616',
        border:   '#1e1e1e',
        text:     '#e8e8e8',
        muted:    '#666666',
        subtle:   '#444444',
        amber:    '#e06c00',
        'amber-dim': '#7a3a00',
        green:    '#52e07a',
        red:      '#e05252',
        blue:     '#5294e0',
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
