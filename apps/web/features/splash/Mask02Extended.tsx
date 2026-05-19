import type { CSSProperties } from "react";

import { cn } from "@/lib/utils";

type SvgElementKind = "path" | "line" | "rect";

type SvgPart = {
  el: SvgElementKind;
  attrs: Record<string, string | number>;
  /** Estimated draw length for stroke-dasharray. Overshoot is invisible. */
  len: number;
  /** Eye-slits get a class so CSS can chain a second ignite animation. */
  isEye?: boolean;
};

/**
 * Extends the silhouette of `Mask02` (helmet + eyes + mouth + axis) with
 * shoulder pauldrons and two pylons so the assembled outline reads as
 * EVA-02's torso, not just a floating mask.
 *
 * Each child carries `--i` (its index in the draw cascade) and `--len`
 * (its dash length). The splash CSS module reads both via custom property
 * to stagger the draw animation.
 */
const PARTS: SvgPart[] = [
  // 0: helmet outline
  {
    el: "path",
    attrs: {
      d: "M70 60 L210 60 L235 110 L235 230 L195 260 L85 260 L45 230 L45 110 Z",
      strokeOpacity: "0.6"
    },
    len: 900
  },
  // 1: cheek lines
  {
    el: "path",
    attrs: { d: "M85 80 L140 60 L195 80", strokeOpacity: "0.35" },
    len: 200
  },
  // 2-5: four vertical eye-slits — get .eyeSlit class for the ignite chain
  {
    el: "line",
    attrs: { x1: "92", y1: "140", x2: "92", y2: "190", strokeWidth: "2.4", strokeOpacity: "0.95" },
    len: 60,
    isEye: true
  },
  {
    el: "line",
    attrs: { x1: "118", y1: "140", x2: "118", y2: "190", strokeWidth: "2.4", strokeOpacity: "0.95" },
    len: 60,
    isEye: true
  },
  {
    el: "line",
    attrs: { x1: "162", y1: "140", x2: "162", y2: "190", strokeWidth: "2.4", strokeOpacity: "0.95" },
    len: 60,
    isEye: true
  },
  {
    el: "line",
    attrs: { x1: "188", y1: "140", x2: "188", y2: "190", strokeWidth: "2.4", strokeOpacity: "0.95" },
    len: 60,
    isEye: true
  },
  // 6: mouth plate
  {
    el: "rect",
    attrs: { x: "108", y: "215", width: "64", height: "16", strokeOpacity: "0.45" },
    len: 170
  },
  // 7: central vertical axis (dashed)
  {
    el: "line",
    attrs: {
      x1: "140",
      y1: "65",
      x2: "140",
      y2: "255",
      strokeOpacity: "0.18",
      strokeDasharray: "2 4"
    },
    len: 200
  },
  // 8: left pylon (above helmet)
  {
    el: "line",
    attrs: { x1: "85", y1: "60", x2: "75", y2: "20", strokeOpacity: "0.7", strokeWidth: "2" },
    len: 50
  },
  // 9: right pylon
  {
    el: "line",
    attrs: { x1: "195", y1: "60", x2: "205", y2: "20", strokeOpacity: "0.7", strokeWidth: "2" },
    len: 50
  },
  // 10: left shoulder pauldron (trapezoid)
  {
    el: "path",
    attrs: { d: "M45 270 L20 320 L80 340 L85 280 Z", strokeOpacity: "0.45" },
    len: 280
  },
  // 11: right shoulder pauldron
  {
    el: "path",
    attrs: { d: "M235 270 L260 320 L200 340 L195 280 Z", strokeOpacity: "0.45" },
    len: 280
  },
  // 12: chest core circle
  {
    el: "path",
    attrs: {
      d: "M140 290 m-12 0 a12 12 0 1 0 24 0 a12 12 0 1 0 -24 0",
      strokeOpacity: "0.55"
    },
    len: 80
  }
];

export function Mask02Extended({
  className,
  eyeClassName
}: {
  className?: string;
  /** Applied to the 4 eye-slits so the splash CSS can chain the ignite animation. */
  eyeClassName?: string;
}) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 280 360"
      className={cn("h-full w-full", className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      preserveAspectRatio="xMidYMid meet"
    >
      {PARTS.map((part, index) => {
        const style: CSSProperties = {
          // CSS custom properties consumed by splash.module.css
          ["--i" as never]: String(index),
          ["--len" as never]: String(part.len)
        };
        const className = part.isEye ? eyeClassName : undefined;
        const sharedProps = { key: index, style, className };

        if (part.el === "line") {
          return <line {...sharedProps} {...(part.attrs as Record<string, string>)} />;
        }
        if (part.el === "rect") {
          return <rect {...sharedProps} {...(part.attrs as Record<string, string>)} />;
        }
        return <path {...sharedProps} {...(part.attrs as Record<string, string>)} />;
      })}
    </svg>
  );
}
