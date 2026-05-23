import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        tb: {
          accent:          "var(--tb-accent)",
          "accent-hover":  "var(--tb-accent-hover)",
          black:           "var(--tb-black)",
          bg:              "var(--tb-bg)",
          surface:         "var(--tb-surface)",
          "surface-2":     "var(--tb-surface-2)",
          "text-primary":  "var(--tb-text-primary)",
          "text-secondary":"var(--tb-text-secondary)",
          "text-tertiary": "var(--tb-text-tertiary)",
          border:          "var(--tb-border)",
          "border-strong": "var(--tb-border-strong)",
          // status
          "status-active":     "var(--tb-status-active)",
          "status-active-bg":  "var(--tb-status-active-bg)",
          "status-price":      "var(--tb-status-price)",
          "status-price-bg":   "var(--tb-status-price-bg)",
          "status-unused":     "var(--tb-status-unused)",
          "status-unused-bg":  "var(--tb-status-unused-bg)",
          "status-trial":      "var(--tb-status-trial)",
          "status-trial-bg":   "var(--tb-status-trial-bg)",
        },
      },
      borderRadius: {
        "tb-sm": "var(--tb-radius-sm)",
        "tb-md": "var(--tb-radius-md)",
        "tb-lg": "var(--tb-radius-lg)",
        "tb-xl": "var(--tb-radius-xl)",
      },
      boxShadow: {
        "tb-sm": "var(--tb-shadow-sm)",
        "tb-md": "var(--tb-shadow-md)",
      },
      maxWidth: {
        mobile: "430px",
      },
    },
  },
  plugins: [],
};

export default config;
