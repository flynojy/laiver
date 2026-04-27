from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    email: str
    display_name: str
    avatar_url: str | None = None
    preferences: dict[str, Any] = Field(default_factory=dict)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    avatar_url: str | None = None
    preferences: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BootstrapUserResponse(BaseModel):
    user: UserRead
    created: bool

