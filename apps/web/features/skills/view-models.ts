import type { UUID } from "@agent/shared";

export type SkillCardViewModel = {
  id: UUID;
  title: string;
  description: string;
  status: string;
  typeLabel: string;
  slug: string;
  versionLabel: string;
  proxyLabel?: string;
  handlerLabel?: string;
  isCommunity: boolean;
  toggleLabel: string;
  manifestJson: string;
  runtimeConfigJson: string;
};

export type SkillInvocationViewModel = {
  id: UUID;
  badges: string[];
  traceId: string;
  timingLabel: string;
  outputJson: string;
  error?: string | null;
};
