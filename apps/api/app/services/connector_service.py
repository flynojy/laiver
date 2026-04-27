from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import ConnectorPlatform, ConnectorStatus
from app.models.runtime import Connector, ConnectorConversationMapping, ConnectorDelivery
from app.models.user import Persona
from app.schemas.agent import AgentChatRequest
from app.schemas.runtime import (
    ConnectorConversationMappingRead,
    ConnectorDeliveryRead,
    ConnectorNormalizedMessage,
    ConnectorRead,
    ConnectorTestResponse,
    ConnectorTraceRead,
)
from app.services.agent_orchestrator import respond as respond_agent


FEISHU_OPENAPI_BASE_URL = "https://open.feishu.cn"
FEISHU_RECEIVE_ID_TYPES = {"chat_id", "open_id", "user_id", "union_id"}


@dataclass
class ConnectorProcessResult:
    connector: Connector
    mapping: ConnectorConversationMapping | None
    normalized_input: ConnectorNormalizedMessage
    trace: ConnectorTraceRead | None
    agent_response: dict[str, Any]
    outbound_response: dict[str, Any]
    delivery: ConnectorDelivery


def feishu_connector_skeleton() -> dict[str, Any]:
    return {
        "connector_type": ConnectorPlatform.FEISHU.value,
        "display_name": "Feishu Connector",
        "capabilities": [
            "webhook_receive",
            "message_normalization",
            "conversation_mapping",
            "agent_reply",
            "openapi_delivery",
            "idempotent_replay_guard",
        ],
        "required_config": {
            "inbound": ["verification_token"],
            "delivery_modes": {
                "webhook": ["reply_webhook_url"],
                "openapi": ["app_id", "app_secret", "receive_id_type"],
            },
        },
        "default_config": {
            "mode": "mock",
            "delivery_mode": "webhook",
            "verification_token": "",
            "reply_webhook_url": "",
            "app_id": "",
            "app_secret": "",
            "receive_id_type": "chat_id",
            "openapi_base_url": FEISHU_OPENAPI_BASE_URL,
            "force_delivery_failure": False,
        },
        "status": "ready_for_local_test_and_live_delivery",
    }


def list_connector_deliveries(db: Session, connector_id: str, limit: int = 20) -> list[ConnectorDeliveryRead]:
    rows = db.scalars(
        select(ConnectorDelivery)
        .where(ConnectorDelivery.connector_id == uuid.UUID(connector_id))
        .order_by(ConnectorDelivery.created_at.desc())
        .limit(limit)
    ).all()
    return [_build_delivery_read(row) for row in rows]


def list_connector_mappings(db: Session, connector_id: str, limit: int = 20) -> list[ConnectorConversationMapping]:
    return db.scalars(
        select(ConnectorConversationMapping)
        .where(ConnectorConversationMapping.connector_id == uuid.UUID(connector_id))
        .order_by(ConnectorConversationMapping.updated_at.desc())
        .limit(limit)
    ).all()


def _parse_feishu_text(raw_content: Any) -> str:
    if isinstance(raw_content, dict):
        return str(raw_content.get("text", "")).strip()
    if not isinstance(raw_content, str):
        return ""
    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError:
        return raw_content.strip()
    if isinstance(parsed, dict):
        return str(parsed.get("text", "")).strip()
    return raw_content.strip()


def extract_feishu_verification_token(payload: dict[str, Any]) -> str:
    candidates = [
        payload.get("token"),
        (payload.get("header") or {}).get("token") if isinstance(payload.get("header"), dict) else None,
    ]
    event = payload.get("event")
    if isinstance(event, dict):
        candidates.extend(
            [
                event.get("token"),
                (event.get("header") or {}).get("token") if isinstance(event.get("header"), dict) else None,
            ]
        )

    for candidate in candidates:
        value = str(candidate or "").strip()
        if value:
            return value
    return ""


def validate_feishu_webhook_request(connector: Connector, payload: dict[str, Any]) -> str | None:
    expected_token = str((connector.config or {}).get("verification_token", "")).strip()
    if not expected_token:
        return None

    actual_token = extract_feishu_verification_token(payload)
    if actual_token and actual_token == expected_token:
        return None
    return "Feishu verification token mismatch."


