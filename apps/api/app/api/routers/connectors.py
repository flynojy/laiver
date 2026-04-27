import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.runtime import Connector
from app.schemas.runtime import (
    ConnectorCreate,
    ConnectorConversationMappingRead,
    ConnectorDeliveryRead,
    ConnectorRead,
    ConnectorTestRequest,
    ConnectorTestResponse,
    ConnectorUpdate,
)
from app.services.connector_service import (
    build_test_payload,
    feishu_connector_skeleton,
    list_connector_deliveries,
    list_connector_mappings,
    process_feishu_message,
    to_test_response,
    validate_feishu_webhook_request,
)

router = APIRouter()


@router.get("", response_model=list[ConnectorRead])
def list_connectors(db: Session = Depends(get_db)) -> list[Connector]:
    return db.scalars(select(Connector).order_by(Connector.created_at.desc())).all()


@router.get("/{connector_id}/deliveries", response_model=list[ConnectorDeliveryRead])
def get_connector_deliveries(connector_id: str, db: Session = Depends(get_db)) -> list[ConnectorDeliveryRead]:
    return list_connector_deliveries(db, connector_id)


@router.get("/{connector_id}/mappings", response_model=list[ConnectorConversationMappingRead])
def get_connector_mappings(connector_id: str, db: Session = Depends(get_db)) -> list[ConnectorConversationMappingRead]:
    rows = list_connector_mappings(db, connector_id)
    return [ConnectorConversationMappingRead.model_validate(row) for row in rows]


@router.post("", response_model=ConnectorRead)
def create_connector(payload: ConnectorCreate, db: Session = Depends(get_db)) -> Connector:
    row = Connector(
        user_id=payload.user_id,
        platform=payload.connector_type,
        name=payload.name,
        status=payload.status,
        config=payload.config,
        extra=payload.metadata,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{connector_id}", response_model=ConnectorRead)
def update_connector(connector_id: str, payload: ConnectorUpdate, db: Session = Depends(get_db)) -> Connector:
    row = db.scalar(select(Connector).where(Connector.id == uuid.UUID(connector_id)))
    if not row:
        raise HTTPException(status_code=404, detail="Connector not found")

    if payload.name is not None:
        row.name = payload.name
    if payload.status is not None:
        row.status = payload.status
    if payload.config is not None:
        row.config = payload.config
    if payload.metadata is not None:
        row.extra = payload.metadata

    db.commit()
    db.refresh(row)
    return row


@router.post("/{connector_id}/test", response_model=ConnectorTestResponse)
async def test_connector(connector_id: str, payload: ConnectorTestRequest, db: Session = Depends(get_db)) -> ConnectorTestResponse:
    row = db.scalar(select(Connector).where(Connector.id == uuid.UUID(connector_id)))
    if not row:
        raise HTTPException(status_code=404, detail="Connector not found")

    if payload.mode:
        row.config = {**(row.config or {}), "mode": payload.mode}
        db.commit()
        db.refresh(row)

    result = await process_feishu_message(
        db,
        connector=row,
        payload=build_test_payload(
            payload.message_text,
            payload.sender_name,
            payload.external_user_id,
            payload.external_chat_id,
            str((row.config or {}).get("verification_token", "")).strip() or None,
        ),
        test_mode=True,
    )
    return to_test_response(result)


@router.post("/feishu/webhook/{connector_id}")
async def feishu_webhook(connector_id: str, payload: dict, db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(Connector).where(Connector.id == uuid.UUID(connector_id)))
    if not row:
        raise HTTPException(status_code=404, detail="Connector not found")

    validation_error = validate_feishu_webhook_request(row, payload)
    if validation_error:
        raise HTTPException(status_code=403, detail=validation_error)

    if "challenge" in payload:
        return {"challenge": payload["challenge"]}

    result = await process_feishu_message(db, connector=row, payload=payload, test_mode=False)
    return {
        "delivery_status": result.delivery.delivery_status,
        "connector_trace_id": result.delivery.trace_id,
        "mapped_conversation_id": str(result.mapping.internal_conversation_id) if result.mapping and result.mapping.internal_conversation_id else None,
        "error": result.delivery.error_message,
    }


@router.get("/skeleton/feishu")
def get_feishu_connector_skeleton() -> dict:
    return feishu_connector_skeleton()
