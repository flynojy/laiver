from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class MemoryRevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fact_id: uuid.UUID
    revision_no: int
    op: str
    content_text: str | None = None
    value_json: dict[str, Any] = Field(default_factory=dict)
    confidence_delta: float
    source_episode_id: uuid.UUID | None = None
    supersedes_revision_id: uuid.UUID | None = None
    conflict_group_id: str | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    author_type: str
    reason_codes: list[Any] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class MemoryFactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    user_id: uuid.UUID
    persona_id: uuid.UUID | None = None
    fact_type: str
    subject_kind: str
    subject_ref: str | None = None
    predicate_key: str
    value_text: str | None = None
    value_json: dict[str, Any] = Field(default_factory=dict)
    normalized_key: str
    status: str
    current_revision_id: uuid.UUID | None = None
    confidence: float
    importance: float
    stability_score: float
    reinforcement_count: int
    source_count: int
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    last_confirmed_at: datetime | None = None
    last_used_at: datetime | None = None
    decay_policy: str
    sensitivity: str
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("details", "metadata"),
    )
    created_at: datetime
    updated_at: datetime


class MemoryFactUpdate(BaseModel):
    status: str | None = None
    value_text: str | None = None
    value_json: dict[str, Any] | None = None
    confidence: float | None = None
    importance: float | None = None
    stability_score: float | None = None
    decay_policy: str | None = None
    sensitivity: str | None = None
    metadata: dict[str, Any] | None = None
