/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
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
    },
  },
  plugins: [],
};
