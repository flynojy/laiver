import type { CSSProperties } from "react";

import { cn } from "@/lib/utils";

const CORNERS = ["tl", "tr", "bl", "br"] as const;
type Corner = (typeof CORNERS)[number];

// Tailwind positioning per corner
const POSITION: Record<Corner, string> = {
  tl: "left-6 top-6",
  tr: "right-6 top-6",
  bl: "bottom-6 left-6",
  br: "bottom-6 right-6"
};

// Two lines meeting at the corner — direction differs per corner
const LINES: Record<Corner, [[number, number, number, number], [number, number, number, number]]> = {
  tl: [[0, 0, 22, 0], [0, 0, 0, 22]],
  tr: [[22, 0, 0, 0], [22, 0, 22, 22]],
  bl: [[0, 22, 22, 22], [0, 22, 0, 0]],
  br: [[22, 22, 0, 22], [22, 22, 22, 0]]
};

/**
 * 4 NERV-style bracket marks pinned to each viewport corner.
 * The splash CSS module animates them with a staggered scale-in via `--i`.
 */
export function CornerBrackets({ className }: { className?: string }) {
  return (
    <>
      {CORNERS.map((corner, index) => {
        const [line1, line2] = LINES[corner];
        const style: CSSProperties = {
          ["--i" as never]: String(index)
        };
        return (
          <svg
            key={corner}
            aria-hidden
            data-corner={corner}
            className={cn("pointer-events-none absolute h-5 w-5", POSITION[corner], className)}
            style={style}
            viewBox="0 0 22 22"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <line x1={line1[0]} y1={line1[1]} x2={line1[2]} y2={line1[3]} />
            <line x1={line2[0]} y1={line2[1]} x2={line2[2]} y2={line2[3]} />
          </svg>
        );
      })}
    </>
  );
}
