"use client";

import { Badge } from "@/components/ui/badge";
import { useI18n } from "@/features/i18n/language-provider";

export function PageHeader({
  eyebrow,
  title,
  description,
  badge
}: {
  eyebrow: string;
  title: string;
  description: string;
  badge?: string;
}) {
  const { t } = useI18n();

  return (
    <div className="mb-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div className="min-w-0">
          <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--accent)]">
            ▶ {t(eyebrow)}
          </p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-[var(--foreground)] md:text-4xl">
            {t(title)}
          </h1>
        </div>
        {badge ? <Badge variant="alert">{t(badge)}</Badge> : null}
      </div>
      <div className="relative mt-4 h-px w-full bg-[color:var(--accent)]/25">
        <div className="absolute left-0 top-0 h-px w-12 bg-[var(--accent)]" />
      </div>
      <p className="mt-4 max-w-2xl text-sm leading-6 text-[var(--foreground-muted)]">
        {t(description)}
      </p>
    </div>
  );
}
