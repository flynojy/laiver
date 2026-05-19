"use client";

import { CheckCircle2, Database, MessageSquare, Sparkles } from "lucide-react";

import { HexGrid } from "@/components/glyphs/HexGrid";
import { Mask02 } from "@/components/glyphs/Mask02";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useI18n } from "@/features/i18n/language-provider";
import { SplashGate } from "@/features/splash/SplashGate";

const stages = [
  {
    title: "导入链路",
    description: "上传聊天记录，查看 normalized message 预览，再提交入库。",
    icon: Database,
    tag: "STAGE 01"
  },
  {
    title: "Persona 链路",
    description: "从导入数据抽取 Persona，并检查 tone、topics、phrases 和 style。",
    icon: Sparkles,
    tag: "STAGE 02"
  },
  {
    title: "对话链路",
    description: "选择 Persona 发起对话，查看 Agent 响应、命中的 memory 和写入结果。",
    icon: MessageSquare,
    tag: "STAGE 03"
  },
  {
    title: "验收闭环",
    description: "在 Memory 页面确认最近写入记录，并对下一轮对话做 recall 验证。",
    icon: CheckCircle2,
    tag: "STAGE 04"
  }
];

export default function DashboardPage() {
  const { t } = useI18n();

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="MISSION 00 / DASHBOARD"
        title="MAGI 一期验收终端"
        description="当前阶段只做一件事：把导入、Persona、Memory、Agent 主链路打磨扎实，并可稳定复现实验。"
        badge="8-STEP E2E"
      />

      {/* hero panel */}
      <div className="nerv-notch relative overflow-hidden rounded-[12px] border border-[color:var(--border-strong)] bg-[var(--surface)] p-8 shadow-panel">
        <div className="pointer-events-none absolute inset-0 text-[var(--accent)] opacity-[0.06]">
          <HexGrid />
        </div>
        <div className="pointer-events-none absolute -right-12 -top-8 h-72 w-72 text-[var(--accent)] opacity-[0.14]">
          <Mask02 />
        </div>
        <div className="relative">
          <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--accent)]">
            ▶ {t("SYNCHRONIZATION COMPLETE")}
          </p>
          <h2 className="mt-4 max-w-2xl text-2xl font-semibold leading-snug text-[var(--foreground)] md:text-3xl">
            {t("PERSONAL AGENT // MAGI v0.1")}
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--foreground-muted)]">
            {t("All systems nominal. Verify import → persona → memory → agent loop before expanding mission scope.")}
          </p>
          <div className="mt-6 flex flex-wrap gap-x-6 gap-y-2 font-mono text-[11px] uppercase tracking-[0.16em] text-[var(--foreground-muted)]">
            <span>
              <span className="text-[var(--success)]">●</span> {t("AT FIELD STABLE")}
            </span>
            <span>
              <span className="text-[var(--success)]">●</span> {t("MAGI ONLINE")}
            </span>
            <span>
              <span className="text-[var(--warning)]">●</span> {t("SYNC RATIO 87.4%")}
            </span>
          </div>
        </div>
      </div>

      {/* stat grid */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard title="验收步骤" value="8" description="按顺序验证上传、解析、入库、抽取、对话、写入、召回。" />
        <StatCard title="核心页面" value="4" description="导入、Persona、聊天、Memory 四个页面可直接验收。" />
        <StatCard title="默认数据库" value="SQLite" description="本地启动后自动建表，无需单独起数据库进程。" />
        <StatCard title="当前模型" value="DeepSeek" description="无 API Key 时走本地 mock fallback，便于链路联调。" />
      </div>

      {/* stages */}
      <div className="grid gap-4 xl:grid-cols-2">
        {stages.map((item) => {
          const Icon = item.icon;
          return (
            <Card key={item.title}>
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-[6px] border border-[color:var(--border-strong)] bg-[var(--accent-soft)] text-[var(--accent)]">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--foreground-muted)]">
                      {t(item.tag)}
                    </p>
                    <CardTitle>{item.title}</CardTitle>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="text-sm leading-6 text-[var(--foreground-muted)]">
                {item.description}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* NERV terminal boot sequence — plays on every mount of the Dashboard route */}
      <SplashGate />
    </div>
  );
}
