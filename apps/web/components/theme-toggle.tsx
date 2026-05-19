"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

import { useI18n } from "@/features/i18n/language-provider";
import { cn } from "@/lib/utils";

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const { t } = useI18n();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  const isDark = mounted
    ? theme === "dark" || (theme === "system" && resolvedTheme === "dark")
    : true;

  return (
    <button
      type="button"
      aria-label={t("Toggle theme")}
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className={cn(
        "inline-flex h-8 items-center gap-2 rounded-[4px] border border-[color:var(--border-strong)] bg-[var(--surface)] px-3 font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--foreground-muted)] transition hover:border-[var(--accent)] hover:text-[var(--accent)]",
        className
      )}
    >
      {isDark ? <Moon className="h-3 w-3" /> : <Sun className="h-3 w-3" />}
      <span>{t(isDark ? "NIGHT" : "DAY")}</span>
    </button>
  );
}
