import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import Persona
from app.schemas.persona import (
    PersonaCreate,
    PersonaExtractionRequest,
    PersonaExtractionResponse,
    PersonaRead,
    PersonaUpdate,
)
from app.services.persona_service import extract_persona

router = APIRouter()


@router.get("", response_model=list[PersonaRead])
def list_personas(db: Session = Depends(get_db)) -> list[Persona]:
    return db.scalars(select(Persona).order_by(Persona.created_at.desc())).all()


@router.post("", response_model=PersonaRead)
def create_persona(payload: PersonaCreate, db: Session = Depends(get_db)) -> Persona:
    if payload.is_default:
        for row in db.scalars(select(Persona).where(Persona.user_id == payload.user_id)).all():
            row.is_default = False
    persona = Persona(**payload.model_dump())
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return persona


@router.post("/extract", response_model=PersonaExtractionResponse)
def extract_persona_route(
    payload: PersonaExtractionRequest,
    db: Session = Depends(get_db),
) -> PersonaExtractionResponse:
    persona, count = extract_persona(db, payload)
    return PersonaExtractionResponse(
        persona=persona,
        source_message_count=count,
        source_speaker=payload.source_speaker,
    )


@router.get("/{persona_id}", response_model=PersonaRead)
def get_persona(persona_id: str, db: Session = Depends(get_db)) -> Persona:
    persona = db.scalar(select(Persona).where(Persona.id == uuid.UUID(persona_id)))
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


@router.put("/{persona_id}", response_model=PersonaRead)
def update_persona(persona_id: str, payload: PersonaUpdate, db: Session = Depends(get_db)) -> Persona:
    persona = db.scalar(select(Persona).where(Persona.id == uuid.UUID(persona_id)))
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(persona, key, value)
    if payload.is_default:
        for row in db.scalars(select(Persona).where(Persona.user_id == persona.user_id)).all():
            if row.id != persona.id:
                row.is_default = False
    db.commit()
    db.refresh(persona)
    return persona
