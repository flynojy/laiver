import * as React from "react";

import { cn } from "@/lib/utils";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "secondary" | "ghost" | "danger";
  size?: "sm" | "default" | "lg";
};

export function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-[4px] font-mono font-semibold uppercase tracking-[0.12em] transition disabled:cursor-not-allowed disabled:opacity-50",
        size === "sm" && "h-7 px-3 text-[10px]",
        size === "default" && "h-9 px-4 text-[11px]",
        size === "lg" && "h-11 px-6 text-xs",
        variant === "default" &&
          "bg-[var(--accent)] text-[var(--accent-foreground)] hover:brightness-110 active:brightness-90",
        variant === "secondary" &&
          "border border-[var(--accent)] bg-transparent text-[var(--accent)] hover:bg-[var(--accent-soft)]",
        variant === "ghost" &&
          "text-[var(--foreground-muted)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)]",
        variant === "danger" && "bg-[var(--danger)] text-white hover:brightness-110",
        className
      )}
      {...props}
    />
  );
}
