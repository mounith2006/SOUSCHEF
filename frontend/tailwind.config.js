/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cream: '#FFFDF8',
        card: '#FFFFFF',
        brand: {
          orange: '#F97316',
          peach: '#FFEDD5',
          dark: '#1F2937',
          muted: '#6B7280',
          border: '#E5E7EB',
          success: '#22C55E',
          error: '#EF4444',
        }
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        'soft-sm': '0 2px 8px -2px rgba(31, 41, 55, 0.05), 0 1px 4px -1px rgba(31, 41, 55, 0.03)',
        'soft': '0 4px 20px -2px rgba(31, 41, 55, 0.06), 0 2px 6px -1px rgba(31, 41, 55, 0.03)',
        'soft-lg': '0 10px 30px -4px rgba(31, 41, 55, 0.08), 0 4px 12px -2px rgba(31, 41, 55, 0.04)',
        'orange-glow': '0 0 35px 0 rgba(249, 115, 22, 0.25)',
        'green-glow': '0 0 35px 0 rgba(34, 197, 94, 0.25)',
      }
    },
  },
  plugins: [],
}
