from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ImportSourceType, ImportStatus, MessageRole


class NormalizedMessageBase(BaseModel):
    external_id: str | None = None
    speaker: str
    role: MessageRole
    content: str
    occurred_at: datetime | None = None
    sequence_index: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedMessageCreate(NormalizedMessageBase):
    pass


class NormalizedMessageRead(NormalizedMessageBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    metadata: dict[str, Any] = Field(default_factory=dict, alias="details")
    created_at: datetime
    updated_at: datetime


class ImportPreviewResponse(BaseModel):
    file_name: str
    source_type: ImportSourceType
    total_messages: int
    detected_participants: list[str]
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    sample_messages: list[NormalizedMessageBase]
    normalized_messages: list[NormalizedMessageBase]


class ImportCommitRequest(BaseModel):
    user_id: uuid.UUID
    file_name: str
    source_type: ImportSourceType
    file_size: int = 0
    raw_text: str | None = None
    raw_payload: dict[str, Any] | list[Any] | None = None
    preview: dict[str, Any] = Field(default_factory=dict)
    normalized_messages: list[NormalizedMessageCreate]


class ImportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    user_id: uuid.UUID
    file_name: str
    source_type: ImportSourceType
    status: ImportStatus
    file_size: int
    raw_text: str | None = None
    raw_payload: dict[str, Any] | list[Any] | None = None
    preview_payload: dict[str, Any] = Field(default_factory=dict, alias="preview_payload")
    normalized_summary: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ImportDetailResponse(BaseModel):
    import_job: ImportRead
    normalized_messages: list[NormalizedMessageRead]
