from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, UUIDType


class MemoryCandidate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "memory_candidates"

    user_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    persona_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("personas.id"), nullable=True, index=True
    )
    episode_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("memory_episodes.id"), nullable=False, index=True
    )
    candidate_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    proposed_value: Mapped[dict] = mapped_column("proposed_value_json", JSONType, nullable=False, default=dict)
    proposed_action: Mapped[str] = mapped_column(
        String(40), nullable=False, default="create", server_default=text("'create'")
    )
    salience_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default=text("0.5"))
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5, server_default=text("0.5")
    )
    sensitivity: Mapped[str] = mapped_column(
        String(40), nullable=False, default="normal", server_default=text("'normal'")
    )
    reason_codes: Mapped[list] = mapped_column("reason_codes_json", JSONType, nullable=False, default=list)
    auto_commit: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="pending", server_default=text("'pending'")
    )
    reviewer_type: Mapped[str | None] = mapped_column(String(40))
    processed_at: Mapped[datetime | None]

    user: Mapped["User"] = relationship(back_populates="memory_candidates")
    persona: Mapped["Persona | None"] = relationship(back_populates="memory_candidates")
    episode: Mapped["MemoryEpisode"] = relationship(back_populates="candidates")


from app.models.memory_episode import MemoryEpisode  # noqa: E402
from app.models.user import Persona, User  # noqa: E402
