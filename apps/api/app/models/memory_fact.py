from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, UUIDType


class MemoryFact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "memory_facts"

    user_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    persona_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("personas.id"), nullable=True, index=True
    )
    fact_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    subject_kind: Mapped[str] = mapped_column(
        String(80), nullable=False, default="user", server_default=text("'user'")
    )
    subject_ref: Mapped[str | None] = mapped_column(String(160), index=True)
    predicate_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    value_text: Mapped[str | None] = mapped_column(Text)
    value_json: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    normalized_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="active", server_default=text("'active'")
    )
    current_revision_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default=text("0.5"))
    importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default=text("0.5"))
    stability_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5, server_default=text("0.5")
    )
    reinforcement_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    effective_from: Mapped[datetime | None]
    effective_to: Mapped[datetime | None]
    last_confirmed_at: Mapped[datetime | None]
    last_used_at: Mapped[datetime | None]
    decay_policy: Mapped[str] = mapped_column(
        String(80), nullable=False, default="default", server_default=text("'default'")
    )
    sensitivity: Mapped[str] = mapped_column(
        String(40), nullable=False, default="normal", server_default=text("'normal'")
    )
    details: Mapped[dict] = mapped_column("metadata", JSONType, nullable=False, default=dict)

    user: Mapped["User"] = relationship(back_populates="memory_facts")
    persona: Mapped["Persona | None"] = relationship(back_populates="memory_facts")
    revisions: Mapped[list["MemoryRevision"]] = relationship(
        back_populates="fact",
        cascade="all, delete-orphan",
        order_by="MemoryRevision.revision_no",
    )


from app.models.memory_revision import MemoryRevision  # noqa: E402
from app.models.user import Persona, User  # noqa: E402
