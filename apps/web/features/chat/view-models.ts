import type { ConversationControls, PersonaCard, UUID } from "@agent/shared";

export interface ChatMemoryItemViewModel {
  id?: UUID;
  type: string;
  label: string;
  state: string;
  importance: number;
  confidence: number;
  content: string;
}

export interface ChatSkillInvocationViewModel {
  id: UUID;
  skillSlug: string;
  toolName: string;
  status: string;
  outputJson: string;
  error?: string | null;
}

export interface ChatRuntimeViewModel {
  skillsEnabled: boolean;
  memoryWriteEnabled: boolean;
  memoryWritten: boolean;
  memoryWriteCount: number;
  personaName: string;
}

export interface ChatProviderViewModel {
  providerName: string;
  modelName: string;
  modelMode: string;
  modelThinkLabel?: string;
  modelThinkGate?: string;
  memoryRoute: string;
  fallbackStatus: string;
  traceId: string;
}

export interface ChatCompressionViewModel {
  active: boolean;
  summarizedMessageCount: number;
  recentMessageCount: number;
  summary?: string | null;
}

export interface ChatExplanationViewModel {
  memoriesUsed: ChatMemoryItemViewModel[];
  personaFieldsUsed: string[];
  skillOutputsUsed: string[];
}

export interface ChatRunViewModel {
  conversationId: UUID;
  personaId?: UUID | null;
  persona?: PersonaCard | null;
  runtime: ChatRuntimeViewModel;
  provider: ChatProviderViewModel;
  compression: ChatCompressionViewModel;
  skillsUsed: string[];
  explanation: ChatExplanationViewModel;
  skillInvocations: ChatSkillInvocationViewModel[];
  memoryHits: ChatMemoryItemViewModel[];
  memoryWrites: ChatMemoryItemViewModel[];
}

export function defaultConversationControls(): ConversationControls {
  return {
    skills_enabled: true,
    memory_write_enabled: true
  };
}
