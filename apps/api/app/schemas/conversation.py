from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ConversationStatus, MessageRole


class ConversationCreate(BaseModel):
    user_id: uuid.UUID
    persona_id: uuid.UUID | None = None
    title: str
    summary: str | None = None
    channel: str = "web"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationUpdate(BaseModel):
    persona_id: uuid.UUID | None = None
    metadata: dict[str, Any] | None = None


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    user_id: uuid.UUID
    persona_id: uuid.UUID | None = None
    title: str
    summary: str | None = None
    channel: str
    status: ConversationStatus
    metadata: dict[str, Any] = Field(default_factory=dict, alias="context")
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    conversation_id: uuid.UUID
    parent_message_id: uuid.UUID | None = None
    role: MessageRole
    content: str
    model_name: str | None = None
    tool_name: str | None = None
    token_usage: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    sequence_index: int = 0


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    parent_message_id: uuid.UUID | None = None
    role: MessageRole
    content: str
    model_name: str | None = None
    tool_name: str | None = None
    token_usage: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict, alias="context")
    sequence_index: int
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(BaseModel):
    conversation: ConversationRead
    messages: list[MessageRead]
