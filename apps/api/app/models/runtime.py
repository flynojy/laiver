from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ConnectorPlatform, ConnectorStatus, ProviderType, SkillStatus
from app.models.base import Base, EnumType, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, UUIDType


class Skill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "skills"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("users.id"), nullable=True, index=True
    )
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False, default="1.0.0", server_default="1.0.0")
    title: Mapped[str] = mapped_column(String(160), nullable=False, default="", server_default="")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    manifest: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    runtime_config: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    status: Mapped[SkillStatus] = mapped_column(
        EnumType(SkillStatus, name="skillstatus"),
        nullable=False,
        default=SkillStatus.ACTIVE,
    )
    is_builtin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    invocations: Mapped[list["SkillInvocation"]] = relationship(back_populates="skill")


class SkillInvocation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "skill_invocations"

    skill_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("skills.id"), nullable=False, index=True)
    skill_slug: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    tool_name: Mapped[str] = mapped_column(String(120), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    trigger_source: Mapped[str] = mapped_column(String(40), nullable=False, default="planner")
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType, ForeignKey("conversations.id"), nullable=True)
    message_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType, ForeignKey("messages.id"), nullable=True)
    input_payload: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    output_payload: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="success", server_default="success")
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]

    skill: Mapped[Skill] = relationship(back_populates="invocations")


class Connector(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "connectors"

    user_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    platform: Mapped[ConnectorPlatform] = mapped_column(
        EnumType(ConnectorPlatform, name="connectorplatform"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[ConnectorStatus] = mapped_column(
        EnumType(ConnectorStatus, name="connectorstatus"),
        nullable=False,
        default=ConnectorStatus.INACTIVE,
    )
    config: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    extra: Mapped[dict] = mapped_column("metadata", JSONType, nullable=False, default=dict)
    last_synced_at: Mapped[datetime | None]

    user: Mapped["User"] = relationship(back_populates="connectors")
    deliveries: Mapped[list["ConnectorDelivery"]] = relationship(back_populates="connector")
    mappings: Mapped[list["ConnectorConversationMapping"]] = relationship(back_populates="connector")


class ConnectorConversationMapping(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "connector_conversation_mappings"
    __table_args__ = (
        UniqueConstraint("connector_id", "conversation_key", name="uq_connector_conversation_mappings_key"),
    )

    connector_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("connectors.id"), nullable=False, index=True
    )
    conversation_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    external_chat_id: Mapped[str | None] = mapped_column(String(255), index=True)
    external_user_id: Mapped[str | None] = mapped_column(String(255), index=True)
    internal_conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("conversations.id"), nullable=True, index=True
    )
    default_persona_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("personas.id"), nullable=True, index=True
    )
    memory_scope: Mapped[str] = mapped_column(String(40), nullable=False, default="chat", server_default="chat")

    connector: Mapped["Connector"] = relationship(back_populates="mappings")
    deliveries: Mapped[list["ConnectorDelivery"]] = relationship(back_populates="mapping")


class ConnectorDelivery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "connector_deliveries"
    __table_args__ = (
        UniqueConstraint("connector_id", "external_message_id", name="uq_connector_deliveries_external_message"),
    )

    connector_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("connectors.id"), nullable=False, index=True
    )
    connector_type: Mapped[str] = mapped_column(String(40), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    conversation_mapping_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("connector_conversation_mappings.id"), nullable=True, index=True
    )
    internal_conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("conversations.id"), nullable=True, index=True
    )
    external_message_id: Mapped[str | None] = mapped_column(String(255))
    inbound_message: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    normalized_input: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    agent_response: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    outbound_response: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    debug_payload: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    delivery_status: Mapped[str] = mapped_column(String(40), nullable=False, default="received")
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="mock", server_default="mock")
    error_message: Mapped[str | None] = mapped_column(Text)

    connector: Mapped[Connector] = relationship(back_populates="deliveries")
    mapping: Mapped["ConnectorConversationMapping | None"] = relationship(back_populates="deliveries")


class ModelProvider(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_providers"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("users.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_type: Mapped[ProviderType] = mapped_column(
        EnumType(ProviderType, name="providertype"),
        nullable=False,
    )
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    api_key_ref: Mapped[str | None] = mapped_column(String(255))
    settings: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )


from app.models.user import User  # noqa: E402
