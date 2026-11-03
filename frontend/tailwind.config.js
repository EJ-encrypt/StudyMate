/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
      colors: {
        navy: {
          DEFAULT: "#0A1F44",
          light: "#12305F",
          dark: "#061530",
        },
        gold: {
          DEFAULT: "#D4AF37",
          light: "#E4C767",
          dark: "#A9862B",
        },
      },
      boxShadow: {
        card: "0 1px 2px rgba(10,31,68,0.06), 0 1px 3px rgba(10,31,68,0.08)",
        lift: "0 4px 12px rgba(10,31,68,0.10)",
      },
      keyframes: {
        pop: { "0%": { transform: "scale(0.96)" }, "60%": { transform: "scale(1.03)" }, "100%": { transform: "scale(1)" } },
        shake: { "0%,100%": { transform: "translateX(0)" }, "25%": { transform: "translateX(-5px)" }, "75%": { transform: "translateX(5px)" } },
        "fade-in": { "0%": { opacity: 0, transform: "translateY(4px)" }, "100%": { opacity: 1, transform: "translateY(0)" } },
      },
      animation: {
        pop: "pop 0.3s ease-out",
        shake: "shake 0.3s ease-in-out",
        "fade-in": "fade-in 0.25s ease-out",
      },
    },
  },
  plugins: [],
};
