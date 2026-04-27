from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import FineTuneJobStatus, ProviderType
from app.core.config import get_settings
from app.models.fine_tuning import FineTuneJob
from app.models.import_job import ImportJob, NormalizedMessage
from app.models.runtime import ModelProvider
from app.schemas.fine_tuning import (
    FineTuneDatasetPreviewSample,
    FineTuneJobCreate,
    FineTuneJobDetailResponse,
    FineTuneJobRead,
    FineTuneJobUpdate,
)
from app.schemas.runtime import ModelProviderRead

PROJECT_ROOT = Path(__file__).resolve().parents[4]
RUN_JOB_SCRIPT = PROJECT_ROOT / "scripts" / "local_finetune" / "run_job.py"
ARTIFACTS_ROOT = Path(
    os.getenv(
        "FINE_TUNE_ARTIFACTS_DIR",
        (PROJECT_ROOT / ".tmp" / "fine-tuning").as_posix(),
    )
)


def _speaker_stats_for(import_row: ImportJob) -> dict[str, dict[str, Any]]:
    stats = import_row.normalized_summary.get("speaker_stats")
    return stats if isinstance(stats, dict) else {}


def _infer_target_speaker(import_row: ImportJob) -> str | None:
    conversation_owner = import_row.normalized_summary.get("conversation_owner")
    if isinstance(conversation_owner, str) and conversation_owner.strip():
        return conversation_owner.strip()

    stats = _speaker_stats_for(import_row)
    if not stats:
        return None
    ranked = sorted(
        stats.items(),
        key=lambda item: int(item[1].get("message_count", 0)),
        reverse=True,
    )
    return ranked[0][0] if ranked else None


def _map_role(message: NormalizedMessage, *, target_speaker: str) -> str:
    if message.speaker == target_speaker:
        return "assistant"
    if str(message.role.value) == "system":
        return "system"
    return "user"


def _is_text_like(message: NormalizedMessage) -> bool:
    content = (message.content or "").strip()
    if not content:
        return False
    if len(content) < 2:
        return False
    return True