def normalize_feishu_message(connector: Connector, payload: dict[str, Any]) -> ConnectorNormalizedMessage:
    event = payload.get("event", {})
    message = event.get("message", payload.get("message", {}))
    sender = event.get("sender", payload.get("sender", {}))
    sender_sender = sender.get("sender_id", {}) if isinstance(sender, dict) else {}
    sender_name = sender.get("sender_name") if isinstance(sender, dict) else None

    text = _parse_feishu_text(message.get("content") if isinstance(message, dict) else None)
    if not text:
        text = str(payload.get("text", "")).strip()
    if not text:
        raise ValueError("No text content found in Feishu payload.")

    return ConnectorNormalizedMessage(
        connector_id=connector.id,
        connector_type=connector.platform.value,
        external_message_id=str(message.get("message_id", "")) or None,
        external_user_id=str(sender_sender.get("open_id", "")) or None,
        external_chat_id=str(message.get("chat_id", "")) or None,
        sender_name=sender_name,
        text=text,
        occurred_at=message.get("create_time") if isinstance(message, dict) else None,
        raw_payload=payload,
    )


def build_feishu_webhook_payload(text: str) -> dict[str, Any]:
    return {
        "msg_type": "text",
        "content": {"text": text},
    }


def _resolve_receive_id(normalized: ConnectorNormalizedMessage, receive_id_type: str) -> str | None:
    if receive_id_type == "chat_id":
        return normalized.external_chat_id
    if receive_id_type in {"open_id", "user_id", "union_id"}:
        return normalized.external_user_id
    return None


def build_feishu_openapi_payload(
    normalized: ConnectorNormalizedMessage,
    *,
    text: str,
    receive_id_type: str,
) -> dict[str, Any]:
    receive_id = _resolve_receive_id(normalized, receive_id_type)
    return {
        "receive_id_type": receive_id_type,
        "receive_id": receive_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}, ensure_ascii=False),
    }


def _build_conversation_key(normalized: ConnectorNormalizedMessage) -> str:
    if normalized.external_chat_id:
        return f"chat:{normalized.external_chat_id}"
    if normalized.external_user_id:
        return f"user:{normalized.external_user_id}"
    sender_key = (normalized.sender_name or "anonymous").strip().lower().replace(" ", "-")
    return f"sender:{sender_key}"


def _resolve_default_persona(db: Session, connector: Connector) -> Persona | None:
    return db.scalar(
        select(Persona)
        .where(Persona.user_id == connector.user_id, Persona.is_default.is_(True))
        .order_by(Persona.updated_at.desc())
    )


def _resolve_connector_mapping(
    db: Session,
    *,
    connector: Connector,
    normalized: ConnectorNormalizedMessage,
) -> tuple[ConnectorConversationMapping, bool]:
    conversation_key = _build_conversation_key(normalized)
    existing = db.scalar(
        select(ConnectorConversationMapping).where(
            ConnectorConversationMapping.connector_id == connector.id,
            ConnectorConversationMapping.conversation_key == conversation_key,
        )
    )
    if existing:
        return existing, False

    default_persona = _resolve_default_persona(db, connector)
    mapping = ConnectorConversationMapping(
        connector_id=connector.id,
        conversation_key=conversation_key,
        external_chat_id=normalized.external_chat_id,
        external_user_id=normalized.external_user_id,
        internal_conversation_id=None,
        default_persona_id=default_persona.id if default_persona else None,
        memory_scope="chat",
    )
    db.add(mapping)
    db.flush()
    return mapping, True


