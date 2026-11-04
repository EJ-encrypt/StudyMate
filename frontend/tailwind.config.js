/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  // Toggled by src/lib/theme.ts. Most colours switch through the CSS
  // variables in index.css instead, so pages need no dark: variants.
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
      colors: {
        // Brand surfaces: the sidebar, primary buttons, game headers. Dark in
        // both themes, a little lighter in dark mode so they stand off the page.
        navy: {
          DEFAULT: "rgb(var(--navy) / <alpha-value>)",
          light: "rgb(var(--navy-light) / <alpha-value>)",
          dark: "#061530",
        },
        gold: {
          DEFAULT: "#D4AF37",
          light: "#E4C767",
          dark: "rgb(var(--gold-dark) / <alpha-value>)",
        },
        // Text, borders and tints: navy on light pages, near-white on dark.
        ink: "rgb(var(--ink) / <alpha-value>)",
        // Cards and inputs, and the page behind them.
        surface: "rgb(var(--surface) / <alpha-value>)",
        canvas: "rgb(var(--canvas) / <alpha-value>)",
      },
      boxShadow: {
        card: "0 1px 2px rgb(var(--shadow) / 0.06), 0 1px 3px rgb(var(--shadow) / 0.08)",
        lift: "0 4px 12px rgb(var(--shadow) / 0.10)",
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
