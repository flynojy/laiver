import * as React from "react";

import { cn } from "@/lib/utils";

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "w-full rounded-2xl border border-[color:var(--border)] bg-white px-4 py-3 text-sm text-[var(--foreground)] outline-none ring-0 placeholder:text-[var(--muted-foreground)] focus:border-slate-400",
        className
      )}
      {...props}
    />
  );
}

