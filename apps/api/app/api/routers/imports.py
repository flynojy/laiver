from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.import_job import ImportJob, NormalizedMessage
from app.schemas.import_job import ImportCommitRequest, ImportDetailResponse, ImportPreviewResponse
from app.services.import_service import commit_import, preview_import

router = APIRouter()


@router.post("/preview", response_model=ImportPreviewResponse)
async def preview_import_route(file: UploadFile = File(...)) -> ImportPreviewResponse:
    raw_bytes = await file.read()
    preview, _, _ = preview_import(file.filename or "upload.txt", raw_bytes)
    return preview


@router.post("/commit", response_model=ImportDetailResponse)
def commit_import_route(payload: ImportCommitRequest, db: Session = Depends(get_db)) -> ImportDetailResponse:
    return commit_import(db, payload)


@router.get("", response_model=list[ImportDetailResponse])
def list_imports(db: Session = Depends(get_db)) -> list[ImportDetailResponse]:
    rows = db.scalars(select(ImportJob).order_by(ImportJob.created_at.desc())).all()
    return [
        ImportDetailResponse(
            import_job=row,
            normalized_messages=db.scalars(
                select(NormalizedMessage)
                .where(NormalizedMessage.import_id == row.id)
                .order_by(NormalizedMessage.sequence_index)
            ).all(),
        )
        for row in rows
    ]


@router.get("/{import_id}", response_model=ImportDetailResponse)
def get_import(import_id: str, db: Session = Depends(get_db)) -> ImportDetailResponse:
    row = db.scalar(select(ImportJob).where(ImportJob.id == import_id))
    if not row:
        raise HTTPException(status_code=404, detail="Import not found")
    messages = db.scalars(
        select(NormalizedMessage)
        .where(NormalizedMessage.import_id == row.id)
        .order_by(NormalizedMessage.sequence_index)
    ).all()
    return ImportDetailResponse(import_job=row, normalized_messages=messages)

