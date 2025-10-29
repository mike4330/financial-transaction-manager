/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Midnight Ember Theme - Warm Dark Mode
        dark: {
          // Backgrounds - Rich, warm darks instead of cold grays
          bg: '#0a0806',        // Deep espresso black
          surface: '#1a1612',   // Rich coffee brown
          card: '#252017',      // Warm charcoal
          elevated: '#2d251a',  // Elevated surface
          border: '#3a2f20',    // Subtle warm borders
        },
        ember: {
          // Primary accent - Warm copper/amber family
          50: '#fef7ed',   // Lightest cream
          100: '#fdedd3',  // Warm cream
          200: '#fbd6a5',  // Light amber
          300: '#f7b76d',  // Medium amber
          400: '#f29432',  // Rich amber
          500: '#ed7014',  // Primary ember (our main accent)
          600: '#de550a',  // Deep ember
          700: '#b83f0c',  // Darker ember
          800: '#933210',  // Very dark ember
          900: '#772b11',  // Deepest ember
        },
        warm: {
          // Secondary warm grays with amber undertones
          50: '#fafaf9',
          100: '#f5f5f4', 
          200: '#e7e5e4',
          300: '#d6d3d1',
          400: '#a8a29e',
          500: '#78716c',  // Medium warm gray
          600: '#57534e',  // Dark warm gray
          700: '#44403c',  // Darker warm gray
          800: '#292524',  // Very dark warm gray
          900: '#1c1917',  // Deepest warm gray
        }
      },
      fontFamily: {
        // Slightly more distinctive fonts
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        // Custom shadows with warm tints
        'ember-glow': '0 0 20px rgba(237, 112, 20, 0.15)',
        'ember-glow-lg': '0 0 40px rgba(237, 112, 20, 0.2)',
        'dark-elevated': '0 8px 32px rgba(0, 0, 0, 0.4)',
      },
      animation: {
        'ember-pulse': 'ember-pulse 2s ease-in-out infinite',
        'fade-in': 'fade-in 0.3s ease-out',
      },
      keyframes: {
        'ember-pulse': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(-10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        }
      }
    },
  },
  plugins: [],
}

