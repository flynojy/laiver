from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    core_identity: dict[str, Any] = Field(default_factory=dict)
    communication_style: dict[str, Any] = Field(default_factory=dict)
    stable_preferences: dict[str, Any] = Field(default_factory=dict)
    boundaries: dict[str, Any] = Field(default_factory=dict)
    life_context: dict[str, Any] = Field(default_factory=dict)
    profile_summary: str
    profile_version: int
    source_fact_count: int
    last_rebuilt_at: datetime | None = None
    confidence: float
    created_at: datetime
    updated_at: datetime
