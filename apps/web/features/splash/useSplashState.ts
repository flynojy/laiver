"use client";

import { useCallback, useEffect, useState } from "react";

export type SplashPhase = "playing" | "dismissing" | "done";

const DEFAULT_DURATION_MS = 4200;
const FADE_OUT_MS = 320;

/**
 * Drives the splash overlay lifecycle:
 *  - "playing"    : the choreography is running
 *  - "dismissing" : skip / auto-end triggered, css fadeOut is running
 *  - "done"       : caller should unmount the overlay
 *
 * Skip is bound to Escape / Space / Enter and any pointerdown anywhere
 * on the window. Auto-dismiss fires after `durationMs`.
 */
export function useSplashState(durationMs: number = DEFAULT_DURATION_MS) {
  const [phase, setPhase] = useState<SplashPhase>("playing");

  const dismiss = useCallback(() => {
    setPhase((current) => {
      if (current !== "playing") return current;
      // schedule the transition to "done" once the fade-out keyframe completes
      window.setTimeout(() => {
        setPhase((p) => (p === "dismissing" ? "done" : p));
      }, FADE_OUT_MS);
      return "dismissing";
    });
  }, []);

  useEffect(() => {
    if (phase !== "playing") return;

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" || event.key === " " || event.key === "Enter") {
        dismiss();
      }
    };
    const onPointer = () => dismiss();

    window.addEventListener("keydown", onKey);
    window.addEventListener("pointerdown", onPointer);
    const autoTimer = window.setTimeout(dismiss, durationMs);

    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("pointerdown", onPointer);
      window.clearTimeout(autoTimer);
    };
  }, [phase, durationMs, dismiss]);

  return { phase, dismiss };
}
