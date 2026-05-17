import { cn } from "@/lib/utils";

export function Mask02({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 200 240"
      className={cn("h-full w-full", className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      preserveAspectRatio="xMidYMid meet"
    >
      {/* outer helmet silhouette */}
      <path
        d="M40 30 L160 30 L180 80 L180 200 L140 230 L60 230 L20 200 L20 80 Z"
        strokeOpacity="0.5"
      />
      {/* cheek lines */}
      <path d="M55 50 L100 30 L145 50" strokeOpacity="0.3" />
      {/* four vertical eye-slits — EVA-02 berserk signature */}
      <line x1="60" y1="110" x2="60" y2="160" strokeOpacity="0.95" strokeWidth="2" />
      <line x1="80" y1="110" x2="80" y2="160" strokeOpacity="0.95" strokeWidth="2" />
      <line x1="120" y1="110" x2="120" y2="160" strokeOpacity="0.95" strokeWidth="2" />
      <line x1="140" y1="110" x2="140" y2="160" strokeOpacity="0.95" strokeWidth="2" />
      {/* mouth plate */}
      <rect x="70" y="185" width="60" height="14" strokeOpacity="0.4" />
      {/* central vertical axis */}
      <line
        x1="100"
        y1="35"
        x2="100"
        y2="225"
        strokeOpacity="0.18"
        strokeDasharray="2 4"
      />
    </svg>
  );
}
