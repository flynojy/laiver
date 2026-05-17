import { cn } from "@/lib/utils";

export function HexGrid({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden
      className={cn("h-full w-full", className)}
      preserveAspectRatio="xMidYMid slice"
    >
      <defs>
        <pattern id="hex-grid" x="0" y="0" width="28" height="32" patternUnits="userSpaceOnUse">
          <polygon
            points="14,2 26,9 26,23 14,30 2,23 2,9"
            fill="none"
            stroke="currentColor"
            strokeWidth="0.7"
            strokeOpacity="0.5"
          />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#hex-grid)" />
    </svg>
  );
}
