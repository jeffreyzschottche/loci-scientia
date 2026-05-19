import type { Config } from 'tailwindcss';

export default {
  content: [
    './app/**/*.{vue,ts}',
    './components/**/*.{vue,ts}',
    './layouts/**/*.{vue,ts}',
    './pages/**/*.{vue,ts}',
    './plugins/**/*.{js,ts}',
    './composables/**/*.{js,ts}',
  ],
  theme: {
    extend: {
      colors: {
        loci: {
          yellow: '#facc15',
          'yellow-hover': '#fbbf24',
          'yellow-light': '#fde68a',
          'yellow-warm': '#f5d24a',
          black: '#111111',
          'black-deep': '#050505',
          white: '#ffffff',
          gray: {
            50: '#f5f5f5',
            100: '#ececec',
            200: '#e5e7eb',
            300: '#d6d3ce',
            400: '#9ca3af',
            500: '#6b7280',
          },
          cream: '#fcfbf9',
        },
      },
      borderRadius: {
        'loci': '20px',
        'loci-lg': '28px',
        'loci-full': '999px',
      },
      fontFamily: {
        sans: ['Inter', 'Helvetica Neue', 'Arial', 'sans-serif'],
      },
    },
  },
  plugins: [],
} satisfies Config;
