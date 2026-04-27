import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.conversation import Conversation, Message
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationRead,
    ConversationUpdate,
    MessageRead,
)

router = APIRouter()


@router.get("", response_model=list[ConversationRead])
def list_conversations(db: Session = Depends(get_db)) -> list[Conversation]:
    return db.scalars(select(Conversation).order_by(Conversation.updated_at.desc())).all()


@router.post("", response_model=ConversationRead)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db)) -> Conversation:
    row = Conversation(
        user_id=payload.user_id,
        persona_id=payload.persona_id,
        title=payload.title,
        summary=payload.summary,
        channel=payload.channel,
        context=payload.metadata,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(conversation_id: str, db: Session = Depends(get_db)) -> ConversationDetailResponse:
    row = db.scalar(select(Conversation).where(Conversation.id == uuid.UUID(conversation_id)))
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = db.scalars(
        select(Message).where(Message.conversation_id == row.id).order_by(Message.sequence_index)
    ).all()
    return ConversationDetailResponse(conversation=row, messages=messages)


@router.patch("/{conversation_id}", response_model=ConversationRead)
def update_conversation(conversation_id: str, payload: ConversationUpdate, db: Session = Depends(get_db)) -> Conversation:
    row = db.scalar(select(Conversation).where(Conversation.id == uuid.UUID(conversation_id)))
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if payload.persona_id is not None:
        row.persona_id = payload.persona_id
    if payload.metadata is not None:
        row.context = {
            **(row.context or {}),
            **payload.metadata,
        }
    db.commit()
    db.refresh(row)
    return row


@router.get("/{conversation_id}/messages", response_model=list[MessageRead])
def get_conversation_messages(conversation_id: str, db: Session = Depends(get_db)) -> list[Message]:
    return db.scalars(
        select(Message).where(Message.conversation_id == uuid.UUID(conversation_id)).order_by(Message.sequence_index)
    ).all()
