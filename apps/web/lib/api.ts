import type {
  AgentChatResponse,
  ConversationControls,
  ConnectorConversationMappingRecord,
  ConnectorDeliveryRecord,
  ConnectorRecord,
  ConnectorTestResult,
  FineTuneJobDetail,
  FineTuneJobRecord,
  ImportPreviewSummary,
  LocalAdapterRuntimeState,
  MemoryEpisodeRecord,
  MemoryCandidateRecord,
  MemoryFactRecord,
  MemoryMaintenanceReport,
  MemoryRecord,
  MemoryRevisionRecord,
  ModelProviderConfig,
  ModelProviderValidationResult,
  NormalizedMessage,
  PersonaCard,
  SkillInvocationRecord,
  SkillRecord,
  UUID
} from "@agent/shared";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export type BootstrapUserResponse = {
  user: {
    id: UUID;
    email: string;
    display_name: string;
  };
  created: boolean;
};

export type ImportPreview = ImportPreviewSummary & {
  normalized_messages: NormalizedMessage[];
};

export type ImportDetail = {
  import_job: {
    id: UUID;
    user_id: UUID;
    file_name: string;
    source_type: string;
    status: string;
    created_at: string;
    preview_payload?: Record<string, unknown>;
    normalized_summary: Record<string, unknown>;
  };
  normalized_messages: NormalizedMessage[];
};

export type ConversationSummary = {
  id: UUID;
  title: string;
  updated_at: string;
  persona_id?: UUID | null;
};

export type ConversationDetail = {
  conversation: ConversationSummary & {
    user_id: UUID;
    persona_id?: UUID | null;
    summary?: string | null;
    metadata?: Record<string, unknown>;
  };
  messages: {
    id: UUID;
    role: "system" | "user" | "assistant" | "tool";
    content: string;
    created_at: string;
    metadata?: Record<string, unknown>;
  }[];
};

export async function bootstrapUser() {
  return apiFetch<BootstrapUserResponse>("/users/bootstrap", {
    method: "POST"
  });
}

export async function bootstrapModelProvider() {
  return apiFetch<ModelProviderConfig>("/model-providers/bootstrap", {
    method: "POST"
  });
}

export async function seedSkills() {
  return apiFetch<SkillRecord[]>("/skills/seed", {
    method: "POST"
  });
}

export async function listImports() {
  return apiFetch<ImportDetail[]>("/imports");
}

