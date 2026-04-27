from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MemoryCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    persona_id: uuid.UUID | None = None
    episode_id: uuid.UUID
    candidate_type: str
    extracted_text: str
    normalized_key: str
    proposed_value: dict[str, Any] = Field(default_factory=dict)
    proposed_action: str
    salience_score: float
    confidence_score: float
    sensitivity: str
    reason_codes: list[Any] = Field(default_factory=list)
    auto_commit: bool
    status: str
    reviewer_type: str | None = None
    processed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class MemoryCandidateUpdate(BaseModel):
    proposed_action: str | None = None
    salience_score: float | None = None
    confidence_score: float | None = None
    sensitivity: str | None = None
    reason_codes: list[Any] | None = None
    auto_commit: bool | None = None
    status: str | None = None
    reviewer_type: str | None = None
