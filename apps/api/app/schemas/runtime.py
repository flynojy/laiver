from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.core.enums import ConnectorPlatform, ConnectorStatus, ProviderType, SkillStatus


class SkillToolManifest(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    returns: dict[str, Any] = Field(default_factory=dict)


class SkillManifestPayload(BaseModel):
    schema_version: str = "1.0"
    name: str
    slug: str
    version: str
    title: str
    description: str
    tools: list[SkillToolManifest] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    triggers: list[str] = Field(default_factory=list)


class SkillCreate(BaseModel):
    user_id: uuid.UUID | None = None
    slug: str
    name: str
    version: str
    title: str
    description: str
    manifest: SkillManifestPayload
    runtime_config: dict[str, Any] = Field(default_factory=dict)
    status: SkillStatus = SkillStatus.ACTIVE
    is_builtin: bool = False


class SkillInstallRequest(BaseModel):
    manifest: SkillManifestPayload
    runtime_config: dict[str, Any] = Field(default_factory=dict)
    source: str = "manual"
    activate: bool = True


class SkillRead(SkillCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class SkillInvocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    invocation_id: uuid.UUID = Field(validation_alias=AliasChoices("id", "invocation_id"))
    skill_id: uuid.UUID
    skill_slug: str
    tool_name: str
    trace_id: str
    trigger_source: str
    conversation_id: uuid.UUID | None = None
    message_id: uuid.UUID | None = None
    status: str
    input: dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("input_payload", "input"))
    output: dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("output_payload", "output"))
    error: str | None = Field(default=None, validation_alias=AliasChoices("error_message", "error"))
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ConnectorNormalizedMessage(BaseModel):
    connector_id: uuid.UUID
    connector_type: str
    external_message_id: str | None = None
    external_user_id: str | None = None
    external_chat_id: str | None = None
    sender_name: str | None = None
    text: str
    occurred_at: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class ConnectorConversationMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    mapping_id: uuid.UUID = Field(validation_alias=AliasChoices("id", "mapping_id"))
    connector_id: uuid.UUID
    conversation_key: str
    external_chat_id: str | None = None
    external_user_id: str | None = None
    internal_conversation_id: uuid.UUID | None = None
    default_persona_id: uuid.UUID | None = None
    memory_scope: str
    created_at: datetime
    updated_at: datetime


class ConnectorTraceRead(BaseModel):
    connector_trace_id: str
    inbound_summary: dict[str, Any] = Field(default_factory=dict)
    normalized_input: ConnectorNormalizedMessage
    mapped_conversation_id: uuid.UUID | None = None
    persona_id: uuid.UUID | None = None
    persona_name: str | None = None
    skills_used: list[str] = Field(default_factory=list)
    fallback_status: str = "not_used"
    outbound_summary: dict[str, Any] = Field(default_factory=dict)
    delivery_status: str


class ConnectorCreate(BaseModel):
    user_id: uuid.UUID
    connector_type: ConnectorPlatform = ConnectorPlatform.FEISHU
    name: str
    status: ConnectorStatus = ConnectorStatus.INACTIVE
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorUpdate(BaseModel):
    name: str | None = None
    status: ConnectorStatus | None = None
    config: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class ConnectorDeliveryRead(BaseModel):
    delivery_id: uuid.UUID
    connector_id: uuid.UUID
    connector_type: str
    trace_id: str
    internal_conversation_id: uuid.UUID | None = None
    external_message_id: str | None = None
    inbound_message: dict[str, Any] = Field(default_factory=dict)
    normalized_input: ConnectorNormalizedMessage
    agent_response: dict[str, Any] = Field(default_factory=dict)
    outbound_response: dict[str, Any] = Field(default_factory=dict)
    mapping: ConnectorConversationMappingRead | None = None
    trace: ConnectorTraceRead | None = None
    delivery_status: str
    mode: str
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class ConnectorTestRequest(BaseModel):
    message_text: str = "Hello from the Feishu connector test path."
    sender_name: str = "Connector Test"
    external_user_id: str = "test_user"
    external_chat_id: str = "test_chat"
    mode: str | None = None


class ConnectorTestResponse(BaseModel):
    connector: ConnectorRead
    normalized_input: ConnectorNormalizedMessage
    mapping: ConnectorConversationMappingRead | None = None
    trace: ConnectorTraceRead | None = None
    agent_response: dict[str, Any]
    outbound_response: dict[str, Any]
    delivery_status: str
    error: str | None = None


class ConnectorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    connector_id: uuid.UUID = Field(validation_alias=AliasChoices("id", "connector_id"))
    user_id: uuid.UUID
    connector_type: ConnectorPlatform = Field(validation_alias=AliasChoices("platform", "connector_type"))
    name: str
    status: ConnectorStatus
    config: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("extra", "metadata"))
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ModelProviderCreate(BaseModel):
    user_id: uuid.UUID | None = None
    name: str
    provider_type: ProviderType
    base_url: str
    model_name: str
    api_key_ref: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False
    is_enabled: bool = True


class ModelProviderUpdate(BaseModel):
    name: str | None = None
    provider_type: ProviderType | None = None
    base_url: str | None = None
    model_name: str | None = None
    api_key_ref: str | None = None
    settings: dict[str, Any] | None = None
    is_default: bool | None = None
    is_enabled: bool | None = None


class ModelProviderRead(ModelProviderCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ModelProviderValidationRequest(BaseModel):
    provider_id: uuid.UUID | None = None
    prompt: str = "Reply with the exact text: pong-live"
    tool_prompt: str = "Call the echo_status tool with {\"status\":\"ok\"}."
    check_stream: bool = True
    check_tool_call: bool = True


class ModelProviderValidationResponse(BaseModel):
    provider_id: uuid.UUID | None = None
    provider_name: str
    provider_type: ProviderType
    model_name: str
    base_url: str
    api_key_configured: bool
    mode: str
    completion_ok: bool
    stream_ok: bool
    tool_call_ok: bool
    completion_preview: str = ""
    stream_preview: str = ""
    tool_calls: list["ModelToolCall"] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    checked_at: datetime


class LocalAdapterRuntimeRead(BaseModel):
    provider_id: uuid.UUID
    provider_name: str
    provider_type: ProviderType = ProviderType.LOCAL_ADAPTER
    model_name: str
    base_model: str
    adapter_path: str
    inference_mode: str
    status: str
    resident: bool
    device: str | None = None
    load_count: int = 0
    request_count: int = 0
    active_request_count: int = 0
    evict_count: int = 0
    load_duration_ms: int | None = None
    memory_allocated_mb: float | None = None
    memory_reserved_mb: float | None = None
    idle_seconds: int | None = None
    idle_timeout_seconds: int = 0
    generate_timeout_seconds: float = 0
    loaded_at: datetime | None = None
    last_used_at: datetime | None = None
    last_evicted_at: datetime | None = None
    last_eviction_reason: str | None = None
    error: str | None = None


class ToolDefinition(BaseModel):
    type: Literal["function"] = "function"
    function: dict[str, Any]


class ModelMessage(BaseModel):
    role: str
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class ModelCompletionRequest(BaseModel):
    provider_id: uuid.UUID | None = None
    model: str | None = None
    messages: list[ModelMessage]
    tools: list[ToolDefinition] = Field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 800


class ModelToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class ModelCompletionResponse(BaseModel):
    content: str
    model: str
    provider: str
    finish_reason: str = "stop"
    tool_calls: list[ModelToolCall] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)


ModelProviderValidationResponse.model_rebuild()
