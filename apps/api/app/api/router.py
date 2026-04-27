from fastapi import APIRouter

from app.api.routers import (
    agent,
    connectors,
    conversations,
    fine_tuning,
    health,
    imports,
    memories,
    model_providers,
    personas,
    skills,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(imports.router, prefix="/imports", tags=["imports"])
api_router.include_router(personas.router, prefix="/personas", tags=["personas"])
api_router.include_router(memories.router, prefix="/memories", tags=["memories"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(fine_tuning.router, prefix="/fine-tuning", tags=["fine-tuning"])
api_router.include_router(skills.router, prefix="/skills", tags=["skills"])
api_router.include_router(connectors.router, prefix="/connectors", tags=["connectors"])
api_router.include_router(model_providers.router, prefix="/model-providers", tags=["model-providers"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
