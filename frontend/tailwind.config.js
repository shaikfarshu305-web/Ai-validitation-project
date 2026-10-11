/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          darkest: '#180E0A',
          dark: '#2A1B14',
          coffee: '#3F281D',
          medium: '#5C3D2E',
          hazel: '#7D543E',
          lightBrown: '#9E775F',
          beige: '#D9C8B4',
          creamDark: '#EDE3D5',
          cream: '#F7F3EB',
          creamLight: '#FCFAF6',
          white: '#FFFFFF',
          border: '#E4D7C5',
          borderDark: '#C9B59F',
        },
        verdict: {
          pass: '#15803D',
          passBg: '#DCFCE7',
          passBorder: '#86EFAC',
          needs: '#B45309',
          needsBg: '#FEF3C7',
          needsBorder: '#FCD34D',
          fail: '#B91C1C',
          failBg: '#FEE2E2',
          failBorder: '#FCA5A5',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'sans-serif'],
      },
      boxShadow: {
        'soft': '0 2px 10px rgba(42, 27, 20, 0.05)',
        'medium': '0 4px 20px rgba(42, 27, 20, 0.08)',
        'lift': '0 10px 25px -5px rgba(42, 27, 20, 0.1), 0 8px 10px -6px rgba(42, 27, 20, 0.06)',
      }
    },
  },
  plugins: [],
}