def _summarize_text(value: str, limit: int = 180) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _build_connector_trace(
    *,
    trace_id: str,
    normalized: ConnectorNormalizedMessage,
    mapping: ConnectorConversationMapping | None,
    agent_payload: dict[str, Any],
    outbound_payload: dict[str, Any],
    delivery_status: str,
) -> ConnectorTraceRead:
    debug = agent_payload.get("debug", {}) if agent_payload else {}
    response_text = str(agent_payload.get("response", "")).strip()
    outbound_text = ""
    content = outbound_payload.get("content")
    if isinstance(content, dict):
        outbound_text = str(content.get("text", "")).strip()
    elif isinstance(content, str):
        outbound_text = _parse_feishu_text(content)

    inbound_summary = {
        "external_message_id": normalized.external_message_id,
        "external_chat_id": normalized.external_chat_id,
        "external_user_id": normalized.external_user_id,
        "sender_name": normalized.sender_name,
        "text_preview": _summarize_text(normalized.text),
        "occurred_at": normalized.occurred_at,
        "conversation_key": mapping.conversation_key if mapping else _build_conversation_key(normalized),
    }
    outbound_summary = {
        "response_preview": _summarize_text(response_text) if response_text else "",
        "outbound_text_preview": _summarize_text(outbound_text) if outbound_text else "",
        "provider_name": debug.get("provider_name"),
        "model_name": debug.get("model_name"),
        "model_mode": debug.get("model_mode"),
        "memory_write_count": debug.get("memory_write_count", 0),
        "skill_invocation_count": len(debug.get("skill_invocations", [])),
    }

    return ConnectorTraceRead(
        connector_trace_id=trace_id,
        inbound_summary=inbound_summary,
        normalized_input=normalized,
        mapped_conversation_id=mapping.internal_conversation_id if mapping else None,
        persona_id=debug.get("persona_id"),
        persona_name=debug.get("persona_name"),
        skills_used=list(debug.get("skills_used", [])),
        fallback_status=str(debug.get("fallback_status", "not_used")),
        outbound_summary=outbound_summary,
        delivery_status=delivery_status,
    )


def _find_existing_delivery(
    db: Session,
    *,
    connector_id: uuid.UUID,
    external_message_id: str | None,
) -> ConnectorDelivery | None:
    if not external_message_id:
        return None
    return db.scalar(
        select(ConnectorDelivery).where(
            ConnectorDelivery.connector_id == connector_id,
            ConnectorDelivery.external_message_id == external_message_id,
        )
    )


def _to_process_result(connector: Connector, delivery: ConnectorDelivery) -> ConnectorProcessResult:
    normalized = ConnectorNormalizedMessage.model_validate(delivery.normalized_input or {})
    trace = ConnectorTraceRead.model_validate(delivery.debug_payload) if delivery.debug_payload else None
    return ConnectorProcessResult(
        connector=connector,
        mapping=delivery.mapping,
        normalized_input=normalized,
        trace=trace,
        agent_response=delivery.agent_response or {},
        outbound_response=delivery.outbound_response or {},
        delivery=delivery,
    )


async def _request_feishu_tenant_access_token(
    *,
    base_url: str,
    app_id: str,
    app_secret: str,
) -> str:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"{base_url}/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": app_id, "app_secret": app_secret},
        )
        response.raise_for_status()
        data = response.json()

    if data.get("code") not in (None, 0):
        raise ValueError(data.get("msg") or "Failed to fetch Feishu tenant access token.")

    token = str(data.get("tenant_access_token", "")).strip()
    if not token:
        raise ValueError("Feishu tenant access token response did not contain a token.")
    return token


