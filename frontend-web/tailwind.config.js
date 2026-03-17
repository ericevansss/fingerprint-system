/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui"],
      },
      colors: {
        navy: {
          900: "#0b0f19",
          800: "#0f172a",
          700: "#111827"
        },
        indigo: {
          500: "#6366f1",
          600: "#4f46e5"
        },
        cyan: {
          400: "#22d3ee"
        }
      },
      boxShadow: {
        glow: "0 0 30px rgba(79, 70, 229, 0.25)",
        card: "0 16px 40px rgba(2, 6, 23, 0.45)"
      }
    }
  },
  plugins: []
};
