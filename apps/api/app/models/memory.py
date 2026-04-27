from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import MemoryType
from app.models.base import Base, EnumType, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, UUIDType


class Memory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "memories"
    __table_args__ = (UniqueConstraint("user_id", "memory_type", "content_hash", name="uq_memories_hash"),)

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
    memory_type: Mapped[MemoryType] = mapped_column(
        EnumType(MemoryType, name="memorytype"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_model: Mapped[str] = mapped_column(
        String(120), nullable=False, default="hash-embedding-v1", server_default=text("'hash-embedding-v1'")
    )
    vector_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    importance_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5, server_default=text("0.5")
    )
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5, server_default=text("0.5")
    )
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    last_accessed_at: Mapped[datetime | None]
    details: Mapped[dict] = mapped_column("metadata", JSONType, nullable=False, default=dict)

    user: Mapped["User"] = relationship(back_populates="memories")
    persona: Mapped["Persona | None"] = relationship(back_populates="memories")
    conversation: Mapped["Conversation | None"] = relationship(back_populates="memories")
    source_message: Mapped["Message | None"] = relationship(back_populates="memories")


from app.models.conversation import Conversation, Message  # noqa: E402
from app.models.user import Persona, User  # noqa: E402