def _build_samples(
    messages: list[NormalizedMessage],
    *,
    target_speaker: str,
    context_window: int,
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []

    for index, message in enumerate(messages):
        if message.speaker != target_speaker or not _is_text_like(message):
            continue

        window_start = max(0, index - context_window)
        context = messages[window_start:index]
        formatted = [
            {
                "role": _map_role(item, target_speaker=target_speaker),
                "content": item.content.strip(),
            }
            for item in context
            if _is_text_like(item)
        ]
        formatted.append({"role": "assistant", "content": message.content.strip()})

        if not any(item["role"] == "user" for item in formatted[:-1]):
            continue
        if formatted[-1]["role"] != "assistant":
            continue

        samples.append({"messages": formatted})

    deduped: list[dict[str, Any]] = []
    seen = set()
    for sample in samples:
        key = json.dumps(sample, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(sample)
    return deduped


def _split_samples(
    samples: list[dict[str, Any]],
    *,
    train_ratio: float,
    validation_ratio: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    total = len(samples)
    if total <= 1:
        return samples, [], []

    train_count = max(1, math.floor(total * train_ratio))
    validation_count = max(0, math.floor(total * validation_ratio))
    if train_count + validation_count >= total:
        validation_count = max(0, min(validation_count, total - train_count - 1))
    test_count = max(0, total - train_count - validation_count)

    train_samples = samples[:train_count]
    validation_samples = samples[train_count : train_count + validation_count]
    test_samples = samples[train_count + validation_count : train_count + validation_count + test_count]

    if not test_samples and len(train_samples) > 1:
        test_samples = [train_samples.pop()]

    return train_samples, validation_samples, test_samples


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _job_dir(job_id: uuid.UUID) -> Path:
    return ARTIFACTS_ROOT / str(job_id)


def _preview_from_samples(samples: list[dict[str, Any]], limit: int = 3) -> list[FineTuneDatasetPreviewSample]:
    return [FineTuneDatasetPreviewSample.model_validate(sample) for sample in samples[:limit]]


def _provider_name_for_job(job: FineTuneJob) -> str:
    return f"{job.name} Adapter"[:120]


def _provider_model_name_for_job(job: FineTuneJob) -> str:
    return job.name[:120]


def _provider_settings_for_job(
    job: FineTuneJob,
    *,
    inference_mode: str,
    artifact_path: str,
) -> dict[str, Any]:
    return {
        "adapter_path": artifact_path,
        "base_model": job.base_model,
        "registered_from_job_id": str(job.id),
        "source_speaker": job.source_speaker,
        "context_window": job.context_window,
        "supports_streaming": False,
        "supports_tool_calling": False,
        "inference_mode": inference_mode,
        "max_new_tokens": 256,
        "temperature": 0.7,
    }


def _registered_provider_read(job: FineTuneJob) -> ModelProviderRead | None:
    if not job.registered_provider:
        return None
    return ModelProviderRead.model_validate(job.registered_provider)


def create_fine_tune_job(db: Session, payload: FineTuneJobCreate) -> FineTuneJobDetailResponse:
    import_row = db.scalar(select(ImportJob).where(ImportJob.id == payload.import_id))
    if not import_row:
        raise ValueError("Import not found")

    target_speaker = payload.source_speaker.strip() or (_infer_target_speaker(import_row) or "")
    if not target_speaker:
        raise ValueError("A target speaker is required for fine-tuning.")

    messages = db.scalars(
        select(NormalizedMessage)
        .where(NormalizedMessage.import_id == import_row.id)
        .order_by(NormalizedMessage.sequence_index)
    ).all()
    samples = _build_samples(messages, target_speaker=target_speaker, context_window=payload.context_window)
    if len(samples) < 2:
        raise ValueError("Not enough usable dialogue samples to build a local fine-tune dataset.")

    train_samples, validation_samples, test_samples = _split_samples(
        samples,
        train_ratio=payload.train_ratio,
        validation_ratio=payload.validation_ratio,
    )

    job = FineTuneJob(
        user_id=payload.user_id,
        import_id=payload.import_id,
        name=payload.name,
        source_speaker=target_speaker,
        backend=payload.backend,
        status=FineTuneJobStatus.PENDING,
        base_model=payload.base_model,
        context_window=payload.context_window,
        source_message_count=len(samples),
        train_examples=len(train_samples),
        validation_examples=len(validation_samples),
        test_examples=len(test_samples),
        dataset_path="",
        config_path="",
        output_dir="",
        launcher_command="",
        training_config={
            "train_ratio": payload.train_ratio,
            "validation_ratio": payload.validation_ratio,
            "base_model": payload.base_model,
            "backend": payload.backend.value,
            "context_window": payload.context_window,
            "max_length": 1024,
            "num_train_epochs": 1,
            "learning_rate": 2e-4,
            "per_device_train_batch_size": 1,
            "per_device_eval_batch_size": 1,
            "gradient_accumulation_steps": 4,
            "warmup_ratio": 0.03,
            "logging_steps": 1,
            "lora_r": 16,
            "lora_alpha": 32,
            "lora_dropout": 0.05,
        },
        dataset_stats={
            "speaker_stats": _speaker_stats_for(import_row),
            "split_summary": {
                "train": len(train_samples),
                "validation": len(validation_samples),
                "test": len(test_samples),
            },
            "preview_samples": samples[:3],
        },
    )
    db.add(job)
    db.flush()

    job_dir = _job_dir(job.id)
    dataset_dir = job_dir / "dataset"
    output_dir = job_dir / "output"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    train_path = dataset_dir / "train.jsonl"
    validation_path = dataset_dir / "validation.jsonl"
    test_path = dataset_dir / "test.jsonl"
    config_path = job_dir / "job_config.json"

    _write_jsonl(train_path, train_samples)
    _write_jsonl(validation_path, validation_samples)
    _write_jsonl(test_path, test_samples)

    config_payload = {
        "job_id": str(job.id),
        "name": job.name,
        "source_speaker": job.source_speaker,
        "backend": job.backend.value,
        "base_model": job.base_model,
        "dataset": {
            "train_path": train_path.as_posix(),
            "validation_path": validation_path.as_posix(),
            "test_path": test_path.as_posix(),
        },
        "output_dir": output_dir.as_posix(),
        "hyperparameters": {
            "context_window": job.context_window,
            "train_examples": job.train_examples,
            "validation_examples": job.validation_examples,
            "test_examples": job.test_examples,
            **dict(job.training_config or {}),
        },
    }
    config_path.write_text(json.dumps(config_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    launcher_command = f"python scripts/local_finetune/run_job.py --job-id \"{job.id}\""
    job.dataset_path = dataset_dir.as_posix()
    job.config_path = config_path.as_posix()
    job.output_dir = output_dir.as_posix()
    job.launcher_command = launcher_command

    db.commit()
    db.refresh(job)
    return FineTuneJobDetailResponse(
        job=FineTuneJobRead.model_validate(job),
        dataset_preview=_preview_from_samples(samples),
        registered_provider=_registered_provider_read(job),
    )


def list_fine_tune_jobs(db: Session) -> list[FineTuneJob]:
    return db.scalars(select(FineTuneJob).order_by(FineTuneJob.created_at.desc())).all()


def get_fine_tune_job_detail(db: Session, job_id: uuid.UUID) -> FineTuneJobDetailResponse | None:
    job = db.scalar(select(FineTuneJob).where(FineTuneJob.id == job_id))
    if not job:
        return None

    preview_samples = job.dataset_stats.get("preview_samples", [])
    return FineTuneJobDetailResponse(
        job=FineTuneJobRead.model_validate(job),
        dataset_preview=[
            FineTuneDatasetPreviewSample.model_validate(sample)
            for sample in preview_samples[:3]
            if isinstance(sample, dict)
        ],
        registered_provider=_registered_provider_read(job),
    )


def update_fine_tune_job(db: Session, job_id: uuid.UUID, payload: FineTuneJobUpdate) -> FineTuneJob | None:
    job = db.scalar(select(FineTuneJob).where(FineTuneJob.id == job_id))
    if not job:
        return None

    updates = payload.model_dump(exclude_unset=True)
    previous_status = job.status
    for key, value in updates.items():
        setattr(job, key, value)

    if payload.status == FineTuneJobStatus.RUNNING and previous_status != FineTuneJobStatus.RUNNING:
        job.started_at = datetime.now(timezone.utc)
    if payload.status in {FineTuneJobStatus.COMPLETED, FineTuneJobStatus.FAILED, FineTuneJobStatus.CANCELLED}:
        job.finished_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(job)
    return job


def register_fine_tune_provider(
    db: Session,
    job_id: uuid.UUID,
    *,
    inference_mode: str | None = None,
) -> ModelProvider | None:
    job = db.scalar(select(FineTuneJob).where(FineTuneJob.id == job_id))
    if not job:
        return None
    if job.status != FineTuneJobStatus.COMPLETED:
        raise ValueError("Only completed fine-tune jobs can be registered as model providers.")
    if not job.artifact_path:
        raise ValueError("Fine-tune job artifact is missing. Run training before registering the provider.")

    provider = None
    if job.registered_provider_id:
        provider = db.scalar(select(ModelProvider).where(ModelProvider.id == job.registered_provider_id))

    if provider is None:
        for candidate in db.scalars(
            select(ModelProvider).where(ModelProvider.provider_type == ProviderType.LOCAL_ADAPTER)
        ).all():
            candidate_job_id = str((candidate.settings or {}).get("registered_from_job_id", "")).strip()
            if candidate_job_id == str(job.id):
                provider = candidate
                break

    result_path = Path(job.output_dir) / "training_result.json"
    result_payload: dict[str, Any] = {}
    if result_path.exists():
        try:
            result_payload = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            result_payload = {}

    resolved_mode = (
        inference_mode
        or str(result_payload.get("mode") or "").strip()
        or str((job.training_config or {}).get("inference_mode") or "").strip()
        or "transformers"
    )
    provider_settings = _provider_settings_for_job(
        job,
        inference_mode=resolved_mode,
        artifact_path=job.artifact_path,
    )

    if provider is None:
        provider = ModelProvider(
            user_id=job.user_id,
            name=_provider_name_for_job(job),
            provider_type=ProviderType.LOCAL_ADAPTER,
            base_url=f"local://adapter/{job.id}",
            model_name=_provider_model_name_for_job(job),
            api_key_ref=None,
            settings=provider_settings,
            is_default=False,
            is_enabled=True,
        )
        db.add(provider)
        db.flush()
    else:
        provider.user_id = job.user_id
        provider.name = _provider_name_for_job(job)
        provider.provider_type = ProviderType.LOCAL_ADAPTER
        provider.base_url = f"local://adapter/{job.id}"
        provider.model_name = _provider_model_name_for_job(job)
        provider.api_key_ref = None
        provider.settings = provider_settings
        provider.is_enabled = True

    job.registered_provider_id = provider.id
    training_config = dict(job.training_config or {})
    training_config["registered_provider"] = {
        "provider_id": str(provider.id),
        "provider_name": provider.name,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    job.training_config = training_config
    db.commit()
    db.refresh(provider)
    db.refresh(job)
    return provider


def launch_fine_tune_job(db: Session, job_id: uuid.UUID, *, wait: bool = False) -> FineTuneJob | None:
    job = db.scalar(select(FineTuneJob).where(FineTuneJob.id == job_id))
    if not job:
        return None
    if not Path(job.config_path).exists():
        raise ValueError("Fine-tune job config is missing. Recreate the job before launching training.")
    if job.status == FineTuneJobStatus.RUNNING:
        return job

    training_config = dict(job.training_config or {})
    training_config["last_launch"] = {
        "mode": "sync" if wait else "background",
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }
    job.training_config = training_config
    job.status = FineTuneJobStatus.RUNNING
    job.error_message = None
    job.artifact_path = None
    job.started_at = datetime.now(timezone.utc)
    job.finished_at = None
    db.commit()
    db.refresh(job)

    command = [
        sys.executable,
        RUN_JOB_SCRIPT.as_posix(),
        "--job-id",
        str(job.id),
        "--database-url",
        get_settings().database_url,
    ]

    try:
        if wait:
            completed = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                row = db.scalar(select(FineTuneJob).where(FineTuneJob.id == job_id))
                if row and row.status == FineTuneJobStatus.RUNNING:
                    row.status = FineTuneJobStatus.FAILED
                    row.error_message = completed.stderr.strip() or completed.stdout.strip() or "Training failed."
                    row.finished_at = datetime.now(timezone.utc)
                    db.commit()
            db.expire_all()
            refreshed = db.scalar(select(FineTuneJob).where(FineTuneJob.id == job_id))
            if refreshed is not None:
                return refreshed
            return job

        process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        row = db.scalar(select(FineTuneJob).where(FineTuneJob.id == job_id))
        if row is not None:
            row.status = FineTuneJobStatus.FAILED
            row.error_message = str(exc)
            row.finished_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(row)
            return row
        raise

    job = db.scalar(select(FineTuneJob).where(FineTuneJob.id == job_id))
    if job is None:
        return None

    training_config = dict(job.training_config or {})
    training_config["last_launch"] = {
        **dict(training_config.get("last_launch") or {}),
        "runner_pid": process.pid,
    }
    job.training_config = training_config
    db.commit()
    db.refresh(job)
    return job
