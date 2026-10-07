/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        carbon: '#000000',
        paper: '#ffffff',
        canvas: '#e5e5e5',
        mist: '#f3f3f3',
        ash: '#c6c6c6',
        smoke: '#979797',
        slate: '#444444',
        graphite: '#2f2f2f',
        mint: '#d1ffca',
        voltage: '#fff100',
      },
      fontFamily: {
        display: ['"Barlow Condensed"', 'Anton', '"Bebas Neue"', 'Impact', 'sans-serif'],
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"IBM Plex Mono"', 'monospace'],
      },
      borderRadius: {
        'card': '24px',
        'card-lg': '32px',
        'card-xl': '48px',
        'pill': '9999px',
      },
      boxShadow: {
        'none': 'none',
      }
    },
  },
  plugins: [],
}
