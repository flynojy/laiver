from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import FineTuneBackend, FineTuneJobStatus
from app.schemas.runtime import ModelProviderRead


class FineTuneDatasetSplitSummary(BaseModel):
    train: int = 0
    validation: int = 0
    test: int = 0


class FineTuneDatasetPreviewSample(BaseModel):
    messages: list[dict[str, str]] = Field(default_factory=list)


class FineTuneJobCreate(BaseModel):
    user_id: uuid.UUID
    import_id: uuid.UUID
    name: str
    source_speaker: str
    backend: FineTuneBackend = FineTuneBackend.LOCAL_QLORA
    base_model: str = "Qwen/Qwen2.5-7B-Instruct"
    context_window: int = Field(default=6, ge=1, le=12)
    train_ratio: float = Field(default=0.8, gt=0.5, lt=0.98)
    validation_ratio: float = Field(default=0.1, gt=0.0, lt=0.3)


class FineTuneJobUpdate(BaseModel):
    status: FineTuneJobStatus | None = None
    artifact_path: str | None = None
    error_message: str | None = None


class FineTuneJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    import_id: uuid.UUID
    name: str
    source_speaker: str
    backend: FineTuneBackend
    status: FineTuneJobStatus
    base_model: str
    context_window: int
    source_message_count: int
    train_examples: int
    validation_examples: int
    test_examples: int
    dataset_path: str
    config_path: str
    output_dir: str
    launcher_command: str
    training_config: dict[str, Any] = Field(default_factory=dict)
    dataset_stats: dict[str, Any] = Field(default_factory=dict)
    artifact_path: str | None = None
    error_message: str | None = None
    registered_provider_id: uuid.UUID | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class FineTuneJobDetailResponse(BaseModel):
    job: FineTuneJobRead
    dataset_preview: list[FineTuneDatasetPreviewSample] = Field(default_factory=list)
    registered_provider: ModelProviderRead | None = None
