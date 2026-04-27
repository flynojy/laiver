from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.core.enums import MemoryType
from app.schemas.memory_candidate import MemoryCandidateRead
from app.schemas.memory_episode import MemoryEpisodeRead
from app.schemas.memory_fact import MemoryFactRead, MemoryRevisionRead


class MemoryCreate(BaseModel):
    user_id: uuid.UUID
    persona_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    source_message_id: uuid.UUID | None = None
    memory_type: MemoryType
    content: str
    importance_score: float = 0.8
    confidence_score: float = 0.8
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    user_id: uuid.UUID
    persona_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    source_message_id: uuid.UUID | None = None
    memory_type: MemoryType
    content: str
    content_hash: str
    embedding_model: str
    vector_id: str
    importance_score: float
    confidence_score: float
    access_count: int
    last_accessed_at: datetime | None = None
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("details", "metadata"),
    )
    created_at: datetime
    updated_at: datetime


class MemoryUpdate(BaseModel):
    importance_score: float | None = None
    confidence_score: float | None = None
    metadata: dict[str, Any] | None = None


class MemorySearchRequest(BaseModel):
    user_id: uuid.UUID
    query: str
    persona_id: uuid.UUID | None = None
    memory_types: list[MemoryType] = Field(default_factory=list)
    limit: int = 5


class MemoryDebugResponse(BaseModel):
    qdrant_available: bool
    collection_name: str
    total_memories: int
    total_episodes: int = 0
    total_facts: int = 0
    total_revisions: int = 0
    candidate_counts: dict[str, int] = Field(default_factory=dict)
    recent_memories: list[MemoryRead]
    recent_episodes: list[MemoryEpisodeRead] = Field(default_factory=list)
    recent_facts: list[MemoryFactRead] = Field(default_factory=list)
    recent_revisions: list[MemoryRevisionRead] = Field(default_factory=list)
    recent_candidates: list[MemoryCandidateRead] = Field(default_factory=list)
    profile_summary: str = ""
    profile_snapshot: dict[str, Any] = Field(default_factory=dict)
    user_profile_snapshot: dict[str, Any] = Field(default_factory=dict)
    relationship_state_snapshot: dict[str, Any] = Field(default_factory=dict)
    conflict_groups: list[dict[str, Any]] = Field(default_factory=list)
    lifecycle_counts: dict[str, int] = Field(default_factory=dict)


class MemoryMaintenanceReport(BaseModel):
    run_at: str
    dry_run: bool
    facts_scanned: int
    facts_decayed: int
    facts_archived: int
    candidates_scanned: int
    candidates_ignored: int
    profiles_rebuilt: int
    decayed_fact_ids: list[str] = Field(default_factory=list)
    archived_fact_ids: list[str] = Field(default_factory=list)
    ignored_candidate_ids: list[str] = Field(default_factory=list)
