import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.fine_tuning import FineTuneJob
from app.schemas.fine_tuning import FineTuneJobCreate, FineTuneJobDetailResponse, FineTuneJobRead, FineTuneJobUpdate
from app.schemas.runtime import ModelProviderRead
from app.services.fine_tuning_service import (
    create_fine_tune_job,
    get_fine_tune_job_detail,
    launch_fine_tune_job,
    list_fine_tune_jobs,
    register_fine_tune_provider,
    update_fine_tune_job,
)

router = APIRouter()


@router.get("/jobs", response_model=list[FineTuneJobRead])
def list_jobs(db: Session = Depends(get_db)) -> list[FineTuneJob]:
    return list_fine_tune_jobs(db)


@router.post("/jobs", response_model=FineTuneJobDetailResponse)
def create_job(payload: FineTuneJobCreate, db: Session = Depends(get_db)) -> FineTuneJobDetailResponse:
    try:
        return create_fine_tune_job(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/jobs/{job_id}", response_model=FineTuneJobDetailResponse)
def get_job(job_id: str, db: Session = Depends(get_db)) -> FineTuneJobDetailResponse:
    detail = get_fine_tune_job_detail(db, uuid.UUID(job_id))
    if not detail:
        raise HTTPException(status_code=404, detail="Fine-tune job not found")
    return detail


@router.post("/jobs/{job_id}/launch", response_model=FineTuneJobRead)
def launch_job(job_id: str, wait: bool = False, db: Session = Depends(get_db)) -> FineTuneJob:
    try:
        row = launch_fine_tune_job(db, uuid.UUID(job_id), wait=wait)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail="Fine-tune job not found")
    return row


@router.post("/jobs/{job_id}/register-provider", response_model=ModelProviderRead)
def register_job_provider(job_id: str, db: Session = Depends(get_db)) -> ModelProviderRead:
    try:
        provider = register_fine_tune_provider(db, uuid.UUID(job_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not provider:
        raise HTTPException(status_code=404, detail="Fine-tune job not found")
    return ModelProviderRead.model_validate(provider)


@router.patch("/jobs/{job_id}", response_model=FineTuneJobRead)
def update_job(job_id: str, payload: FineTuneJobUpdate, db: Session = Depends(get_db)) -> FineTuneJob:
    row = update_fine_tune_job(db, uuid.UUID(job_id), payload)
    if not row:
        raise HTTPException(status_code=404, detail="Fine-tune job not found")
    return row
