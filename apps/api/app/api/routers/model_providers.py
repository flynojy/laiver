import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import ProviderType
from app.db.session import get_db
from app.models.runtime import ModelProvider
from app.schemas.runtime import (
    LocalAdapterRuntimeRead,
    ModelCompletionRequest,
    ModelCompletionResponse,
    ModelProviderCreate,
    ModelProviderRead,
    ModelProviderUpdate,
    ModelProviderValidationRequest,
    ModelProviderValidationResponse,
)
from app.services.local_adapter_runtime import get_local_adapter_runtime_manager
from app.services.model_router import ModelRouterService

router = APIRouter()
settings = get_settings()


@router.get("", response_model=list[ModelProviderRead])
def list_model_providers(db: Session = Depends(get_db)) -> list[ModelProvider]:
    return db.scalars(select(ModelProvider).order_by(ModelProvider.created_at.desc())).all()


@router.post("", response_model=ModelProviderRead)
def create_model_provider(payload: ModelProviderCreate, db: Session = Depends(get_db)) -> ModelProvider:
    if payload.is_default:
        for existing in db.scalars(select(ModelProvider).where(ModelProvider.is_default.is_(True))).all():
            existing.is_default = False
    row = ModelProvider(**payload.model_dump())
    if row.is_default:
        row.is_enabled = True
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{provider_id}", response_model=ModelProviderRead)
def update_model_provider(
    provider_id: str,
    payload: ModelProviderUpdate,
    db: Session = Depends(get_db),
) -> ModelProvider:
    row = db.scalar(select(ModelProvider).where(ModelProvider.id == uuid.UUID(provider_id)))
    if not row:
        raise HTTPException(status_code=404, detail="Model provider not found")

    updates = payload.model_dump(exclude_unset=True)
    if updates.get("is_default") is True:
        for existing in db.scalars(select(ModelProvider).where(ModelProvider.is_default.is_(True))).all():
            existing.is_default = False
        updates["is_enabled"] = True

    for key, value in updates.items():
        setattr(row, key, value)

    db.commit()
    db.refresh(row)
    if row.provider_type == ProviderType.LOCAL_ADAPTER and row.is_enabled is False:
        get_local_adapter_runtime_manager().evict_by_provider_id(row.id)
    return row


@router.post("/bootstrap", response_model=ModelProviderRead)
def bootstrap_model_provider(db: Session = Depends(get_db)) -> ModelProvider:
    row = db.scalar(select(ModelProvider).where(ModelProvider.is_default.is_(True)))
    if row:
        return row

    row = ModelProvider(
        name="DeepSeek Default",
        provider_type=ProviderType.DEEPSEEK,
        base_url=settings.deepseek_base_url,
        model_name=settings.deepseek_model,
        api_key_ref="env:DEEPSEEK_API_KEY",
        settings={"supports_streaming": True, "supports_tool_calling": True},
        is_default=True,
        is_enabled=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/complete", response_model=ModelCompletionResponse)
async def complete_chat(
    payload: ModelCompletionRequest,
    db: Session = Depends(get_db),
) -> ModelCompletionResponse:
    return await ModelRouterService(db).complete(payload)


@router.post("/stream")
async def stream_chat(payload: ModelCompletionRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    async def event_stream():
        async for chunk in ModelRouterService(db).stream(payload):
            yield chunk

    return StreamingResponse(event_stream(), media_type="text/plain")


@router.post("/validate", response_model=ModelProviderValidationResponse)
async def validate_provider(
    payload: ModelProviderValidationRequest,
    db: Session = Depends(get_db),
) -> ModelProviderValidationResponse:
    return await ModelRouterService(db).validate(payload)


@router.get("/local-adapters/runtime", response_model=list[LocalAdapterRuntimeRead])
def list_local_adapter_runtime(db: Session = Depends(get_db)) -> list[LocalAdapterRuntimeRead]:
    providers = db.scalars(
        select(ModelProvider).where(ModelProvider.provider_type == ProviderType.LOCAL_ADAPTER)
    ).all()
    return get_local_adapter_runtime_manager().list_statuses(providers)


@router.post("/{provider_id}/warm", response_model=LocalAdapterRuntimeRead)
def warm_local_adapter(provider_id: str, db: Session = Depends(get_db)) -> LocalAdapterRuntimeRead:
    provider = db.scalar(select(ModelProvider).where(ModelProvider.id == uuid.UUID(provider_id)))
    if not provider:
        raise HTTPException(status_code=404, detail="Model provider not found")
    if provider.provider_type != ProviderType.LOCAL_ADAPTER:
        raise HTTPException(status_code=400, detail="Only local_adapter providers can be warmed")
    status = get_local_adapter_runtime_manager().warm(provider)
    if status.status == "error":
        raise HTTPException(status_code=400, detail=status.error or "Local adapter warm failed")
    return status


@router.post("/{provider_id}/evict", response_model=LocalAdapterRuntimeRead)
def evict_local_adapter(provider_id: str, db: Session = Depends(get_db)) -> LocalAdapterRuntimeRead:
    provider = db.scalar(select(ModelProvider).where(ModelProvider.id == uuid.UUID(provider_id)))
    if not provider:
        raise HTTPException(status_code=404, detail="Model provider not found")
    if provider.provider_type != ProviderType.LOCAL_ADAPTER:
        raise HTTPException(status_code=400, detail="Only local_adapter providers can be evicted")
    return get_local_adapter_runtime_manager().evict(provider)
