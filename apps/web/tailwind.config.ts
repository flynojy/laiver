import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
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
        surface: "var(--surface)",
        surface2: "var(--surface-2)",
        foreground: "var(--foreground)",
        foregroundMuted: "var(--foreground-muted)",
        border: "var(--border)",
        borderStrong: "var(--border-strong)",
        accent: "var(--accent)",
        accentForeground: "var(--accent-foreground)",
        accentSoft: "var(--accent-soft)",
        warning: "var(--warning)",
        danger: "var(--danger)",
        success: "var(--success)",
        sidebarBg: "var(--sidebar-bg)",
        sidebarFg: "var(--sidebar-fg)",
        sidebarAccent: "var(--sidebar-accent)",
        sidebarMuted: "var(--sidebar-muted)",
        sidebarBorder: "var(--sidebar-border)",
        // Legacy aliases — auto-inherited pages still using old names
        card: "var(--surface)",
        muted: "var(--surface-2)",
        mutedForeground: "var(--foreground-muted)"
      },
      fontFamily: {
        sans: ["var(--font-sans)", "PingFang SC", "Microsoft YaHei", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "JetBrains Mono", "Consolas", "monospace"]
      },
      boxShadow: {
        panel: "var(--shadow-panel)",
        hover: "var(--shadow-hover)"
      },
      borderRadius: {
        panel: "12px",
        shell: "20px",
        xl2: "1.5rem"
      },
      letterSpacing: {
        hud: "0.16em",
        wider2: "0.24em"
      }
    }
  },
  plugins: []
};

export default config;
