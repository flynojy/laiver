import { cn } from "@/lib/utils";

function hexPoints(cx: number, cy: number, r: number): string {
  return Array.from({ length: 6 })
    .map((_, i) => {
      const angle = (Math.PI / 3) * i - Math.PI / 2;
      return `${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`;
    })
    .join(" ");
}

export function ATFieldBurst({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 200 200"
      className={cn("h-full w-full", className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="1"
      preserveAspectRatio="xMidYMid meet"
    >
      {[40, 60, 80, 100].map((r, i) => (
        <polygon key={r} points={hexPoints(100, 100, r)} strokeOpacity={0.6 - i * 0.13} />
      ))}
    </svg>
  );
}
