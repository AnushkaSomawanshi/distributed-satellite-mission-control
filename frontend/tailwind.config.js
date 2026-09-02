/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        space: {
          950: '#030712',
          900: '#0b1329',
          800: '#111c3a',
          700: '#1e294b'
        }
      }
    },
  },
  plugins: [],
}
