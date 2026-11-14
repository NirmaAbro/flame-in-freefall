import type { Config } from "tailwindcss";

/**
 * IGNIS design tokens.
 * - "space"  : the dark navy base (page, panels, borders)
 * - "flame"  : warm accent, used for actions and highlights
 * - "diffuse": cool blue accent, the colour of a microgravity diffusion flame
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        space: {
          950: "#060b16",
          900: "#0a1222",
          800: "#0f1a30",
          700: "#182641",
          600: "#26375a",
          400: "#7d8db0",
          300: "#a5b2cf",
          200: "#cbd5e8",
          100: "#e8edf7",
        },
        flame: { 300: "#ffb27a", 400: "#ff9650", 500: "#f57a2c", 600: "#d95f14" },
        diffuse: { 300: "#9fd3ff", 400: "#6bb8f5", 500: "#3d96e0" },
      },
      fontFamily: {
        // Serif for headlines, system sans for everything else. No web-font download needed.
        display: ["Georgia", "Cambria", "'Times New Roman'", "serif"],
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "'Segoe UI'", "Roboto", "sans-serif"],
      },
      keyframes: {
        breathe: {
          "0%, 100%": { transform: "scale(1)", opacity: "0.95" },
          "50%": { transform: "scale(1.04)", opacity: "1" },
        },
      },
      animation: { breathe: "breathe 6s ease-in-out infinite" },
    },
  },
  plugins: [],
};

export default config;
