from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, UUIDType


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    preferences: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    personas: Mapped[list["Persona"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    imports: Mapped[list["ImportJob"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    memories: Mapped[list["Memory"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    memory_episodes: Mapped[list["MemoryEpisode"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    memory_facts: Mapped[list["MemoryFact"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    memory_candidates: Mapped[list["MemoryCandidate"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    user_profile: Mapped["UserProfile | None"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    relationship_states: Mapped[list["RelationshipState"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    connectors: Mapped[list["Connector"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    fine_tune_jobs: Mapped[list["FineTuneJob"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Persona(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "personas"

    user_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    source_import_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("imports.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    tone: Mapped[str] = mapped_column(String(120), nullable=False)
    verbosity: Mapped[str] = mapped_column(String(60), nullable=False)
    common_phrases: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    common_topics: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    response_style: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    relationship_style: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    confidence_scores: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    evidence_samples: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    extracted_at: Mapped[datetime | None]

    user: Mapped["User"] = relationship(back_populates="personas")
    source_import: Mapped["ImportJob | None"] = relationship(back_populates="personas")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="persona")
    memories: Mapped[list["Memory"]] = relationship(back_populates="persona")
    memory_episodes: Mapped[list["MemoryEpisode"]] = relationship(back_populates="persona")
    memory_facts: Mapped[list["MemoryFact"]] = relationship(back_populates="persona")
    memory_candidates: Mapped[list["MemoryCandidate"]] = relationship(back_populates="persona")
    relationship_states: Mapped[list["RelationshipState"]] = relationship(back_populates="persona")


from app.models.conversation import Conversation  # noqa: E402
from app.models.fine_tuning import FineTuneJob  # noqa: E402
from app.models.import_job import ImportJob  # noqa: E402
from app.models.memory_candidate import MemoryCandidate  # noqa: E402
from app.models.memory_episode import MemoryEpisode  # noqa: E402
from app.models.memory_fact import MemoryFact  # noqa: E402
from app.models.memory import Memory  # noqa: E402
from app.models.relationship_state import RelationshipState  # noqa: E402
from app.models.runtime import Connector  # noqa: E402
from app.models.user_profile import UserProfile  # noqa: E402
