from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.memory_candidate import MemoryCandidate
from app.models.memory import Memory
from app.schemas.memory_candidate import MemoryCandidateRead, MemoryCandidateUpdate
from app.schemas.memory import (
    MemoryCreate,
    MemoryDebugResponse,
    MemoryMaintenanceReport,
    MemoryRead,
    MemorySearchRequest,
    MemoryUpdate,
)
from app.services.memory_service import (
    debug_memory_state,
    list_memory_candidates,
    run_memory_maintenance,
    search_memories,
    update_memory,
    update_memory_candidate,
    write_memory,
)

router = APIRouter()


@router.get("", response_model=list[MemoryRead])
def list_memories(db: Session = Depends(get_db)) -> list[Memory]:
    return db.scalars(select(Memory).order_by(Memory.created_at.desc()).limit(100)).all()


@router.post("", response_model=MemoryRead)
def create_memory(payload: MemoryCreate, db: Session = Depends(get_db)) -> Memory:
    return write_memory(db, payload)


@router.patch("/{memory_id}", response_model=MemoryRead)
def update_memory_route(memory_id: str, payload: MemoryUpdate, db: Session = Depends(get_db)) -> Memory:
    try:
        return update_memory(db, memory_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/search", response_model=list[MemoryRead])
def search_memories_route(payload: MemorySearchRequest, db: Session = Depends(get_db)) -> list[Memory]:
    return search_memories(
        db,
        user_id=str(payload.user_id),
        query=payload.query,
        persona_id=str(payload.persona_id) if payload.persona_id else None,
        memory_types=payload.memory_types,
        limit=payload.limit,
    )


@router.get("/debug", response_model=MemoryDebugResponse)
def debug_memories(db: Session = Depends(get_db)) -> MemoryDebugResponse:
    return debug_memory_state(db)


@router.post("/maintenance/run", response_model=MemoryMaintenanceReport)
def run_memory_maintenance_route(
    dry_run: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> dict:
    return run_memory_maintenance(db, dry_run=dry_run)


@router.get("/candidates", response_model=list[MemoryCandidateRead])
def list_memory_candidates_route(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[MemoryCandidate]:
    return list_memory_candidates(db, status=status, limit=limit)


@router.patch("/candidates/{candidate_id}", response_model=MemoryCandidateRead)
def update_memory_candidate_route(
    candidate_id: str,
    payload: MemoryCandidateUpdate,
    db: Session = Depends(get_db),
) -> MemoryCandidate:
    try:
        return update_memory_candidate(
            db,
            candidate_id,
            proposed_action=payload.proposed_action,
            salience_score=payload.salience_score,
            confidence_score=payload.confidence_score,
            sensitivity=payload.sensitivity,
            reason_codes=payload.reason_codes,
            auto_commit=payload.auto_commit,
            status=payload.status,
            reviewer_type=payload.reviewer_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
