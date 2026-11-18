/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        space: '#05060F',
        panel: 'rgba(13,17,38,0.55)',
        neon: '#22D3EE',
        violet2: '#8B5CF6',
        emerald2: '#34D399',
        rose2: '#FB7185',
        amber2: '#FBBF24',
        ink: '#E6EDF7',
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        neon: '0 0 24px rgba(34,211,238,0.35)',
        rose: '0 0 24px rgba(251,113,133,0.35)',
        emerald: '0 0 24px rgba(52,211,153,0.35)',
        violet: '0 0 24px rgba(139,92,246,0.35)',
      },
      backdropBlur: { xs: '2px' },
      keyframes: {
        shimmer: { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } },
        pulseBeam: { '0%,100%': { opacity: '0.35' }, '50%': { opacity: '1' } },
        floaty: { '0%,100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-12px)' } },
      },
      animation: {
        shimmer: 'shimmer 2.4s linear infinite',
        pulseBeam: 'pulseBeam 2.2s ease-in-out infinite',
        floaty: 'floaty 5s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};