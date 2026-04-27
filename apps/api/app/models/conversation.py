from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ConversationStatus, MessageRole
from app.models.base import Base, EnumType, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, UUIDType


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    persona_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("personas.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(80), nullable=False, default="web", server_default=text("'web'"))
    status: Mapped[ConversationStatus] = mapped_column(
        EnumType(ConversationStatus, name="conversationstatus"),
        default=ConversationStatus.ACTIVE,
        nullable=False,
        server_default=text("'active'"),
    )
    context: Mapped[dict] = mapped_column("metadata", JSONType, nullable=False, default=dict)

    user: Mapped["User"] = relationship(back_populates="conversations")
    persona: Mapped["Persona | None"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.sequence_index",
    )
    memories: Mapped[list["Memory"]] = relationship(back_populates="conversation")
    memory_episodes: Mapped[list["MemoryEpisode"]] = relationship(back_populates="conversation")


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("conversations.id"), nullable=False, index=True
    )
    parent_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("messages.id"), nullable=True
    )
    role: Mapped[MessageRole] = mapped_column(
        EnumType(MessageRole, name="messagerole"),
        nullable=False,
        default=MessageRole.USER,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(120))
    tool_name: Mapped[str | None] = mapped_column(String(120))
    token_usage: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    context: Mapped[dict] = mapped_column("metadata", JSONType, nullable=False, default=dict)
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    parent_message: Mapped["Message | None"] = relationship(remote_side="Message.id")
    memories: Mapped[list["Memory"]] = relationship(back_populates="source_message")
    memory_episodes: Mapped[list["MemoryEpisode"]] = relationship(back_populates="source_message")


from app.models.memory import Memory  # noqa: E402
from app.models.memory_episode import MemoryEpisode  # noqa: E402
from app.models.user import Persona, User  # noqa: E402
