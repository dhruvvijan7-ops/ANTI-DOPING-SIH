/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f6f7f9",
          100: "#eceef2",
          200: "#d4d9e2",
          300: "#aeb7c7",
          400: "#818da5",
          500: "#616f8b",
          600: "#4d5873",
          700: "#40495f",
          800: "#383f51",
          900: "#22252f",
          950: "#12141b",
        },
        paper: {
          50: "#fbfaf8",
          100: "#f4f2ee",
          200: "#e6e2da",
        },
        signal: {
          50: "#eefaf8",
          100: "#d5f2ee",
          200: "#aee5e0",
          300: "#7cd0cb",
          400: "#4bb3b0",
          500: "#2f9694",
          600: "#237877",
          700: "#206060",
          800: "#1d4d4e",
          900: "#1b4142",
          950: "#0a2425",
        },
        amber: {
          500: "#e59f2b",
          600: "#c98317",
          700: "#a56612",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "SFMono-Regular", "ui-monospace", "Menlo", "Consolas", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(18,20,27,0.05), 0 1px 3px rgba(18,20,27,0.06)",
        lift: "0 4px 12px rgba(18,20,27,0.08)",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.2s ease-out both",
        "fade-up": "fade-up 0.3s ease-out both",
      },
    },
  },
  plugins: [],
};