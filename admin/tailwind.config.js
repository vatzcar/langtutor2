/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#7C9FE5',
        secondary: '#E8A0BF',
        accent: '#FFD36E',
        success: '#8ED1A5',
        error: '#E88B8B',
        textPrimary: '#2D3142',
        textSecondary: '#6B7280',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
