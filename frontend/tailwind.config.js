/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        serif: ['"Newsreader"', '"Instrument Serif"', 'Georgia', 'serif'],
        sans: ['"Inter"', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', '"Helvetica Neue"', 'Arial', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        bg: 'var(--bg)',
        surface: {
          DEFAULT: 'var(--surface)',
          hover: 'var(--surface-hover)',
          active: 'var(--surface-active)',
        },
        border: {
          DEFAULT: 'var(--border)',
          subtle: 'var(--border-subtle)',
          focus: 'var(--border-focus)',
        },
        text: {
          DEFAULT: 'var(--text)',
          muted: 'var(--text-muted)',
          dim: 'var(--text-dim)',
        },
        accent: {
          DEFAULT: 'var(--accent)',
          hover: 'var(--accent-hover)',
          contrast: 'var(--accent-contrast)',
          subtle: 'var(--accent-subtle)',
          border: 'var(--accent-border)',
        },
        success: {
          DEFAULT: 'var(--success)',
          subtle: 'var(--success-subtle)',
        },
        danger: {
          DEFAULT: 'var(--danger)',
          subtle: 'var(--danger-subtle)',
        },
        brand: {
          50: '#f7f6f3',
          100: '#edebe6',
          200: '#dedad2',
          300: '#c5bfb3',
          400: '#a8a090',
          500: '#E8A33D',
          600: '#d49332',
          700: '#b87c24',
          800: '#8c5d18',
          900: '#5c3d0f',
          950: '#161618',
        },
      },
      borderRadius: {
        'card': '12px',
      }
    },
  },
  plugins: [],
}
