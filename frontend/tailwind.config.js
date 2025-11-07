/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html",
  ],
  theme: {
    extend: {
      colors: {
        // Custom color palette for signal coverage
        signal: {
          excellent: '#006400',
          good: '#228B22',
          fair: '#32CD32',
          poor: '#FFD700',
          verypoor: '#FF4500'
        }
      }
    },
  },
  plugins: [],
}