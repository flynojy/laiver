"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname } from "next/navigation";
import {
  Bot,
  BrainCircuit,
  Cable,
  Database,
  LayoutDashboard,
  MessageSquare,
  Rocket,
  Settings2,
  Sparkles,
  WandSparkles,
  type LucideIcon
} from "lucide-react";

import { HexGrid } from "@/components/glyphs/HexGrid";
import { Mask02 } from "@/components/glyphs/Mask02";
import { NervMark } from "@/components/glyphs/NervMark";
import { SyncBars } from "@/components/glyphs/SyncBars";
import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";

const navItems: ReadonlyArray<{
  href: Route;
  label: string;
  tag: string;
  icon: LucideIcon;
}> = [
  { href: "/", label: "Dashboard", tag: "00", icon: LayoutDashboard },
  { href: "/onboarding", label: "Initialization", tag: "01", icon: Rocket },
  { href: "/chat", label: "Dialog // 02", tag: "02", icon: MessageSquare },
  { href: "/imports", label: "Imports", tag: "03", icon: Database },
  { href: "/persona", label: "Persona", tag: "04", icon: Sparkles },
  { href: "/training", label: "Pilot Training", tag: "05", icon: WandSparkles },
  { href: "/memories", label: "Memory Bank", tag: "06", icon: BrainCircuit },
  { href: "/skills", label: "Equipment", tag: "07", icon: Bot },
  { href: "/connectors", label: "Connectors", tag: "08", icon: Cable },
  { href: "/settings", label: "Mission Control", tag: "09", icon: Settings2 }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      <div className="mx-auto flex min-h-screen max-w-[1600px] gap-6 px-4 py-4 sm:px-6">
        <aside className="relative hidden w-[300px] shrink-0 flex-col overflow-hidden rounded-[20px] border border-[color:var(--sidebar-border)] bg-[var(--sidebar-bg)] text-[var(--sidebar-fg)] shadow-panel lg:flex">
          {/* hex grid watermark */}
          <div className="pointer-events-none absolute inset-0 text-[var(--sidebar-accent)] opacity-[0.06]">
            <HexGrid />
          </div>

          {/* brand */}
          <div className="relative z-10 border-b border-[color:var(--sidebar-border)] p-5">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 text-[var(--sidebar-accent)]">
                <NervMark />
              </div>
              <div>
                <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--sidebar-muted)]">
                  LAIVER
                </p>
                <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--sidebar-fg)]">
                  EVA-02 EDITION
                </p>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.18em] text-[var(--sidebar-muted)]">
              <span className="inline-block h-1.5 w-1.5 animate-pulse-glow rounded-full bg-[var(--success)]" />
              <span>SYSTEM ONLINE</span>
              <span className="ml-auto">v0.1</span>
            </div>
          </div>

          {/* nav */}
          <nav className="relative z-10 flex-1 space-y-0.5 px-3 py-4">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "group flex items-center gap-3 rounded-[4px] border border-transparent px-3 py-2 font-mono text-[11px] uppercase tracking-[0.12em] transition",
                    active
                      ? "border-[color:var(--sidebar-accent)]/40 bg-[color:var(--sidebar-accent)]/10 text-[var(--sidebar-accent)]"
                      : "text-[var(--sidebar-muted)] hover:bg-white/5 hover:text-[var(--sidebar-fg)]"
                  )}
                >
                  <span
                    className={cn(
                      "w-2 font-mono text-[10px]",
                      active ? "text-[var(--sidebar-accent)]" : "text-[var(--sidebar-muted)]"
                    )}
                  >
                    {active ? "▶" : "·"}
                  </span>
                  <Icon className="h-3.5 w-3.5" />
                  <span className="flex-1">{item.label}</span>
                  <span className="font-mono text-[9px] opacity-50">{item.tag}</span>
                </Link>
              );
            })}
          </nav>

          {/* pilot slot */}
          <div className="relative z-10 border-t border-[color:var(--sidebar-border)] p-5">
            <div className="relative overflow-hidden rounded-[8px] border border-[color:var(--sidebar-border)] bg-black/30 p-4">
              <div className="pointer-events-none absolute -right-6 -top-4 h-32 w-28 text-[var(--sidebar-accent)] opacity-25">
                <Mask02 />
              </div>
              <div className="relative">
                <p className="font-mono text-[9px] uppercase tracking-[0.24em] text-[var(--sidebar-muted)]">
                  PILOT // 02
                </p>
                <p className="mt-1 font-mono text-sm font-semibold text-[var(--sidebar-fg)]">
                  SORYU
                </p>
                <div className="mt-3 space-y-1.5">
                  <div className="flex items-end justify-between gap-2">
                    <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-[var(--sidebar-muted)]">
                      SYNC RATIO
                    </span>
                    <span className="font-mono text-[18px] font-semibold leading-none text-[var(--sidebar-accent)]">
                      87.4
                      <span className="text-[10px] text-[var(--sidebar-muted)]">%</span>
                    </span>
                  </div>
                  <div className="h-[3px] w-full overflow-hidden rounded-full bg-white/10">
                    <div
                      className="h-full rounded-full bg-[var(--sidebar-accent)]"
                      style={{ width: "87.4%" }}
                    />
                  </div>
                  <div className="flex items-center justify-between gap-2 pt-1">
                    <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-[var(--success)]">
                      ● STABLE
                    </span>
                    <SyncBars className="text-[var(--sidebar-accent)]" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div className="font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--foreground-muted)]">
              <span className="text-[var(--accent)]">▶</span> NERV TERMINAL · TOKYO-3
            </div>
            <ThemeToggle />
          </div>
          {children}
        </main>
      </div>
    </div>
  );
}