async def deliver_feishu_reply(
    connector: Connector,
    *,
    normalized: ConnectorNormalizedMessage,
    text: str,
) -> tuple[str, str | None, str, dict[str, Any]]:
    config = connector.config or {}
    mode = str(config.get("mode", "mock")).lower()
    delivery_mode = str(config.get("delivery_mode", "webhook")).lower()

    if config.get("force_delivery_failure"):
        outbound_payload = build_feishu_webhook_payload(text)
        return "failed", "Forced connector delivery failure for local testing.", mode, outbound_payload

    if mode == "live" and delivery_mode == "openapi":
        receive_id_type = str(config.get("receive_id_type", "chat_id")).strip() or "chat_id"
        outbound_payload = build_feishu_openapi_payload(
            normalized,
            text=text,
            receive_id_type=receive_id_type,
        )
        if receive_id_type not in FEISHU_RECEIVE_ID_TYPES:
            return "failed", f"Unsupported Feishu receive_id_type: {receive_id_type}", "live", outbound_payload

        receive_id = outbound_payload.get("receive_id")
        if not receive_id:
            return "failed", f"Unable to resolve Feishu receive_id for {receive_id_type}.", "live", outbound_payload

        app_id = str(config.get("app_id", "")).strip()
        app_secret = str(config.get("app_secret", "")).strip()
        base_url = str(config.get("openapi_base_url", FEISHU_OPENAPI_BASE_URL)).rstrip("/")
        if not app_id or not app_secret:
            return (
                "failed",
                "Feishu app_id/app_secret are required for live OpenAPI delivery.",
                "live",
                outbound_payload,
            )

        try:
            tenant_access_token = await _request_feishu_tenant_access_token(
                base_url=base_url,
                app_id=app_id,
                app_secret=app_secret,
            )
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{base_url}/open-apis/im/v1/messages",
                    params={"receive_id_type": receive_id_type},
                    headers={
                        "Authorization": f"Bearer {tenant_access_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "receive_id": receive_id,
                        "msg_type": "text",
                        "content": outbound_payload["content"],
                    },
                )
                response.raise_for_status()
                data = response.json()
            if data.get("code") not in (None, 0):
                return "failed", str(data.get("msg") or "Feishu message delivery failed."), "live", outbound_payload
            return "delivered", None, "live", outbound_payload
        except Exception as exc:
            return "failed", str(exc), "live", outbound_payload

    outbound_payload = build_feishu_webhook_payload(text)
    webhook_url = str(config.get("reply_webhook_url", "")).strip()
    if mode == "live" and webhook_url.startswith("mock://success"):
        return "delivered", None, "live", outbound_payload
    if mode == "live" and webhook_url.startswith("mock://failure"):
        return "failed", "Simulated live delivery failure.", "live", outbound_payload
    if mode != "live" or not webhook_url:
        return "mock_delivered", None, "mock", outbound_payload

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(webhook_url, json=outbound_payload)
            response.raise_for_status()
        return "delivered", None, "live", outbound_payload
    except Exception as exc:
        return "failed", str(exc), "live", outbound_payload


def _build_delivery_read(delivery: ConnectorDelivery) -> ConnectorDeliveryRead:
    normalized = ConnectorNormalizedMessage.model_validate(delivery.normalized_input or {})
    mapping = (
        ConnectorConversationMappingRead.model_validate(delivery.mapping)
        if delivery.mapping is not None
        else None
    )
    trace = ConnectorTraceRead.model_validate(delivery.debug_payload) if delivery.debug_payload else None
    return ConnectorDeliveryRead(
        delivery_id=delivery.id,
        connector_id=delivery.connector_id,
        connector_type=delivery.connector_type,
        trace_id=delivery.trace_id,
        internal_conversation_id=delivery.internal_conversation_id,
        external_message_id=delivery.external_message_id,
        inbound_message=delivery.inbound_message or {},
        normalized_input=normalized,
        agent_response=delivery.agent_response or {},
        outbound_response=delivery.outbound_response or {},
        mapping=mapping,
        trace=trace,
        delivery_status=delivery.delivery_status,
        mode=delivery.mode,
        error=delivery.error_message,
        created_at=delivery.created_at,
        updated_at=delivery.updated_at,
    )


