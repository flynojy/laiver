from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RelationshipStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    persona_id: uuid.UUID
    relationship_stage: str
    warmth_score: float
    trust_score: float
    familiarity_score: float
    preferred_tone: str | None = None
    active_topics: list[str] = Field(default_factory=list)
    recurring_rituals: list[str] = Field(default_factory=list)
    recent_sensitivities: list[str] = Field(default_factory=list)
    unresolved_tensions: list[str] = Field(default_factory=list)
    last_meaningful_interaction_at: datetime | None = None
    last_repair_at: datetime | None = None
    summary: str
    version: int
    created_at: datetime
    updated_at: datetime


class RelationshipStateUpdate(BaseModel):
    relationship_stage: str | None = None
    warmth_score: float | None = None
    trust_score: float | None = None
    familiarity_score: float | None = None
    preferred_tone: str | None = None
    active_topics: list[str] | None = None
    recurring_rituals: list[str] | None = None
    recent_sensitivities: list[str] | None = None
    unresolved_tensions: list[str] | None = None
    summary: str | None = None
