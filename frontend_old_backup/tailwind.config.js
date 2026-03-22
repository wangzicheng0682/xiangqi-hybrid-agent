/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'china-red': '#C41E3A',
        'ink-black': '#2C3E50',
        'gilt-gold': '#D4AF37',
        'paper-white': '#F5F5DC',
      },
      backgroundImage: {
        'board-pattern': "url('/assets/wood_texture.png')",
      },
      fontFamily: {
        'serif': ['"Noto Serif SC"', 'STZhongsong', 'simsun', 'serif'],
      }
    },
  },
  plugins: [],
}
