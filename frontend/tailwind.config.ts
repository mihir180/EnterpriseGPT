import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // Interactive accent — indigo-violet. Distinct from Claude's terracotta
        // and ChatGPT's green/black, closer to Gemini's cool register but solid,
        // not a gradient, so it stays calm in an enterprise setting.
        brand: {
          50: "#f1f1fe",
          100: "#e5e4fd",
          200: "#cccafb",
          300: "#a8a5f7",
          400: "#8480f2",
          500: "#6a65ef",
          600: "#5b5fef", // primary accent
          700: "#4a3fd1",
          800: "#3d34a8",
          900: "#332d84",
        },
        // Warm near-black used for the unified sidebar (nav + chat history).
        ink: {
          50: "#f6f6f7",
          100: "#e8e7ea",
          400: "#6f6c78",
          500: "#4d4a56",
          700: "#2a2830",
          800: "#1e1c24",
          900: "#17151d",
          950: "#111017",
        },
        // Soft off-white app canvas (lighter/neutraler than Claude's cream,
        // so it doesn't read as a direct lift).
        paper: {
          DEFAULT: "#fafaf9",
          raised: "#ffffff",
        },
      },
      fontFamily: {
        sans: [
          "var(--font-inter)",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
        display: ["var(--font-fraunces)", "ui-serif", "Georgia", "serif"],
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem",
      },
      boxShadow: {
        composer: "0 2px 10px -2px rgb(0 0 0 / 0.08), 0 0 0 1px rgb(0 0 0 / 0.04)",
        "composer-focus":
          "0 4px 18px -4px rgb(91 95 239 / 0.25), 0 0 0 1px rgb(91 95 239 / 0.35)",
      },
    },
  },
  plugins: [],
};
export default config;
