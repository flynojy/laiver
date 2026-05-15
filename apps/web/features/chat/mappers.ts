import type {
  AgentChatResponse,
  ConversationControls,
  MemoryRecord,
  SkillInvocationRecord
} from "@agent/shared";

import {
  type ChatMemoryItemViewModel,
  type ChatRunViewModel,
  type ChatSkillInvocationViewModel,
  defaultConversationControls
} from "./view-models";

export { defaultConversationControls };

export function normalizeConversationControls(value: unknown): ConversationControls {
  const defaults = defaultConversationControls();
  if (!value || typeof value !== "object") {
    return defaults;
  }
  const candidate = value as Partial<ConversationControls>;
  return {
    skills_enabled: candidate.skills_enabled ?? defaults.skills_enabled,
    memory_write_enabled: candidate.memory_write_enabled ?? defaults.memory_write_enabled
  };
}

export function toChatMemoryItem(memory: MemoryRecord): ChatMemoryItemViewModel {
  return {
    id: memory.id,
    type: memory.memory_type,
    label: String(memory.metadata?.memory_label ?? "unknown"),
    state: String(memory.metadata?.state ?? "active"),
    importance: memory.importance_score,
    confidence: memory.confidence_score,
    content: memory.content
  };
}

function toThinkLabel(value: boolean | null | undefined): string | undefined {
  if (value === true) {
    return "think on";
  }
  if (value === false) {
    return "think off";
  }
  return undefined;
}

function toSkillInvocation(invocation: SkillInvocationRecord): ChatSkillInvocationViewModel {
  return {
    id: invocation.invocation_id,
    skillSlug: invocation.skill_slug,
    toolName: invocation.tool_name,
    status: invocation.status,
    outputJson: JSON.stringify(invocation.output, null, 2),
    error: invocation.error
  };
}

export function toChatRunViewModel(response: AgentChatResponse): ChatRunViewModel {
  const debug = response.debug;
  return {
    conversationId: response.conversation_id,
    personaId: debug.persona_id ?? null,
    persona: response.persona,
    runtime: {
      skillsEnabled: debug.skills_enabled,
      memoryWriteEnabled: debug.memory_write_enabled,
      memoryWritten: debug.memory_write_count > 0,
      memoryWriteCount: debug.memory_write_count,
      personaName: debug.persona_name ?? "no persona"
    },
    provider: {
      providerName: debug.provider_name,
      modelName: debug.model_name,
      modelMode: debug.model_mode,
      modelThinkLabel: toThinkLabel(debug.model_think_enabled),
      modelThinkGate: debug.model_think_gate ? `think ${debug.model_think_gate}` : undefined,
      memoryRoute: debug.memory_query_route,
      fallbackStatus: debug.fallback_status,
      traceId: debug.trace_id
    },
    compression: {
      active: debug.compression_active,
      summarizedMessageCount: debug.summarized_message_count,
      recentMessageCount: debug.recent_message_count,
      summary: debug.conversation_summary
    },
    skillsUsed: debug.skills_used,
    explanation: {
      memoriesUsed: debug.explanation.memories_used.map(toChatMemoryItem),
      personaFieldsUsed: debug.explanation.persona_fields_used,
      skillOutputsUsed: debug.explanation.skill_outputs_used
    },
    skillInvocations: debug.skill_invocations.map(toSkillInvocation),
    memoryHits: debug.memory_hits.map(toChatMemoryItem),
    memoryWrites: debug.memory_writes.map(toChatMemoryItem)
  };
}
