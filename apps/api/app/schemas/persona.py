from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PersonaBase(BaseModel):
    user_id: uuid.UUID
    source_import_id: uuid.UUID | None = None
    name: str
    description: str | None = None
    tone: str
    verbosity: str
    common_phrases: list[str] = Field(default_factory=list)
    common_topics: list[str] = Field(default_factory=list)
    response_style: dict[str, Any] = Field(default_factory=dict)
    relationship_style: dict[str, Any] = Field(default_factory=dict)
    confidence_scores: dict[str, float] = Field(default_factory=dict)
    evidence_samples: dict[str, list[str]] = Field(default_factory=dict)
    is_default: bool = False


class PersonaCreate(PersonaBase):
    pass


class PersonaUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    tone: str | None = None
    verbosity: str | None = None
    common_phrases: list[str] | None = None
    common_topics: list[str] | None = None
    response_style: dict[str, Any] | None = None
    relationship_style: dict[str, Any] | None = None
    confidence_scores: dict[str, float] | None = None
    evidence_samples: dict[str, list[str]] | None = None
    is_default: bool | None = None


class PersonaRead(PersonaBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    extracted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PersonaExtractionRequest(BaseModel):
    user_id: uuid.UUID
    import_id: uuid.UUID | None = None
    name: str = "Primary Persona"
    description: str | None = None
    source_speaker: str | None = None
    sample_messages: list[dict[str, Any]] = Field(default_factory=list)
    persist: bool = True
    set_default: bool = True


class PersonaExtractionResponse(BaseModel):
    persona: PersonaRead
    source_message_count: int
    source_speaker: str | None = None
