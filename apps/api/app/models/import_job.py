from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ImportSourceType, ImportStatus, MessageRole
from app.models.base import Base, EnumType, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, UUIDType


class ImportJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "imports"

    user_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[ImportSourceType] = mapped_column(
        EnumType(ImportSourceType, name="importsourcetype"),
        nullable=False,
    )
    status: Mapped[ImportStatus] = mapped_column(
        EnumType(ImportStatus, name="importstatus"),
        nullable=False,
        default=ImportStatus.PREVIEWED,
    )
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    raw_text: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict | list | None] = mapped_column(JSONType)
    preview_payload: Mapped[dict] = mapped_column("preview", JSONType, nullable=False, default=dict)
    normalized_summary: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)

    user: Mapped["User"] = relationship(back_populates="imports")
    normalized_messages: Mapped[list["NormalizedMessage"]] = relationship(
        back_populates="import_job",
        cascade="all, delete-orphan",
        order_by="NormalizedMessage.sequence_index",
    )
    personas: Mapped[list["Persona"]] = relationship(back_populates="source_import")
    fine_tune_jobs: Mapped[list["FineTuneJob"]] = relationship(back_populates="import_job")


class NormalizedMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "normalized_messages"
    __table_args__ = (UniqueConstraint("import_id", "sequence_index", name="uq_normalized_messages_import_sequence"),)

    import_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("imports.id"), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(255))
    speaker: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[MessageRole] = mapped_column(
        EnumType(MessageRole, name="messagerole"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime | None]
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False)
    details: Mapped[dict] = mapped_column("metadata", JSONType, nullable=False, default=dict)

    import_job: Mapped["ImportJob"] = relationship(back_populates="normalized_messages")


from app.models.fine_tuning import FineTuneJob  # noqa: E402
from app.models.user import Persona, User  # noqa: E402
