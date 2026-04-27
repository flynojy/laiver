import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.router import api_router
from app.core.config import get_settings
from app.core.enums import ProviderType
from app.db.session import SessionLocal
from app.db.init_db import init_db
from app.models.runtime import ModelProvider
from app.services.local_adapter_runtime import get_local_adapter_runtime_manager
from app.services.memory_service import run_memory_maintenance

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.auto_init_db:
        init_db()
    runtime_manager = get_local_adapter_runtime_manager()
    cleanup_task = None
    memory_maintenance_task = None
    if settings.local_adapter_cleanup_interval_seconds > 0:
        async def cleanup_loop() -> None:
            while True:
                await asyncio.sleep(settings.local_adapter_cleanup_interval_seconds)
                runtime_manager.cleanup_idle()

        cleanup_task = asyncio.create_task(cleanup_loop())
    if settings.memory_maintenance_enabled and settings.memory_maintenance_interval_seconds > 0:
        async def memory_maintenance_loop() -> None:
            while True:
                await asyncio.sleep(settings.memory_maintenance_interval_seconds)
                with SessionLocal() as db:
                    run_memory_maintenance(db)

        memory_maintenance_task = asyncio.create_task(memory_maintenance_loop())
    if settings.local_adapter_preload_default:
        with SessionLocal() as db:
            default_local_adapter = db.scalar(
                select(ModelProvider).where(
                    ModelProvider.is_default.is_(True),
                    ModelProvider.is_enabled.is_(True),
                    ModelProvider.provider_type == ProviderType.LOCAL_ADAPTER,
                )
            )
            if default_local_adapter:
                runtime_manager.warm(default_local_adapter)
    yield
    if cleanup_task is not None:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    if memory_maintenance_task is not None:
        memory_maintenance_task.cancel()
        try:
            await memory_maintenance_task
        except asyncio.CancelledError:
            pass
    runtime_manager.shutdown()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)
