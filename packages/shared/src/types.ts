export type UUID = string;

export type MessageRole = "system" | "user" | "assistant" | "tool";
export type ImportSourceType = "txt" | "csv" | "json" | "xlsx";
export type ImportStatus = "previewed" | "committed" | "failed";
export type MemoryType = "session" | "episodic" | "semantic" | "instruction";
export type ConnectorPlatform = "feishu";
export type ConnectorStatus = "inactive" | "active" | "error";
export type MemoryScope = "chat" | "user";
export type ProviderType = "deepseek" | "openai_compatible" | "ollama" | "local_adapter";
export type SkillStatus = "disabled" | "active";
export type FineTuneBackend = "local_lora" | "local_qlora";
export type FineTuneJobStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export interface NormalizedMessage {
  sequence_index: number;
  speaker: string;
  role: MessageRole;
  content: string;
  occurred_at?: string | null;
  metadata: Record<string, unknown>;
}

export interface ImportSourceMetadata {
  source_format?: string | null;
  conversation_owner?: string | null;
  export_tool?: string | null;
  export_version?: string | null;
  platform?: string | null;
  exported_at?: string | null;
  message_types?: string[];
  speaker_stats?: Record<
    string,
    {
      message_count: number;
      roles: string[];
      is_self: boolean;
    }
  >;
}

export interface ImportPreviewSummary {
  source_type: ImportSourceType;
  file_name: string;
  total_messages: number;
  detected_participants: string[];
  source_metadata: ImportSourceMetadata;
  sample_messages: NormalizedMessage[];
  normalized_messages?: NormalizedMessage[];
}

