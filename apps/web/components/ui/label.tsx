"use client";

import * as React from "react";

import { useI18n } from "@/features/i18n/language-provider";
import { cn } from "@/lib/utils";

export function Label({ className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  const { tNode } = useI18n();

  return (
    <label
      className={cn(
        "font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--foreground-muted)]",
        className
      )}
      {...props}
    >
      {tNode(props.children)}
    </label>
  );
}
