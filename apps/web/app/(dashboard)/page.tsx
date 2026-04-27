import { CheckCircle2, Database, MessageSquare, Sparkles } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const stages = [
  {
    title: "导入链路",
    description: "上传聊天记录，查看 normalized message 预览，再提交入库。",
    icon: Database
  },
  {
    title: "Persona 链路",
    description: "从导入数据抽取 Persona，并检查 tone、topics、phrases 和 style。",
    icon: Sparkles
  },
  {
    title: "对话链路",
    description: "选择 Persona 发起对话，查看 Agent 响应、命中的 memory 和写入结果。",
    icon: MessageSquare
  },
  {
    title: "验收闭环",
    description: "在 Memory 页面确认最近写入记录，并对下一轮对话做 recall 验证。",
    icon: CheckCircle2
  }
];

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="MVP Acceptance"
        title="一期 MVP 控制台"
        description="当前阶段只做一件事：把导入、Persona、Memory、Agent 主链路打磨扎实，并可稳定复现实验。"
        badge="8-step E2E"
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard title="验收步骤" value="8" description="按顺序验证上传、解析、入库、抽取、对话、写入、召回。" />
        <StatCard title="核心页面" value="4" description="导入、Persona、聊天、Memory 四个页面可直接验收。" />
        <StatCard title="默认数据库" value="SQLite" description="本地启动后自动建表，无需单独起数据库进程。" />
        <StatCard title="当前模型" value="DeepSeek" description="无 API Key 时走本地 mock fallback，便于链路联调。" />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        {stages.map((item) => {
          const Icon = item.icon;
          return (
            <Card key={item.title} className="bg-white/88">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="rounded-2xl bg-[var(--muted)] p-3 text-[var(--foreground)]">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <CardTitle>{item.title}</CardTitle>
                    <CardDescription>当前阶段的重点验证项</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="text-sm leading-6 text-[var(--muted-foreground)]">
                {item.description}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
