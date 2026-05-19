"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

// SSR-skip + code-split: the overlay only lives in its own chunk that
// is fetched after the dashboard has mounted, so it never blocks FCP/LCP.
const SplashOverlay = dynamic(
  () => import("@/features/splash/SplashOverlay").then((mod) => mod.SplashOverlay),
  { ssr: false }
);

/**
 * Decides whether to render the splash overlay for the current mount of
 * the Dashboard page. Returns `null` on first render so the server HTML
 * stays splash-free (no hydration flash, no FOUC).
 *
 *   - default: play every time Dashboard mounts (per user spec)
 *   - `?splash=0` in the URL skips the overlay entirely
 *   - `prefers-reduced-motion: reduce` is handled inside the CSS module
 *     (static final frame instead of the keyframed sequence)
 */
export function SplashGate() {
  const [decision, setDecision] = useState<"pending" | "skip" | "play">("pending");

  useEffect(() => {
    if (typeof window === "undefined") {
      setDecision("skip");
      return;
    }
    const params = new URLSearchParams(window.location.search);
    if (params.get("splash") === "0") {
      setDecision("skip");
      return;
    }
    setDecision("play");
  }, []);

  if (decision !== "play") return null;
  return <SplashOverlay />;
}
