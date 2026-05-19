import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";

import { ThemeProvider } from "@/components/theme-provider";
import { LanguageProvider } from "@/features/i18n/language-provider";

import "./globals.css";

export const metadata: Metadata = {
  title: "LAIVER / EVA-02 EDITION",
  description:
    "Personal AI agent platform — MAGI synchronization terminal for imports, persona, memory, agent, and skill runtime."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${GeistSans.variable} ${GeistMono.variable}`}
      suppressHydrationWarning
    >
      <body>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
          <LanguageProvider>{children}</LanguageProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
