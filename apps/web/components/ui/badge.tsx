"use client";

import * as React from "react";

import { useI18n } from "@/features/i18n/language-provider";
import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "sync" | "standby" | "alert" | "idle";

type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & {
  variant?: BadgeVariant;
};

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const { tNode } = useI18n();

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-[3px] border px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-[0.12em]",
        variant === "default" &&
          "border-[color:var(--border-strong)] bg-transparent text-[var(--foreground-muted)]",
        variant === "sync" &&
          "border-[var(--success)] bg-[var(--success)]/10 text-[var(--success)]",
        variant === "standby" &&
          "border-[var(--warning)] bg-[var(--warning)]/10 text-[var(--warning)]",
        variant === "alert" &&
          "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]",
        variant === "idle" &&
          "border-[color:var(--border)] bg-[var(--surface-2)] text-[var(--foreground-muted)]",
        className
      )}
      {...props}
    >
      {tNode(props.children)}
    </span>
  );
}
