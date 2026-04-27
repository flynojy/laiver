from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _bootstrap_imports() -> None:
    workspace_root = Path(__file__).resolve().parents[2]
    api_root = workspace_root / "apps" / "api"
    if str(api_root) not in sys.path:
        sys.path.insert(0, str(api_root))


def _write_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a Laiver fine-tune job and persist status updates.")
    parser.add_argument("--job-id", required=True, help="Fine-tune job identifier.")
    parser.add_argument("--database-url", help="Optional database URL override for the worker process.")
    args = parser.parse_args()

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    _bootstrap_imports()

    from sqlalchemy import select

    from app.core.enums import FineTuneJobStatus
    from app.db.session import SessionLocal
    from app.models.fine_tuning import FineTuneJob
    from app.services.fine_tuning_service import register_fine_tune_provider
    from app.services.local_fine_tune_runner import run_training_job

    job_id = uuid.UUID(args.job_id)
    with SessionLocal() as db:
        job = db.scalar(select(FineTuneJob).where(FineTuneJob.id == job_id))
        if not job:
            raise SystemExit(f"Fine-tune job not found: {job_id}")

        output_dir = Path(job.output_dir)
        training_config = dict(job.training_config or {})
        training_config["runner"] = {
            "pid": os.getpid(),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "entrypoint": "scripts/local_finetune/run_job.py",
        }
        job.training_config = training_config
        job.status = FineTuneJobStatus.RUNNING
        job.error_message = None
        job.artifact_path = None
        if job.started_at is None:
            job.started_at = datetime.now(timezone.utc)
        job.finished_at = None
        db.commit()

        try:
            result = run_training_job(Path(job.config_path))
        except Exception as exc:
            error_text = str(exc).strip() or exc.__class__.__name__
            _write_report(
                output_dir / "run_failure.json",
                {
                    "job_id": str(job.id),
                    "status": "failed",
                    "error": error_text,
                    "traceback": traceback.format_exc(),
                },
            )

            job = db.scalar(select(FineTuneJob).where(FineTuneJob.id == job_id))
            if job is not None:
                training_config = dict(job.training_config or {})
                training_config["runner"] = {
                    **dict(training_config.get("runner") or {}),
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "status": "failed",
                }
                job.training_config = training_config
                job.status = FineTuneJobStatus.FAILED
                job.error_message = error_text
                job.finished_at = datetime.now(timezone.utc)
                db.commit()
            return 1

        _write_report(
            output_dir / "run_success.json",
            {
                "job_id": str(job.id),
                "status": "completed",
                "result": result,
            },
        )

        job = db.scalar(select(FineTuneJob).where(FineTuneJob.id == job_id))
        if job is not None:
            training_config = dict(job.training_config or {})
            training_config["runner"] = {
                **dict(training_config.get("runner") or {}),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "status": "completed",
            }
            job.training_config = training_config
            job.status = FineTuneJobStatus.COMPLETED
            job.artifact_path = str(result.get("artifact_path") or "")
            job.error_message = None
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
            register_fine_tune_provider(
                db,
                job_id,
                inference_mode=str(result.get("mode") or "").strip() or None,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
