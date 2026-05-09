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
      <div className="mx-auto flex min-h-screen max-w-[1480px] gap-8 px-6 py-8">
        <aside className="hidden w-[240px] shrink-0 flex-col border-r border-[color:var(--border)] pr-6 lg:flex">
          <div className="pb-8">
            <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--muted-foreground)]">
              Laiver
            </p>
            <h1 className="mt-2 text-base font-medium tracking-tight text-[var(--foreground)]">
              Personal Agent
            </h1>
          </div>
          <nav className="space-y-0.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm transition-colors",
                    active
                      ? "bg-[var(--subtle)] text-[var(--foreground)]"
                      : "text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0 opacity-70" />
                  <span className="truncate">{item.label}</span>
                </Link>
              );
            })}
          </nav>
          <div className="mt-auto pt-8">
            <p className="text-xs leading-5 text-[var(--muted-foreground)]">
              Imports · Persona · Memory · Skills · Providers · Local fine-tuning.
            </p>
          </div>
        </aside>
        <main className="flex-1 min-w-0">{children}</main>
      </div>
    </div>
  );
}