export interface PersonaCard {
  id?: UUID;
  user_id: UUID;
  name: string;
  description?: string | null;
  tone: string;
  verbosity: string;
  common_phrases: string[];
  common_topics: string[];
  response_style: Record<string, unknown>;
  relationship_style: Record<string, unknown>;
  confidence_scores: Record<string, number>;
  evidence_samples: Record<string, string[]>;
  source_import_id?: UUID | null;
  is_default: boolean;
  extracted_at?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface MemoryRecord {
  id?: UUID;
  user_id: UUID;
  persona_id?: UUID | null;
  conversation_id?: UUID | null;
  source_message_id?: UUID | null;
  memory_type: MemoryType;
  content: string;
  importance_score: number;
  confidence_score: number;
  access_count?: number;
  metadata: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
  last_accessed_at?: string | null;
}

export interface MemoryEpisodeRecord {
  id: UUID;
  user_id: UUID;
  persona_id?: UUID | null;
  conversation_id?: UUID | null;
  source_message_id?: UUID | null;
  source_type: string;
  source_ref?: string | null;
  speaker_role?: string | null;
  occurred_at?: string | null;
  raw_text: string;
  structured_payload: Record<string, unknown>;
  summary_short?: string | null;
  summary_medium?: string | null;
  importance: number;
  emotional_weight: number;
  embedding_vector_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MemoryRevisionRecord {
  id: UUID;
  fact_id: UUID;
  revision_no: number;
  op: string;
  content_text?: string | null;
  value_json: Record<string, unknown>;
  confidence_delta: number;
  source_episode_id?: UUID | null;
  supersedes_revision_id?: UUID | null;
  conflict_group_id?: string | null;
  valid_from?: string | null;
  valid_to?: string | null;
  author_type: string;
  reason_codes: unknown[];
  created_at: string;
  updated_at: string;
}

export interface MemoryFactRecord {
  id: UUID;
  user_id: UUID;
  persona_id?: UUID | null;
  fact_type: string;
  subject_kind: string;
  subject_ref?: string | null;
  predicate_key: string;
  value_text?: string | null;
  value_json: Record<string, unknown>;
  normalized_key: string;
  status: string;
  current_revision_id?: UUID | null;
  confidence: number;
  importance: number;
  stability_score: number;
  reinforcement_count: number;
  source_count: number;
  effective_from?: string | null;
  effective_to?: string | null;
  last_confirmed_at?: string | null;
  last_used_at?: string | null;
  decay_policy: string;
  sensitivity: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface UserProfileRecord {
  id: UUID;
  user_id: UUID;
  core_identity: Record<string, unknown>;
  communication_style: Record<string, unknown>;
  stable_preferences: Record<string, unknown>;
  boundaries: Record<string, unknown>;
  life_context: Record<string, unknown>;
  profile_summary: string;
  profile_version: number;
  source_fact_count: number;
  last_rebuilt_at?: string | null;
  confidence: number;
  created_at: string;
  updated_at: string;
}

export interface RelationshipStateRecord {
  id: UUID;
  user_id: UUID;
  persona_id: UUID;
  relationship_stage: string;
  warmth_score: number;
  trust_score: number;
  familiarity_score: number;
  preferred_tone?: string | null;
  active_topics: string[];
  recurring_rituals: string[];
  recent_sensitivities: string[];
  unresolved_tensions: string[];
  last_meaningful_interaction_at?: string | null;
  last_repair_at?: string | null;
  summary: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface MemoryCandidateRecord {
  id: UUID;
  user_id: UUID;
  persona_id?: UUID | null;
  episode_id: UUID;
  candidate_type: string;
  extracted_text: string;
  normalized_key: string;
  proposed_value: Record<string, unknown>;
  proposed_action: string;
  salience_score: number;
  confidence_score: number;
  sensitivity: string;
  reason_codes: unknown[];
  auto_commit: boolean;
  status: string;
  reviewer_type?: string | null;
  processed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MemoryMaintenanceReport {
  run_at: string;
  dry_run: boolean;
  facts_scanned: number;
  facts_decayed: number;
  facts_archived: number;
  candidates_scanned: number;
  candidates_ignored: number;
  profiles_rebuilt: number;
  decayed_fact_ids: string[];
  archived_fact_ids: string[];
  ignored_candidate_ids: string[];
}

export interface SkillToolManifest {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
  returns: Record<string, unknown>;
}

export interface SkillManifest {
  schema_version: string;
  name: string;
  slug: string;
  version: string;
  title: string;
  description: string;
  tools: SkillToolManifest[];
  permissions: string[];
  triggers: string[];
}

export interface SkillRecord {
  id: UUID;
  user_id?: UUID | null;
  slug: string;
  name: string;
  version: string;
  title: string;
  description: string;
  manifest: SkillManifest;
  runtime_config: Record<string, unknown>;
  status: SkillStatus;
  is_builtin: boolean;
  created_at: string;
  updated_at: string;
}

export interface SkillInvocationRecord {
  invocation_id: UUID;
  skill_id: UUID;
  skill_slug: string;
  tool_name: string;
  trace_id: string;
  trigger_source: string;
  conversation_id?: UUID | null;
  message_id?: UUID | null;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  error?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface ConnectorRecord {
  connector_id: UUID;
  user_id: UUID;
  connector_type: ConnectorPlatform;
  name: string;
  status: ConnectorStatus;
  config: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ConnectorNormalizedMessage {
  connector_id: UUID;
  connector_type: ConnectorPlatform;
  external_message_id?: string | null;
  external_user_id?: string | null;
  external_chat_id?: string | null;
  sender_name?: string | null;
  text: string;
  occurred_at?: string | null;
  raw_payload: Record<string, unknown>;
}

export interface ConnectorConversationMappingRecord {
  mapping_id: UUID;
  connector_id: UUID;
  conversation_key: string;
  external_chat_id?: string | null;
  external_user_id?: string | null;
  internal_conversation_id?: UUID | null;
  default_persona_id?: UUID | null;
  memory_scope: MemoryScope;
  created_at: string;
  updated_at: string;
}

export interface ConnectorTraceRecord {
  connector_trace_id: string;
  inbound_summary: Record<string, unknown>;
  normalized_input: ConnectorNormalizedMessage;
  mapped_conversation_id?: UUID | null;
  persona_id?: UUID | null;
  persona_name?: string | null;
  skills_used: string[];
  fallback_status: string;
  outbound_summary: Record<string, unknown>;
  delivery_status: string;
}

export interface ConnectorDeliveryRecord {
  delivery_id: UUID;
  connector_id: UUID;
  connector_type: ConnectorPlatform;
  trace_id: string;
  internal_conversation_id?: UUID | null;
  external_message_id?: string | null;
  inbound_message: Record<string, unknown>;
  normalized_input: ConnectorNormalizedMessage;
  agent_response: Record<string, unknown>;
  outbound_response: Record<string, unknown>;
  mapping?: ConnectorConversationMappingRecord | null;
  trace?: ConnectorTraceRecord | null;
  delivery_status: string;
  mode: string;
  error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConnectorTestResult {
  connector: ConnectorRecord;
  normalized_input: ConnectorNormalizedMessage;
  mapping?: ConnectorConversationMappingRecord | null;
  trace?: ConnectorTraceRecord | null;
  agent_response: Record<string, unknown>;
  outbound_response: Record<string, unknown>;
  delivery_status: string;
  error?: string | null;
}

export interface ModelProviderConfig {
  id?: UUID;
  name: string;
  provider_type: ProviderType;
  base_url: string;
  model_name: string;
  api_key_ref?: string | null;
  settings: Record<string, unknown>;
  is_default: boolean;
  is_enabled?: boolean;
}

export interface ModelProviderValidationResult {
  provider_id?: UUID | null;
  provider_name: string;
  provider_type: ProviderType;
  model_name: string;
  base_url: string;
  api_key_configured: boolean;
  mode: string;
  completion_ok: boolean;
  stream_ok: boolean;
  tool_call_ok: boolean;
  completion_preview: string;
  stream_preview: string;
  tool_calls: {
    id: string;
    name: string;
    arguments: Record<string, unknown>;
  }[];
  usage: Record<string, unknown>;
  error?: string | null;
  checked_at: string;
}

export interface LocalAdapterRuntimeState {
  provider_id: UUID;
  provider_name: string;
  provider_type: "local_adapter";
  model_name: string;
  base_model: string;
  adapter_path: string;
  inference_mode: string;
  status: string;
  resident: boolean;
  device?: string | null;
  load_count: number;
  request_count: number;
  active_request_count: number;
  evict_count: number;
  load_duration_ms?: number | null;
  memory_allocated_mb?: number | null;
  memory_reserved_mb?: number | null;
  idle_seconds?: number | null;
  idle_timeout_seconds: number;
  generate_timeout_seconds: number;
  loaded_at?: string | null;
  last_used_at?: string | null;
  last_evicted_at?: string | null;
  last_eviction_reason?: string | null;
  error?: string | null;
}

export interface FineTuneDatasetPreviewSample {
  messages: {
    role: "system" | "user" | "assistant";
    content: string;
  }[];
}

export interface FineTuneJobRecord {
  id: UUID;
  user_id: UUID;
  import_id: UUID;
  name: string;
  source_speaker: string;
  backend: FineTuneBackend;
  status: FineTuneJobStatus;
  base_model: string;
  context_window: number;
  source_message_count: number;
  train_examples: number;
  validation_examples: number;
  test_examples: number;
  dataset_path: string;
  config_path: string;
  output_dir: string;
  launcher_command: string;
  training_config: Record<string, unknown>;
  dataset_stats: Record<string, unknown>;
  artifact_path?: string | null;
  error_message?: string | null;
  registered_provider_id?: UUID | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface FineTuneJobDetail {
  job: FineTuneJobRecord;
  dataset_preview: FineTuneDatasetPreviewSample[];
  registered_provider?: ModelProviderConfig | null;
}

export interface AgentChatRequest {
  user_id: UUID;
  conversation_id?: UUID | null;
  persona_id?: UUID | null;
  message: string;
  controls?: ConversationControls;
}

export interface ConversationControls {
  skills_enabled: boolean;
  memory_write_enabled: boolean;
}

export interface AnswerExplanation {
  memories_used: MemoryRecord[];
  persona_fields_used: string[];
  skill_outputs_used: string[];
}

export interface AgentDebugInfo {
  trace_id: string;
  provider_name: string;
  model_name: string;
  model_mode: string;
  persona_id?: UUID | null;
  persona_name?: string | null;
  memory_write_count: number;
  conversation_summary?: string | null;
  compression_active: boolean;
  summarized_message_count: number;
  recent_message_count: number;
  memory_query_route: string;
  memory_hits: MemoryRecord[];
  memory_writes: MemoryRecord[];
  skills_used: string[];
  skill_invocations: SkillInvocationRecord[];
  skill_invocation_summary: string[];
  skill_output_summary: string[];
  skills_enabled: boolean;
  memory_write_enabled: boolean;
  explanation: AnswerExplanation;
  fallback_status: string;
}

export interface AgentChatResponse {
  conversation_id: UUID;
  user_message_id: UUID;
  assistant_message_id: UUID;
  response: string;
  persona?: PersonaCard | null;
  debug: AgentDebugInfo;
}

export interface SkillRuntimeSummary {
  skills: SkillRecord[];
  invocations: SkillInvocationRecord[];
}
