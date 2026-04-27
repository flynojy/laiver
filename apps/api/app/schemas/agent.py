from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.schemas.memory import MemoryRead
from app.schemas.persona import PersonaRead
from app.schemas.runtime import SkillInvocationRead


class ConversationControls(BaseModel):
    skills_enabled: bool = True
    memory_write_enabled: bool = True


class AnswerExplanation(BaseModel):
    memories_used: list[MemoryRead] = Field(default_factory=list)
    persona_fields_used: list[str] = Field(default_factory=list)
    skill_outputs_used: list[str] = Field(default_factory=list)


class AgentChatRequest(BaseModel):
    user_id: uuid.UUID
    conversation_id: uuid.UUID | None = None
    persona_id: uuid.UUID | None = None
    message: str
    controls: ConversationControls | None = None


class AgentDebugInfo(BaseModel):
    trace_id: str
    provider_name: str
    model_name: str
    model_mode: str
    persona_id: uuid.UUID | None = None
    persona_name: str | None = None
    memory_write_count: int
    conversation_summary: str | None = None
    compression_active: bool = False
    summarized_message_count: int = 0
    recent_message_count: int = 0
    memory_query_route: str = "general"
    memory_hits: list[MemoryRead]
    memory_writes: list[MemoryRead]
    skills_used: list[str]
    skill_invocations: list[SkillInvocationRead] = Field(default_factory=list)
    skill_invocation_summary: list[str] = Field(default_factory=list)
    skill_output_summary: list[str] = Field(default_factory=list)
    skills_enabled: bool = True
    memory_write_enabled: bool = True
    explanation: AnswerExplanation = Field(default_factory=AnswerExplanation)
    fallback_status: str


class AgentChatResponse(BaseModel):
    conversation_id: uuid.UUID
    user_message_id: uuid.UUID
    assistant_message_id: uuid.UUID
    response: str
    persona: PersonaRead | None = None
    debug: AgentDebugInfo
