"use client";

import { Languages } from "lucide-react";

import { useI18n } from "@/features/i18n/language-provider";
import { cn } from "@/lib/utils";

export function LanguageToggle({ className }: { className?: string }) {
  const { language, toggleLanguage } = useI18n();

  return (
    <button
      type="button"
      aria-label={language === "en" ? "Switch UI to Chinese" : "切换界面到英文"}
      onClick={toggleLanguage}
      className={cn(
        "inline-flex h-8 items-center gap-2 rounded-[4px] border border-[color:var(--border-strong)] bg-[var(--surface)] px-3 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--foreground-muted)] transition hover:border-[var(--accent)] hover:text-[var(--accent)]",
        className
      )}
    >
      <Languages className="h-3 w-3" />
      <span className={language === "en" ? "text-[var(--accent)]" : undefined}>EN</span>
      <span className="text-[var(--foreground-muted)]/40">/</span>
      <span className={language === "zh" ? "text-[var(--accent)]" : undefined}>中文</span>
    </button>
  );
}
