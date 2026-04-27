from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, UUIDType


class MemoryEpisode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "memory_episodes"

    user_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    persona_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("personas.id"), nullable=True, index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("conversations.id"), nullable=True, index=True
    )
    source_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("messages.id"), nullable=True, index=True
    )
    source_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    source_ref: Mapped[str | None] = mapped_column(String(255), index=True)
    speaker_role: Mapped[str | None] = mapped_column(String(40))
    occurred_at: Mapped[datetime | None]
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_payload: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    summary_short: Mapped[str | None] = mapped_column(String(500))
    summary_medium: Mapped[str | None] = mapped_column(Text)
    importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default=text("0.5"))
    emotional_weight: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default=text("0")
    )
    embedding_vector_id: Mapped[str | None] = mapped_column(String(64), index=True)

    user: Mapped["User"] = relationship(back_populates="memory_episodes")
    persona: Mapped["Persona | None"] = relationship(back_populates="memory_episodes")
    conversation: Mapped["Conversation | None"] = relationship(back_populates="memory_episodes")
    source_message: Mapped["Message | None"] = relationship(back_populates="memory_episodes")
    candidates: Mapped[list["MemoryCandidate"]] = relationship(
        back_populates="episode",
        cascade="all, delete-orphan",
    )
    revisions: Mapped[list["MemoryRevision"]] = relationship(back_populates="source_episode")


from app.models.conversation import Conversation, Message  # noqa: E402
from app.models.memory_candidate import MemoryCandidate  # noqa: E402
from app.models.memory_revision import MemoryRevision  # noqa: E402
from app.models.user import Persona, User  # noqa: E402
