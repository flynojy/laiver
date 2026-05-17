import * as React from "react";

import { cn } from "@/lib/utils";

export function Textarea({
  className,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "min-h-[120px] w-full rounded-[4px] border border-[color:var(--border-strong)] bg-[var(--surface)] px-3 py-2.5 text-sm text-[var(--foreground)] outline-none transition placeholder:font-mono placeholder:text-xs placeholder:text-[var(--foreground-muted)] focus:border-[var(--accent)] focus:outline focus:outline-1 focus:outline-[var(--accent)] focus:[outline-offset:-1px]",
        className
      )}
      {...props}
    />
  );
}
