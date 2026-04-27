from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import FineTuneBackend, FineTuneJobStatus
from app.models.base import Base, EnumType, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, UUIDType


class FineTuneJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fine_tune_jobs"

    user_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    import_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("imports.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    source_speaker: Mapped[str] = mapped_column(String(120), nullable=False)
    backend: Mapped[FineTuneBackend] = mapped_column(
        EnumType(FineTuneBackend, name="finetunebackend"),
        nullable=False,
    )
    status: Mapped[FineTuneJobStatus] = mapped_column(
        EnumType(FineTuneJobStatus, name="finetunejobstatus"),
        nullable=False,
        default=FineTuneJobStatus.PENDING,
        server_default=text("'pending'"),
    )
    base_model: Mapped[str] = mapped_column(String(160), nullable=False)
    context_window: Mapped[int] = mapped_column(Integer, nullable=False, default=6, server_default=text("6"))
    source_message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    train_examples: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    validation_examples: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    test_examples: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    dataset_path: Mapped[str] = mapped_column(String(500), nullable=False)
    config_path: Mapped[str] = mapped_column(String(500), nullable=False)
    output_dir: Mapped[str] = mapped_column(String(500), nullable=False)
    launcher_command: Mapped[str] = mapped_column(Text, nullable=False)
    training_config: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    dataset_stats: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    artifact_path: Mapped[str | None] = mapped_column(String(500))
    error_message: Mapped[str | None] = mapped_column(Text)
    registered_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType,
        ForeignKey("model_providers.id"),
        nullable=True,
        index=True,
    )
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]

    user: Mapped["User"] = relationship(back_populates="fine_tune_jobs")
    import_job: Mapped["ImportJob"] = relationship(back_populates="fine_tune_jobs")
    registered_provider: Mapped["ModelProvider | None"] = relationship()


from app.models.import_job import ImportJob  # noqa: E402
from app.models.runtime import ModelProvider  # noqa: E402
from app.models.user import User  # noqa: E402
