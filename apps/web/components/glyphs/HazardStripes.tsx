import { cn } from "@/lib/utils";

export function HazardStripes({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn("h-1.5 w-full", className)}
      style={{
        backgroundImage:
          "repeating-linear-gradient(135deg, var(--warning) 0 8px, transparent 8px 16px, var(--foreground) 16px 24px, transparent 24px 32px)"
      }}
    />
  );
}
