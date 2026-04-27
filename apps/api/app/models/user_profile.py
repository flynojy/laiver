from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, UUIDType


class UserProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    core_identity: Mapped[dict] = mapped_column("core_identity_json", JSONType, nullable=False, default=dict)
    communication_style: Mapped[dict] = mapped_column(
        "communication_style_json", JSONType, nullable=False, default=dict
    )
    stable_preferences: Mapped[dict] = mapped_column(
        "stable_preferences_json", JSONType, nullable=False, default=dict
    )
    boundaries: Mapped[dict] = mapped_column("boundaries_json", JSONType, nullable=False, default=dict)
    life_context: Mapped[dict] = mapped_column("life_context_json", JSONType, nullable=False, default=dict)
    profile_summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default=text("''"))
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    source_fact_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    last_rebuilt_at: Mapped[datetime | None]
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default=text("0.5"))

    user: Mapped["User"] = relationship(back_populates="user_profile")


from app.models.user import User  # noqa: E402
