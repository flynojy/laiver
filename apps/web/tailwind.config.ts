import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "../../packages/shared/src/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        card: "var(--card)",
        border: "var(--border)",
        accent: "var(--accent)",
        accentForeground: "var(--accent-foreground)",
        muted: "var(--muted)",
        mutedForeground: "var(--muted-foreground)",
        subtle: "var(--subtle)"
      },
      boxShadow: {
        panel: "0 1px 2px rgba(15, 15, 15, 0.04), 0 1px 1px rgba(15, 15, 15, 0.03)",
        soft: "0 1px 0 rgba(15, 15, 15, 0.04)"
      },
      borderRadius: {
        xl2: "0.75rem"
      }
    }
  },
  plugins: []
};

export default config;
