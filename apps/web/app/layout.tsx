import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Personal Agent Platform",
  description: "个人 Agent 平台一期 MVP，聚焦导入、Persona、Memory 与 Agent 主链路验收。"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