async def process_feishu_message(
    db: Session,
    *,
    connector: Connector,
    payload: dict[str, Any],
    test_mode: bool = False,
) -> ConnectorProcessResult:
    normalized = normalize_feishu_message(connector, payload)
    existing_delivery = _find_existing_delivery(
        db,
        connector_id=connector.id,
        external_message_id=normalized.external_message_id,
    )
    if existing_delivery is not None:
        return _to_process_result(connector, existing_delivery)

    trace_id = str(uuid.uuid4())
    mapping, _ = _resolve_connector_mapping(db, connector=connector, normalized=normalized)

    delivery = ConnectorDelivery(
        connector_id=connector.id,
        connector_type=connector.platform.value,
        trace_id=trace_id,
        conversation_mapping_id=mapping.id,
        internal_conversation_id=mapping.internal_conversation_id,
        external_message_id=normalized.external_message_id,
        inbound_message=payload,
        normalized_input=normalized.model_dump(mode="json"),
        agent_response={},
        outbound_response={},
        debug_payload={},
        delivery_status="received",
        mode=str(connector.config.get("mode", "mock")) if connector.config else "mock",
    )
    db.add(delivery)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing_delivery = _find_existing_delivery(
            db,
            connector_id=connector.id,
            external_message_id=normalized.external_message_id,
        )
        if existing_delivery is not None:
            return _to_process_result(connector, existing_delivery)
        raise

    if connector.status != ConnectorStatus.ACTIVE and not test_mode:
        delivery.delivery_status = "inactive"
        delivery.error_message = "Connector is inactive."
        trace = _build_connector_trace(
            trace_id=trace_id,
            normalized=normalized,
            mapping=mapping,
            agent_payload={},
            outbound_payload={},
            delivery_status=delivery.delivery_status,
        )
        delivery.debug_payload = trace.model_dump(mode="json")
        connector.last_synced_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(delivery)
        return ConnectorProcessResult(
            connector=connector,
            mapping=mapping,
            normalized_input=normalized,
            trace=trace,
            agent_response={},
            outbound_response={},
            delivery=delivery,
        )

    agent_response = await respond_agent(
        db,
        AgentChatRequest(
            user_id=connector.user_id,
            conversation_id=mapping.internal_conversation_id,
            persona_id=mapping.default_persona_id,
            message=normalized.text,
        ),
    )
    agent_payload = agent_response.model_dump(mode="json")

    mapping.internal_conversation_id = agent_response.conversation_id
    if mapping.default_persona_id is None and agent_response.persona and agent_response.persona.id:
        mapping.default_persona_id = agent_response.persona.id

    delivery.internal_conversation_id = agent_response.conversation_id
    delivery.agent_response = agent_payload

    delivery_status, error_message, mode, outbound_payload = await deliver_feishu_reply(
        connector,
        normalized=normalized,
        text=agent_response.response,
    )
    delivery.outbound_response = outbound_payload
    delivery.delivery_status = delivery_status
    delivery.error_message = error_message
    delivery.mode = mode

    trace = _build_connector_trace(
        trace_id=trace_id,
        normalized=normalized,
        mapping=mapping,
        agent_payload=agent_payload,
        outbound_payload=outbound_payload,
        delivery_status=delivery_status,
    )
    delivery.debug_payload = trace.model_dump(mode="json")
    connector.last_synced_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(mapping)
    db.refresh(delivery)

    return ConnectorProcessResult(
        connector=connector,
        mapping=mapping,
        normalized_input=normalized,
        trace=trace,
        agent_response=agent_payload,
        outbound_response=outbound_payload,
        delivery=delivery,
    )


def to_test_response(result: ConnectorProcessResult) -> ConnectorTestResponse:
    return ConnectorTestResponse(
        connector=ConnectorRead.model_validate(result.connector),
        normalized_input=result.normalized_input,
        mapping=ConnectorConversationMappingRead.model_validate(result.mapping) if result.mapping else None,
        trace=result.trace,
        agent_response=result.agent_response,
        outbound_response=result.outbound_response,
        delivery_status=result.delivery.delivery_status,
        error=result.delivery.error_message,
    )


def build_test_payload(
    message_text: str,
    sender_name: str,
    external_user_id: str,
    external_chat_id: str,
    verification_token: str | None = None,
) -> dict[str, Any]:
    now_ms = str(int(datetime.now(timezone.utc).timestamp() * 1000))
    payload = {
        "event": {
            "message": {
                "message_id": f"test_{uuid.uuid4().hex}",
                "chat_id": external_chat_id,
                "create_time": now_ms,
                "message_type": "text",
                "content": json.dumps({"text": message_text}, ensure_ascii=False),
            },
            "sender": {
                "sender_id": {"open_id": external_user_id},
                "sender_name": sender_name,
            },
        }
    }
    if verification_token:
        payload["header"] = {"token": verification_token}
    return payload
