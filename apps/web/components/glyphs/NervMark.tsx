import { cn } from "@/lib/utils";

export function NervMark({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 64 64"
      className={cn("h-full w-full", className)}
      fill="none"
      preserveAspectRatio="xMidYMid meet"
    >
      {/* upper angular wedge */}
      <path
        d="M8 12 L56 12 L48 28 L24 28 L32 44 L20 44 L8 12 Z"
        fill="currentColor"
        fillOpacity="0.9"
      />
      {/* lower wedge — offset for asymmetric NERV feel */}
      <path d="M40 36 L56 36 L48 52 L32 52 L40 36 Z" fill="currentColor" fillOpacity="0.55" />
    </svg>
  );
}