export async function previewImport(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE_URL}/imports/preview`, {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return (await response.json()) as ImportPreview;
}

export async function commitImport(payload: {
  user_id: UUID;
  file_name: string;
  source_type: "txt" | "csv" | "json" | "xlsx";
  file_size: number;
  normalized_messages: NormalizedMessage[];
  preview?: Record<string, unknown>;
}) {
  return apiFetch<ImportDetail>("/imports/commit", {
    method: "POST",
    body: JSON.stringify({
      ...payload,
      preview: payload.preview ?? {
        total_messages: payload.normalized_messages.length
      }
    })
  });
}

export async function listPersonas() {
  return apiFetch<PersonaCard[]>("/personas");
}

export async function extractPersona(payload: {
  user_id: UUID;
  import_id?: UUID;
  name: string;
  source_speaker?: string;
  persist?: boolean;
  set_default?: boolean;
}) {
  return apiFetch<{ persona: PersonaCard; source_message_count: number; source_speaker?: string | null }>(
    "/personas/extract",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function updatePersona(personaId: UUID, payload: Partial<PersonaCard>) {
  return apiFetch<PersonaCard>(`/personas/${personaId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export async function listMemories() {
  return apiFetch<MemoryRecord[]>("/memories");
}

export async function getMemoryDebug() {
  return apiFetch<{
    qdrant_available: boolean;
    collection_name: string;
    total_memories: number;
    total_episodes: number;
    total_facts: number;
    total_revisions: number;
    candidate_counts: Record<string, number>;
    recent_memories: MemoryRecord[];
    recent_episodes: MemoryEpisodeRecord[];
    recent_facts: MemoryFactRecord[];
    recent_revisions: MemoryRevisionRecord[];
    recent_candidates: MemoryCandidateRecord[];
    profile_summary: string;
    profile_snapshot: Record<string, unknown>;
    user_profile_snapshot: Record<string, unknown>;
    relationship_state_snapshot: Record<string, unknown>;
    conflict_groups: Array<{
      group_id: string;
      fact_key: string;
      items: Array<{
        id: string;
        content: string;
        state: string;
        current_version: boolean;
        polarity?: string | null;
      }>;
    }>;
    lifecycle_counts: Record<string, number>;
  }>("/memories/debug");
}

export async function listMemoryCandidates(payload?: { status?: string; limit?: number }) {
  const params = new URLSearchParams();
  if (payload?.status) {
    params.set("status", payload.status);
  }
  if (typeof payload?.limit === "number") {
    params.set("limit", String(payload.limit));
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  return apiFetch<MemoryCandidateRecord[]>(`/memories/candidates${suffix}`);
}

export async function updateMemoryCandidate(
  candidateId: UUID,
  payload: {
    proposed_action?: string;
    salience_score?: number;
    confidence_score?: number;
    sensitivity?: string;
    reason_codes?: unknown[];
    auto_commit?: boolean;
    status?: string;
    reviewer_type?: string | null;
  }
) {
  return apiFetch<MemoryCandidateRecord>(`/memories/candidates/${candidateId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function runMemoryMaintenance(payload?: { dry_run?: boolean }) {
  const params = new URLSearchParams();
  if (payload?.dry_run) {
    params.set("dry_run", "true");
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  return apiFetch<MemoryMaintenanceReport>(`/memories/maintenance/run${suffix}`, {
    method: "POST"
  });
}

export async function searchMemories(payload: {
  user_id: UUID;
  query: string;
  persona_id?: UUID | null;
  memory_types?: string[];
  limit?: number;
}) {
  return apiFetch<MemoryRecord[]>("/memories/search", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function createMemory(payload: {
  user_id: UUID;
  persona_id?: UUID | null;
  conversation_id?: UUID | null;
  memory_type: "session" | "episodic" | "semantic" | "instruction";
  content: string;
  importance_score?: number;
  confidence_score?: number;
}) {
  return apiFetch<MemoryRecord>("/memories", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateMemory(
  memoryId: UUID,
  payload: {
    importance_score?: number;
    confidence_score?: number;
    metadata?: Record<string, unknown>;
  }
) {
  return apiFetch<MemoryRecord>(`/memories/${memoryId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function listConversations() {
  return apiFetch<ConversationSummary[]>("/conversations");
}

export async function getConversation(conversationId: UUID) {
  return apiFetch<ConversationDetail>(`/conversations/${conversationId}`);
}

export async function updateConversation(
  conversationId: UUID,
  payload: {
    persona_id?: UUID | null;
    metadata?: Record<string, unknown>;
  }
) {
  return apiFetch<ConversationSummary & { user_id: UUID; metadata?: Record<string, unknown> }>(
    `/conversations/${conversationId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload)
    }
  );
}

export async function respondAgent(payload: {
  user_id: UUID;
  conversation_id?: UUID | null;
  persona_id?: UUID | null;
  message: string;
  controls?: ConversationControls;
}) {
  return apiFetch<AgentChatResponse>("/agent/respond", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function listSkills() {
  return apiFetch<SkillRecord[]>("/skills");
}

export async function listSkillInvocations() {
  return apiFetch<SkillInvocationRecord[]>("/skills/invocations");
}

export async function enableSkill(skillId: UUID) {
  return apiFetch<SkillRecord>(`/skills/${skillId}/enable`, {
    method: "POST"
  });
}

export async function disableSkill(skillId: UUID) {
  return apiFetch<SkillRecord>(`/skills/${skillId}/disable`, {
    method: "POST"
  });
}

export async function deleteSkill(skillId: UUID) {
  return apiFetch<{ deleted: boolean }>(`/skills/${skillId}`, {
    method: "DELETE"
  });
}

export async function installSkillPackage(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<SkillRecord>("/skills/install/upload", {
    method: "POST",
    body: formData
  });
}

export async function listConnectors() {
  return apiFetch<ConnectorRecord[]>("/connectors");
}

export async function createConnector(payload: {
  user_id: UUID;
  connector_type?: "feishu";
  name: string;
  status?: "inactive" | "active" | "error";
  config?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}) {
  return apiFetch<ConnectorRecord>("/connectors", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateConnector(
  connectorId: UUID,
  payload: {
    name?: string;
    status?: "inactive" | "active" | "error";
    config?: Record<string, unknown>;
    metadata?: Record<string, unknown>;
  }
) {
  return apiFetch<ConnectorRecord>(`/connectors/${connectorId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function testConnector(
  connectorId: UUID,
  payload?: {
    message_text?: string;
    sender_name?: string;
    external_user_id?: string;
    external_chat_id?: string;
    mode?: string;
  }
) {
  return apiFetch<ConnectorTestResult>(`/connectors/${connectorId}/test`, {
    method: "POST",
    body: JSON.stringify(payload ?? {})
  });
}

export async function listConnectorDeliveries(connectorId: UUID) {
  return apiFetch<ConnectorDeliveryRecord[]>(`/connectors/${connectorId}/deliveries`);
}

export async function listConnectorMappings(connectorId: UUID) {
  return apiFetch<ConnectorConversationMappingRecord[]>(`/connectors/${connectorId}/mappings`);
}

export async function getFeishuSkeleton() {
  return apiFetch<Record<string, unknown>>("/connectors/skeleton/feishu");
}

export async function listModelProviders() {
  return apiFetch<ModelProviderConfig[]>("/model-providers");
}

export async function createModelProvider(payload: {
  name: string;
  provider_type: "deepseek" | "openai_compatible" | "ollama" | "local_adapter";
  base_url: string;
  model_name: string;
  api_key_ref?: string | null;
  settings?: Record<string, unknown>;
  is_default?: boolean;
  is_enabled?: boolean;
}) {
  return apiFetch<ModelProviderConfig>("/model-providers", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateModelProvider(
  providerId: UUID,
  payload: {
    name?: string;
    provider_type?: "deepseek" | "openai_compatible" | "ollama" | "local_adapter";
    base_url?: string;
    model_name?: string;
    api_key_ref?: string | null;
    settings?: Record<string, unknown>;
    is_default?: boolean;
    is_enabled?: boolean;
  }
) {
  return apiFetch<ModelProviderConfig>(`/model-providers/${providerId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function validateModelProvider(payload?: {
  provider_id?: UUID;
  prompt?: string;
  tool_prompt?: string;
  check_stream?: boolean;
  check_tool_call?: boolean;
}) {
  return apiFetch<ModelProviderValidationResult>("/model-providers/validate", {
    method: "POST",
    body: JSON.stringify(payload ?? {})
  });
}

export async function listLocalAdapterRuntime() {
  return apiFetch<LocalAdapterRuntimeState[]>("/model-providers/local-adapters/runtime");
}

export async function warmLocalAdapter(providerId: UUID) {
  return apiFetch<LocalAdapterRuntimeState>(`/model-providers/${providerId}/warm`, {
    method: "POST"
  });
}

export async function evictLocalAdapter(providerId: UUID) {
  return apiFetch<LocalAdapterRuntimeState>(`/model-providers/${providerId}/evict`, {
    method: "POST"
  });
}

export async function listFineTuneJobs() {
  return apiFetch<FineTuneJobRecord[]>("/fine-tuning/jobs");
}

export async function getFineTuneJob(jobId: UUID) {
  return apiFetch<FineTuneJobDetail>(`/fine-tuning/jobs/${jobId}`);
}

export async function createFineTuneJob(payload: {
  user_id: UUID;
  import_id: UUID;
  name: string;
  source_speaker: string;
  backend?: "local_lora" | "local_qlora";
  base_model?: string;
  context_window?: number;
  train_ratio?: number;
  validation_ratio?: number;
}) {
  return apiFetch<FineTuneJobDetail>("/fine-tuning/jobs", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function launchFineTuneJob(jobId: UUID, payload?: { wait?: boolean }) {
  const params = new URLSearchParams();
  if (payload?.wait) {
    params.set("wait", "true");
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  return apiFetch<FineTuneJobRecord>(`/fine-tuning/jobs/${jobId}/launch${suffix}`, {
    method: "POST"
  });
}

export async function registerFineTuneProvider(jobId: UUID) {
  return apiFetch<ModelProviderConfig>(`/fine-tuning/jobs/${jobId}/register-provider`, {
    method: "POST"
  });
}
