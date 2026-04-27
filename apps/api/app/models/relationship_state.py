from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, UUIDType


class RelationshipState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "relationship_states"
    __table_args__ = (UniqueConstraint("user_id", "persona_id", name="uq_relationship_states_user_persona"),)

    user_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    persona_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("personas.id"), nullable=False, index=True)
    relationship_stage: Mapped[str] = mapped_column(
        String(80), nullable=False, default="new", server_default=text("'new'")
    )
    warmth_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default=text("0.5"))
    trust_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default=text("0.5"))
    familiarity_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5, server_default=text("0.5")
    )
    preferred_tone: Mapped[str | None] = mapped_column(String(120))
    active_topics: Mapped[list] = mapped_column("active_topics_json", JSONType, nullable=False, default=list)
    recurring_rituals: Mapped[list] = mapped_column(
        "recurring_rituals_json", JSONType, nullable=False, default=list
    )
    recent_sensitivities: Mapped[list] = mapped_column(
        "recent_sensitivities_json", JSONType, nullable=False, default=list
    )
    unresolved_tensions: Mapped[list] = mapped_column(
        "unresolved_tensions_json", JSONType, nullable=False, default=list
    )
    last_meaningful_interaction_at: Mapped[datetime | None]
    last_repair_at: Mapped[datetime | None]
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default=text("''"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))

    user: Mapped["User"] = relationship(back_populates="relationship_states")
    persona: Mapped["Persona"] = relationship(back_populates="relationship_states")


from app.models.user import Persona, User  # noqa: E402
