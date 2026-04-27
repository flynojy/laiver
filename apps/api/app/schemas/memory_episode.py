from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MemoryEpisodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    persona_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    source_message_id: uuid.UUID | None = None
    source_type: str
    source_ref: str | None = None
    speaker_role: str | None = None
    occurred_at: datetime | None = None
    raw_text: str
    structured_payload: dict[str, Any] = Field(default_factory=dict)
    summary_short: str | None = None
    summary_medium: str | None = None
    importance: float
    emotional_weight: float
    embedding_vector_id: str | None = None
    created_at: datetime
    updated_at: datetime
