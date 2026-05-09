import * as React from "react";

import { cn } from "@/lib/utils";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "secondary" | "ghost";
};

export function Button({ className, variant = "default", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-md px-3.5 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        variant === "default" &&
          "bg-[var(--accent)] text-[var(--accent-foreground)] hover:bg-[var(--foreground)]/90",
        variant === "secondary" &&
          "border border-[color:var(--border)] bg-[var(--card)] text-[var(--foreground)] hover:bg-[var(--muted)]",
        variant === "ghost" &&
          "text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-[var(--foreground)]",
        className
      )}
      {...props}
    />
  );
}
