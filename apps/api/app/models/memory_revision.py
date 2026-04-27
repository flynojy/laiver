from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, UUIDType


class MemoryRevision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "memory_revisions"

    fact_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("memory_facts.id"), nullable=False, index=True)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    op: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    content_text: Mapped[str | None] = mapped_column(Text)
    value_json: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    confidence_delta: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default=text("0")
    )
    source_episode_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("memory_episodes.id"), nullable=True, index=True
    )
    supersedes_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType,
        ForeignKey("memory_revisions.id"),
        nullable=True,
        index=True,
    )
    conflict_group_id: Mapped[str | None] = mapped_column(String(160), index=True)
    valid_from: Mapped[datetime | None]
    valid_to: Mapped[datetime | None]
    author_type: Mapped[str] = mapped_column(
        String(40), nullable=False, default="system", server_default=text("'system'")
    )
    reason_codes: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)

    fact: Mapped["MemoryFact"] = relationship(back_populates="revisions")
    source_episode: Mapped["MemoryEpisode | None"] = relationship(back_populates="revisions")
    supersedes_revision: Mapped["MemoryRevision | None"] = relationship(remote_side="MemoryRevision.id")


from app.models.memory_episode import MemoryEpisode  # noqa: E402
from app.models.memory_fact import MemoryFact  # noqa: E402
