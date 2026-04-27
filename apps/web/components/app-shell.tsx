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
  WandSparkles
} from "lucide-react";

import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/onboarding", label: "Onboarding", icon: Rocket },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/imports", label: "Imports", icon: Database },
  { href: "/persona", label: "Persona", icon: Sparkles },
  { href: "/training", label: "Training", icon: WandSparkles },
  { href: "/memories", label: "Memories", icon: BrainCircuit },
  { href: "/skills", label: "Skills", icon: Bot },
  { href: "/connectors", label: "Connectors", icon: Cable },
  { href: "/settings", label: "Settings", icon: Settings2 }
] as const satisfies ReadonlyArray<{ href: Route; label: string; icon: typeof LayoutDashboard }>;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      <div className="mx-auto flex min-h-screen max-w-[1600px] gap-6 px-4 py-4 sm:px-6">
        <aside className="hidden w-[280px] shrink-0 flex-col rounded-[2rem] border border-white/60 bg-[linear-gradient(180deg,#102a43_0%,#173f5f_50%,#f3efe7_100%)] p-5 text-white shadow-panel lg:flex">
          <div className="rounded-[1.5rem] bg-white/10 p-5 backdrop-blur">
            <p className="text-xs uppercase tracking-[0.3em] text-white/70">Personal Agent</p>
            <h1 className="mt-3 text-2xl font-semibold">MVP Validation Console</h1>
            <p className="mt-3 text-sm leading-6 text-white/80">
              Keep the import, Persona, memory, agent, and skill runtime loop stable before expanding business scope.
            </p>
          </div>
          <nav className="mt-6 space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm transition",
                    active ? "bg-white text-slate-900" : "text-white/80 hover:bg-white/10 hover:text-white"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="mt-auto rounded-[1.5rem] bg-slate-950/20 p-4 text-sm text-white/80">
            The current console now covers imports, Persona, memories, skills, model providers, and the first local
            fine-tuning workflow.
          </div>
        </aside>
        <main className="flex-1">{children}</main>
      </div>
    </div>
  );
}
