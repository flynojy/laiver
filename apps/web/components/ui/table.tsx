"use client";

import * as React from "react";

import { useI18n } from "@/features/i18n/language-provider";
import { cn } from "@/lib/utils";

export function Table({ className, ...props }: React.HTMLAttributes<HTMLTableElement>) {
  return <table className={cn("w-full caption-bottom text-sm", className)} {...props} />;
}

export function TableHead({
  className,
  ...props
}: React.ThHTMLAttributes<HTMLTableCellElement>) {
  const { tNode } = useI18n();

  return (
    <th
      className={cn(
        "px-4 py-3 text-left font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--foreground-muted)]",
        className
      )}
      {...props}
    >
      {tNode(props.children)}
    </th>
  );
}

export function TableRow({
  className,
  ...props
}: React.HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={cn(
        "border-t border-[color:var(--border)] align-top transition hover:bg-[var(--accent-soft)]",
        className
      )}
      {...props}
    />
  );
}

export function TableCell({
  className,
  ...props
}: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn("px-4 py-4 text-sm tabular-nums", className)} {...props} />;
}
