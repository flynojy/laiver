from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import MemoryType
from app.models.memory_candidate import MemoryCandidate
from app.models.memory import Memory
from app.models.memory_episode import MemoryEpisode
from app.models.memory_fact import MemoryFact
from app.models.memory_revision import MemoryRevision
from app.models.relationship_state import RelationshipState
from app.models.user_profile import UserProfile
from app.models.user import User
from app.schemas.memory import MemoryCreate, MemoryDebugResponse, MemoryUpdate
from app.utils.text import normalize_whitespace, tokenize

settings = get_settings()


class LocalHashEmbeddingProvider:
    def __init__(self, size: int) -> None:
        self.size = size

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.size
        for token in tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = digest[0] % self.size
            sign = 1.0 if digest[1] % 2 == 0 else -1.0
            weight = 1.0 + (digest[2] / 255.0)
            vector[index] += sign * weight
        norm = math.sqrt(sum(item * item for item in vector)) or 1.0
        return [item / norm for item in vector]


class QdrantMemoryIndex:
    def __init__(self) -> None:
        self.client = QdrantClient(url=settings.qdrant_url, check_compatibility=False)
        self.collection_name = settings.qdrant_collection
        self.vector_size = settings.memory_vector_size

    def ensure_collection(self) -> bool:
        try:
            collections = self.client.get_collections().collections
            if not any(item.name == self.collection_name for item in collections):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qdrant_models.VectorParams(
                        size=self.vector_size,
                        distance=qdrant_models.Distance.COSINE,
                    ),
                )
            return True
        except Exception:
            return False

    def upsert(self, memory_id: str, vector: list[float], payload: dict) -> bool:
        if not self.ensure_collection():
            return False
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[qdrant_models.PointStruct(id=memory_id, vector=vector, payload=payload)],
            )
            return True
        except Exception:
            return False

    def search(self, vector: list[float], user_id: str, persona_id: str | None, limit: int) -> list[str]:
        if not self.ensure_collection():
            return []

        filters = [
            qdrant_models.FieldCondition(
                key="user_id",
                match=qdrant_models.MatchValue(value=user_id),
            )
        ]
        if persona_id:
            filters.append(
                qdrant_models.FieldCondition(
                    key="persona_id",
                    match=qdrant_models.MatchValue(value=persona_id),
                )
            )
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                query_filter=qdrant_models.Filter(must=filters),
                limit=limit,
            )
            return [str(item.id) for item in results]
        except Exception:
            return []


embedding_provider = LocalHashEmbeddingProvider(settings.memory_vector_size)
vector_index = QdrantMemoryIndex()

FACT_KEY_STOPWORDS = {
    "i",
    "me",
    "my",
    "we",
    "you",
    "the",
    "a",
    "an",
    "to",
    "for",
    "of",
    "and",
    "is",
    "are",
    "be",
    "it",
    "that",
    "this",
    "please",
    "remember",
    "always",
    "prefer",
    "like",
    "keep",
    "tone",
}

MEMORY_ROUTE_HINTS = {
    "profile": (
        "prefer",
        "preference",
        "style",
        "tone",
        "what do i like",
        "what style",
        "how should you respond",
        "response style",
        "keep it practical",
    ),
    "instruction": (
        "remember",
        "always",
        "must",
        "should you",
        "do not",
        "don't",
        "rule",
        "instruction",
        "from now on",
    ),
    "episodic": (
        "last time",
        "earlier",
        "before",
        "yesterday",
        "today",
        "when we",
        "we discussed",
        "what happened",
        "previously",
    ),
}

FACT_AUTO_COMMIT_MIN_IMPORTANCE = 0.75
FACT_AUTO_COMMIT_MIN_CONFIDENCE = 0.72
REVIEW_REQUIRED_SENSITIVITY = {"sensitive", "private", "high"}
DECAY_POLICY_RATES = {
    "session": 0.08,
    "volatile": 0.05,
    "default": 0.02,
    "slow": 0.01,
    "stable": 0.005,
    "permanent": 0.0,
}
DECAY_POLICY_GRACE_DAYS = {
    "session": 0,
    "volatile": 3,
    "default": 14,
    "slow": 30,
    "stable": 90,
    "permanent": 36500,
}
FACT_ARCHIVE_STABILITY_THRESHOLD = 0.12
FACT_ARCHIVE_IMPORTANCE_THRESHOLD = 0.2
STALE_CANDIDATE_DAYS = 30


def _normalized_content(content: str) -> str:
    lowered = normalize_whitespace(content).lower()
    return re.sub(r"[^a-z0-9\u4e00-\u9fff\s]+", "", lowered).strip()


def _hash_content(content: str) -> str:
    return hashlib.sha256(_normalized_content(content).encode("utf-8")).hexdigest()


def _build_dedupe_key(content: str) -> str:
    normalized = _normalized_content(content)
    tokens = normalized.split()[:10]
    return " ".join(tokens)


def _memory_state(details: dict[str, Any]) -> str:
    return str(details.get("state", "active"))


def _aware_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _memory_label_from_metadata(metadata: dict[str, Any]) -> str:
    return str(metadata.get("memory_label", "session"))


def _memory_label(memory: Memory | MemoryCreate) -> str:
    if isinstance(memory, Memory):
        return _memory_label_from_metadata(memory.details)
    return _memory_label_from_metadata(memory.metadata)


def _extract_fact_key(content: str, *, label: str) -> str:
    normalized = _normalized_content(content)
    raw_tokens = [
        token
        for token in tokenize(normalized)
        if token not in FACT_KEY_STOPWORDS and len(token) > 1
    ]
    token_limit = 5 if label in {"instruction", "preference"} else 6
    tokens = raw_tokens[:token_limit]
    if tokens:
        return " ".join(tokens)
    return _build_dedupe_key(content) or "general"


def _infer_polarity(content: str) -> str:
    lowered = normalize_whitespace(content).lower()
    negative_markers = ("don't", "do not", "never", "not ", "no ", "avoid", "stop", "别", "不要", "不能")
    return "negative" if any(marker in lowered for marker in negative_markers) else "positive"


def _memory_bucket(memory: Memory | MemoryCreate) -> str:
    label = _memory_label(memory)
    if label in {"instruction", "preference"}:
        return "identity"
    if label == "episodic":
        return "timeline"
    if label == "assistant_reply":
        return "assistant"
    return "context"


def _memory_strength(memory: Memory) -> float:
    reinforcement_count = int(memory.details.get("reinforcement_count", memory.details.get("duplicate_count", 1)))
    pinned_boost = 1.0 if memory.details.get("pinned") else 0.0
    strength = (memory.importance_score * 0.4) + (memory.confidence_score * 0.4)
    strength += min(memory.access_count, 8) * 0.05
    strength += min(reinforcement_count, 6) * 0.08
    strength += pinned_boost
    if memory.details.get("current_version", True):
        strength += 0.3
    return round(strength, 4)


def _line_for_profile(memory: Memory) -> str:
    label = _memory_label(memory)
    prefix = {
        "instruction": "Instruction",
        "preference": "Preference",
        "episodic": "Episode",
    }.get(label, "Memory")
    return f"{prefix}: {normalize_whitespace(memory.content)}"


def _is_searchable_memory(memory: Memory) -> bool:
    state = _memory_state(memory.details)
    return state in {"active", "pinned"} and bool(memory.details.get("current_version", True))


def infer_memory_profile(text: str, *, origin: str = "user_message") -> tuple[MemoryType, str, float, float]:
    lowered = text.lower()

    instruction_hits = [
        token
        for token in ("remember", "please remember", "from now on", "always", "must", "prefer")
        if token in lowered
    ]
    if any(token in text for token in ("请记住", "记住", "以后", "总是", "偏好", "必须")):
        instruction_hits.append("zh-instruction")

    preference_hits = [
        token
        for token in ("i like", "i prefer", "my favorite", "keep the tone", "i usually")
        if token in lowered
    ]
    if any(token in text for token in ("我喜欢", "我偏好", "我通常", "保持语气")):
        preference_hits.append("zh-preference")

    episodic_hits = [
        token
        for token in ("yesterday", "today", "we discussed", "when we", "last time", "shipped", "fixed")
        if token in lowered
    ]
    if any(token in text for token in ("今天", "昨天", "刚刚", "上次", "讨论过", "修复了")):
        episodic_hits.append("zh-episodic")

    if instruction_hits:
        return MemoryType.INSTRUCTION, "instruction", 0.92, 0.9
    if preference_hits:
        return MemoryType.SEMANTIC, "preference", 0.84, 0.82
    if episodic_hits:
        return MemoryType.EPISODIC, "episodic", 0.76, 0.72
    if origin == "assistant_message":
        return MemoryType.SESSION, "assistant_reply", 0.35, 0.38
    return MemoryType.SESSION, "session", 0.55, 0.5


def _write_strategy(memory_label: str) -> str:
    if memory_label == "instruction":
        return "high_priority_instruction"
    if memory_label == "preference":
        return "preference_profile"
    if memory_label == "episodic":
        return "episodic_context"
    if memory_label == "assistant_reply":
        return "assistant_low_signal"
    return "session_context"


def _find_near_duplicate(db: Session, payload: MemoryCreate, content_hash: str) -> Memory | None:
    existing = db.scalar(
        select(Memory).where(
            Memory.user_id == payload.user_id,
            Memory.memory_type == payload.memory_type,
            Memory.content_hash == content_hash,
        )
    )
    if existing:
        return existing

    label = _memory_label(payload)
    if label not in {"instruction", "preference"}:
        return None

    current_tokens = set(tokenize(payload.content))
    if not current_tokens:
        return None

    candidates = db.scalars(
        select(Memory)
        .where(
            Memory.user_id == payload.user_id,
            Memory.memory_type == payload.memory_type,
        )
        .order_by(desc(Memory.updated_at))
        .limit(20)
    ).all()
    for candidate in candidates:
        if _memory_label(candidate) != label:
            continue
        candidate_tokens = set(tokenize(candidate.content))
        overlap = len(current_tokens & candidate_tokens) / max(len(current_tokens | candidate_tokens), 1)
        if overlap >= 0.76:
            return candidate
    return None


def _find_conflicting_candidates(db: Session, payload: MemoryCreate) -> list[Memory]:
    label = _memory_label(payload)
    if label not in {"instruction", "preference"}:
        return []

    fact_key = str(payload.metadata.get("fact_key", "")).strip()
    polarity = str(payload.metadata.get("polarity", "positive")).strip()
    if not fact_key:
        return []

    candidates = db.scalars(
        select(Memory)
        .where(
            Memory.user_id == payload.user_id,
            Memory.memory_type == payload.memory_type,
        )
        .order_by(desc(Memory.updated_at))
        .limit(20)
    ).all()
    conflicts: list[Memory] = []
    for candidate in candidates:
        if _memory_label(candidate) != label:
            continue
        if not candidate.details.get("current_version", True):
            continue
        candidate_key = str(candidate.details.get("fact_key", "")).strip()
        if candidate_key != fact_key:
            continue
        candidate_polarity = str(candidate.details.get("polarity", "positive")).strip()
        if candidate_polarity != polarity:
            conflicts.append(candidate)
    return conflicts


def _should_skip_memory_write(payload: MemoryCreate) -> bool:
    normalized = _normalized_content(payload.content)
    label = _memory_label(payload)
    origin = str(payload.metadata.get("origin", payload.metadata.get("source", "manual")))
    state = str(payload.metadata.get("state", "active"))

    if state in {"archived", "ignored"}:
        return True
    if len(normalized) < 12:
        return True
    if origin == "assistant_message" and label == "assistant_reply":
        if "mock mode is active" in normalized or len(normalized.split()) < 10:
            return True
    if label == "session" and len(normalized.split()) < 6:
        return True
    return False


def _active_memories_for_profile(
    db: Session,
    *,
    user_id: UUID,
    persona_id: UUID | None = None,
) -> list[Memory]:
    statement = select(Memory).where(Memory.user_id == user_id).order_by(desc(Memory.updated_at))
    if persona_id:
        statement = statement.where(Memory.persona_id == persona_id)
    rows = db.scalars(statement).all()
    return [row for row in rows if _is_searchable_memory(row)]


def _fact_strength(fact: MemoryFact) -> float:
    strength = (fact.importance * 0.35) + (fact.confidence * 0.35) + (fact.stability_score * 0.2)
    strength += min(fact.reinforcement_count, 6) * 0.05
    if fact.last_used_at is not None:
        strength += 0.05
    return round(strength, 4)


def classify_memory_query(query: str) -> str:
    lowered = normalize_whitespace(query).lower()
    for route, markers in MEMORY_ROUTE_HINTS.items():
        if any(marker in lowered for marker in markers):
            return route
    return "general"


def _active_facts_for_profile(
    db: Session,
    *,
    user_id: UUID,
    persona_id: UUID | None = None,
) -> list[MemoryFact]:
    statement = select(MemoryFact).where(
        MemoryFact.user_id == user_id,
        MemoryFact.status == "active",
    ).order_by(desc(MemoryFact.updated_at))
    if persona_id:
        statement = statement.where(MemoryFact.persona_id == persona_id)
    rows = db.scalars(statement).all()
    return [row for row in rows if row.current_revision_id is not None]


def _fact_text(fact: MemoryFact) -> str:
    if fact.value_text:
        return normalize_whitespace(fact.value_text)
    content = fact.value_json.get("content")
    if isinstance(content, str):
        return normalize_whitespace(content)
    return normalize_whitespace(str(fact.value_json or ""))


def _is_negative_fact(fact: MemoryFact) -> bool:
    polarity = str(fact.value_json.get("polarity", "")).strip().lower()
    if polarity == "negative":
        return True
    return _infer_polarity(_fact_text(fact)) == "negative"


def _extract_preferred_tone(preferences: list[MemoryFact], instructions: list[MemoryFact]) -> str | None:
    style_candidates = preferences + instructions
    markers = ("concise", "warm", "practical", "gentle", "direct", "playful", "calm")
    for fact in style_candidates:
        text = _fact_text(fact).lower()
        for marker in markers:
            if marker in text:
                return marker
    return None


def _topic_candidates_from_memories(memories: list[Memory]) -> list[str]:
    topics: list[str] = []
    for memory in memories:
        candidate = str(memory.details.get("fact_key") or memory.details.get("dedupe_key") or "").strip()
        if candidate and candidate not in topics:
            topics.append(candidate)
    return topics[:5]


def _serialize_user_profile(profile: UserProfile | None) -> dict[str, Any]:
    if profile is None:
        return {}
    return {
        "id": str(profile.id),
        "user_id": str(profile.user_id),
        "core_identity": dict(profile.core_identity or {}),
        "communication_style": dict(profile.communication_style or {}),
        "stable_preferences": dict(profile.stable_preferences or {}),
        "boundaries": dict(profile.boundaries or {}),
        "life_context": dict(profile.life_context or {}),
        "profile_summary": profile.profile_summary,
        "profile_version": profile.profile_version,
        "source_fact_count": profile.source_fact_count,
        "last_rebuilt_at": profile.last_rebuilt_at.isoformat() if profile.last_rebuilt_at else None,
        "confidence": profile.confidence,
    }


def _serialize_relationship_state(state: RelationshipState | None) -> dict[str, Any]:
    if state is None:
        return {}
    return {
        "id": str(state.id),
        "user_id": str(state.user_id),
        "persona_id": str(state.persona_id),
        "relationship_stage": state.relationship_stage,
        "warmth_score": state.warmth_score,
        "trust_score": state.trust_score,
        "familiarity_score": state.familiarity_score,
        "preferred_tone": state.preferred_tone,
        "active_topics": list(state.active_topics or []),
        "recurring_rituals": list(state.recurring_rituals or []),
        "recent_sensitivities": list(state.recent_sensitivities or []),
        "unresolved_tensions": list(state.unresolved_tensions or []),
        "last_meaningful_interaction_at": (
            state.last_meaningful_interaction_at.isoformat() if state.last_meaningful_interaction_at else None
        ),
        "last_repair_at": state.last_repair_at.isoformat() if state.last_repair_at else None,
        "summary": state.summary,
        "version": state.version,
    }


def _memory_row_for_fact(db: Session, fact: MemoryFact) -> Memory | None:
    memory_id = str((fact.details or {}).get("memory_id", "")).strip()
    if not memory_id:
        return None
    try:
        return db.scalar(select(Memory).where(Memory.id == UUID(memory_id)))
    except ValueError:
        return None


def _fact_backed_memories(
    db: Session,
    *,
    user_id: UUID,
    persona_id: UUID | None,
    fact_types: tuple[str, ...],
    limit: int,
) -> list[Memory]:
    statement = (
        select(MemoryFact)
        .where(
            MemoryFact.user_id == user_id,
            MemoryFact.status == "active",
            MemoryFact.fact_type.in_(fact_types),
        )
        .order_by(desc(MemoryFact.updated_at))
        .limit(max(limit * 2, 8))
    )
    if persona_id is None:
        statement = statement.where(MemoryFact.persona_id.is_(None))
    else:
        statement = statement.where(MemoryFact.persona_id == persona_id)

    facts = db.scalars(statement).all()
    rows: list[Memory] = []
    seen: set[str] = set()
    for fact in sorted(facts, key=_fact_strength, reverse=True):
        row = _memory_row_for_fact(db, fact)
        if row is None or not _is_searchable_memory(row):
            continue
        row_id = str(row.id)
        if row_id in seen:
            continue
        seen.add(row_id)
        rows.append(row)
        if len(rows) >= limit:
            break
    return rows


def build_memory_profile(
    db: Session,
    *,
    user_id: UUID,
    persona_id: UUID | None = None,
) -> dict[str, Any]:
    facts = _active_facts_for_profile(db, user_id=user_id, persona_id=persona_id)
    memory_rows = _active_memories_for_profile(db, user_id=user_id, persona_id=persona_id)

    if facts:
        ranked_facts = sorted(facts, key=_fact_strength, reverse=True)
        stable_preferences = [row for row in ranked_facts if row.fact_type == "preference"][:5]
        stable_instructions = [row for row in ranked_facts if row.fact_type == "instruction"][:5]
    else:
        ranked_memories = sorted(memory_rows, key=_memory_strength, reverse=True)
        stable_preferences = [row for row in ranked_memories if _memory_label(row) == "preference"][:5]
        stable_instructions = [row for row in ranked_memories if _memory_label(row) == "instruction"][:5]

    recent_episodes = [row for row in memory_rows if _memory_label(row) == "episodic"][:5]
    identity_facts = [row for row in facts if row.fact_type == "identity"][:5]
    boundary_facts = [row for row in stable_instructions if _is_negative_fact(row)] if facts else []
    preferred_tone = _extract_preferred_tone(stable_preferences, stable_instructions)

    summary_lines: list[str] = []
    if stable_instructions:
        summary_lines.append("Long-term instructions:")
        summary_lines.extend(f"- {_fact_text(item) if facts else normalize_whitespace(item.content)}" for item in stable_instructions[:3])
    if stable_preferences:
        summary_lines.append("Long-term preferences:")
        summary_lines.extend(f"- {_fact_text(item) if facts else normalize_whitespace(item.content)}" for item in stable_preferences[:3])
    if recent_episodes:
        summary_lines.append("Recent episodic context:")
        summary_lines.extend(f"- {normalize_whitespace(item.content)}" for item in recent_episodes[:2])

    stable_preferences_text = [_fact_text(item) if facts else item.content for item in stable_preferences]
    stable_instructions_text = [_fact_text(item) if facts else item.content for item in stable_instructions]
    recent_episodes_text = [item.content for item in recent_episodes]

    return {
        "summary_text": "\n".join(summary_lines),
        "stable_preferences": stable_preferences_text,
        "stable_instructions": stable_instructions_text,
        "recent_episodes": recent_episodes_text,
        "core_identity": {"items": [_fact_text(item) for item in identity_facts]},
        "communication_style": {
            "preferred_tone": preferred_tone,
            "instructions": stable_instructions_text[:3],
        },
        "boundaries": {"items": [_fact_text(item) for item in boundary_facts[:5]]},
        "life_context": {
            "recent_episodes": recent_episodes_text[:3],
        },
        "by_bucket": {
            "identity": (
                [f"Preference: {_fact_text(item)}" for item in stable_preferences[:3]]
                + [f"Instruction: {_fact_text(item)}" for item in stable_instructions[:3]]
            )[:6],
            "timeline": [f"Episode: {normalize_whitespace(item.content)}" for item in recent_episodes[:4]],
            "context": [_line_for_profile(item) for item in memory_rows if _memory_bucket(item) == "context"][:4],
        },
    }


def build_relationship_state_snapshot(
    db: Session,
    *,
    user_id: UUID,
    persona_id: UUID | None,
    profile_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if persona_id is None:
        return {}

    facts = _active_facts_for_profile(db, user_id=user_id, persona_id=persona_id)
    memories = _active_memories_for_profile(db, user_id=user_id, persona_id=persona_id)
    snapshot = profile_snapshot or build_memory_profile(db, user_id=user_id, persona_id=persona_id)
    active_topics = _topic_candidates_from_memories(memories)
    sensitivities = [
        _fact_text(item)
        for item in facts
        if item.fact_type == "instruction" and _is_negative_fact(item)
    ][:3]
    event_count = len(memories) + len(facts)
    if event_count >= 8:
        relationship_stage = "established"
    elif event_count >= 3:
        relationship_stage = "developing"
    else:
        relationship_stage = "new"

    familiarity = min(0.95, 0.35 + min(event_count, 8) * 0.07)
    warmth = min(0.95, 0.4 + min(len(snapshot.get("stable_preferences", [])), 5) * 0.08)
    trust = min(0.95, 0.4 + min(len(snapshot.get("stable_instructions", [])), 5) * 0.08)
    preferred_tone = snapshot.get("communication_style", {}).get("preferred_tone")
    recent_episode_lines = snapshot.get("recent_episodes", [])[:2]
    summary_parts = [
        f"Stage: {relationship_stage}",
        f"Tone: {preferred_tone or 'adaptive'}",
    ]
    if recent_episode_lines:
        summary_parts.append("Recent context: " + "; ".join(recent_episode_lines))

    return {
        "relationship_stage": relationship_stage,
        "warmth_score": round(warmth, 3),
        "trust_score": round(trust, 3),
        "familiarity_score": round(familiarity, 3),
        "preferred_tone": preferred_tone,
        "active_topics": active_topics[:5],
        "recurring_rituals": [],
        "recent_sensitivities": sensitivities,
        "unresolved_tensions": [],
        "summary": " | ".join(summary_parts),
    }


def _persist_profile_snapshot(
    db: Session,
    *,
    user_id: UUID,
    persona_id: UUID | None,
    profile_snapshot: dict[str, Any],
) -> None:
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        return
    now = datetime.now(timezone.utc)
    preferences = dict(user.preferences or {})
    preferences["memory_profile"] = {
        **profile_snapshot,
        "updated_at": now.isoformat(),
    }
    user.preferences = preferences

    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if profile is None:
        profile = UserProfile(user_id=user_id)
        db.add(profile)

    profile.core_identity = dict(profile_snapshot.get("core_identity", {}))
    profile.communication_style = dict(profile_snapshot.get("communication_style", {}))
    profile.stable_preferences = {"items": list(profile_snapshot.get("stable_preferences", []))}
    profile.boundaries = dict(profile_snapshot.get("boundaries", {}))
    profile.life_context = dict(profile_snapshot.get("life_context", {}))
    profile.profile_summary = str(profile_snapshot.get("summary_text", ""))
    profile.profile_version = int(profile.profile_version or 0) + 1
    profile.source_fact_count = len(_active_facts_for_profile(db, user_id=user_id, persona_id=persona_id))
    profile.last_rebuilt_at = now
    profile.confidence = round(
        min(
            0.99,
            0.4 + min(len(profile_snapshot.get("stable_preferences", [])) + len(profile_snapshot.get("stable_instructions", [])), 6) * 0.08,
        ),
        3,
    )

    if persona_id is not None:
        relationship_snapshot = build_relationship_state_snapshot(
            db,
            user_id=user_id,
            persona_id=persona_id,
            profile_snapshot=profile_snapshot,
        )
        state = db.scalar(
            select(RelationshipState).where(
                RelationshipState.user_id == user_id,
                RelationshipState.persona_id == persona_id,
            )
        )
        if state is None:
            state = RelationshipState(user_id=user_id, persona_id=persona_id)
            db.add(state)
        state.relationship_stage = str(relationship_snapshot.get("relationship_stage", state.relationship_stage))
        state.warmth_score = float(relationship_snapshot.get("warmth_score", state.warmth_score))
        state.trust_score = float(relationship_snapshot.get("trust_score", state.trust_score))
        state.familiarity_score = float(relationship_snapshot.get("familiarity_score", state.familiarity_score))
        state.preferred_tone = relationship_snapshot.get("preferred_tone")
        state.active_topics = list(relationship_snapshot.get("active_topics", []))
        state.recurring_rituals = list(relationship_snapshot.get("recurring_rituals", []))
        state.recent_sensitivities = list(relationship_snapshot.get("recent_sensitivities", []))
        state.unresolved_tensions = list(relationship_snapshot.get("unresolved_tensions", []))
        state.last_meaningful_interaction_at = now
        state.summary = str(relationship_snapshot.get("summary", ""))
        state.version = int(state.version or 0) + 1


def _sync_memory_scores(memory: Memory) -> None:
    memory.details = {
        **memory.details,
        "stability_score": _memory_strength(memory),
        "memory_bucket": _memory_bucket(memory),
    }


def _fact_status_from_memory(memory: Memory) -> str:
    state = _memory_state(memory.details)
    if state == "ignored":
        return "ignored"
    if not memory.details.get("current_version", True):
        return "superseded"
    if state == "archived":
        return "archived"
    return "active"


def _fact_type_from_memory(memory: Memory) -> str:
    label = _memory_label(memory)
    if label == "assistant_reply":
        return "assistant_reply"
    return label


def _normalized_fact_slot(content: str, *, label: str, fact_key: str) -> str:
    normalized_key = normalize_whitespace(fact_key).lower()
    if not normalized_key:
        normalized_key = _build_dedupe_key(content)
    return f"{label}:{normalized_key or 'general'}"


def _revision_value_from_memory(memory: Memory) -> dict[str, Any]:
    return {
        "content": normalize_whitespace(memory.content),
        "memory_type": memory.memory_type.value,
        "memory_label": memory.details.get("memory_label"),
        "state": _memory_state(memory.details),
        "current_version": bool(memory.details.get("current_version", True)),
        "fact_key": memory.details.get("fact_key"),
        "dedupe_key": memory.details.get("dedupe_key"),
        "polarity": memory.details.get("polarity"),
        "source": memory.details.get("source"),
        "origin": memory.details.get("origin"),
        "write_strategy": memory.details.get("write_strategy"),
    }


def _find_memory_fact(
    db: Session,
    *,
    user_id: UUID,
    persona_id: UUID | None,
    normalized_key: str,
) -> MemoryFact | None:
    statement = (
        select(MemoryFact)
        .where(
            MemoryFact.user_id == user_id,
            MemoryFact.normalized_key == normalized_key,
        )
        .order_by(desc(MemoryFact.updated_at))
    )
    if persona_id is None:
        statement = statement.where(MemoryFact.persona_id.is_(None))
    else:
        statement = statement.where(MemoryFact.persona_id == persona_id)
    return db.scalar(statement)


def _next_revision_number(db: Session, *, fact_id: UUID) -> int:
    current = db.scalar(select(func.max(MemoryRevision.revision_no)).where(MemoryRevision.fact_id == fact_id))
    return int(current or 0) + 1


def _upsert_memory_fact(
    db: Session,
    *,
    payload: MemoryCreate,
    memory: Memory,
    episode: MemoryEpisode,
    operation: str,
) -> tuple[MemoryFact, MemoryRevision]:
    label = _memory_label(memory)
    fact_key = str(memory.details.get("fact_key", "")).strip()
    normalized_key = _normalized_fact_slot(memory.content, label=label, fact_key=fact_key)
    fact = _find_memory_fact(
        db,
        user_id=memory.user_id,
        persona_id=memory.persona_id,
        normalized_key=normalized_key,
    )
    created_fact = False
    now = datetime.now(timezone.utc)
    if fact is None:
        fact = MemoryFact(
            user_id=memory.user_id,
            persona_id=memory.persona_id,
            fact_type=_fact_type_from_memory(memory),
            subject_kind="user",
            predicate_key=fact_key or label,
            value_text=memory.content,
            value_json=_revision_value_from_memory(memory),
            normalized_key=normalized_key,
            status=_fact_status_from_memory(memory),
            confidence=memory.confidence_score,
            importance=memory.importance_score,
            stability_score=float(memory.details.get("stability_score", _memory_strength(memory))),
            reinforcement_count=int(
                memory.details.get("reinforcement_count", memory.details.get("duplicate_count", 1))
            ),
            source_count=1,
            effective_from=now,
            last_confirmed_at=now,
            last_used_at=memory.last_accessed_at,
            decay_policy=str(memory.details.get("decay_policy", "default")),
            sensitivity=str(memory.details.get("sensitivity", "normal")),
            details={
                "memory_id": str(memory.id),
                "memory_type": memory.memory_type.value,
                "memory_label": label,
                "source": memory.details.get("source"),
            },
        )
        db.add(fact)
        db.flush()
        created_fact = True

    previous_revision: MemoryRevision | None = None
    if fact.current_revision_id:
        previous_revision = db.scalar(select(MemoryRevision).where(MemoryRevision.id == fact.current_revision_id))
        if previous_revision and previous_revision.valid_to is None:
            previous_revision.valid_to = now

    fact.fact_type = _fact_type_from_memory(memory)
    fact.predicate_key = fact_key or label
    fact.value_text = memory.content
    fact.value_json = _revision_value_from_memory(memory)
    fact.status = _fact_status_from_memory(memory)
    fact.confidence = memory.confidence_score
    fact.importance = memory.importance_score
    fact.stability_score = float(memory.details.get("stability_score", _memory_strength(memory)))
    fact.reinforcement_count = int(memory.details.get("reinforcement_count", memory.details.get("duplicate_count", 1)))
    fact.source_count = 1 if created_fact else int(fact.source_count) + 1
    fact.effective_from = now if operation in {"create", "supersede"} or fact.effective_from is None else fact.effective_from
    fact.effective_to = None
    fact.last_confirmed_at = now
    fact.last_used_at = memory.last_accessed_at
    fact.decay_policy = str(memory.details.get("decay_policy", fact.decay_policy))
    fact.sensitivity = str(memory.details.get("sensitivity", fact.sensitivity))
    fact.details = {
        **dict(fact.details or {}),
        "memory_id": str(memory.id),
        "memory_type": memory.memory_type.value,
        "memory_label": label,
        "source": memory.details.get("source"),
        "origin": memory.details.get("origin"),
        "write_strategy": memory.details.get("write_strategy"),
    }

    revision = MemoryRevision(
        fact_id=fact.id,
        revision_no=_next_revision_number(db, fact_id=fact.id),
        op=operation,
        content_text=memory.content,
        value_json=_revision_value_from_memory(memory),
        confidence_delta=round(memory.confidence_score - (previous_revision.value_json.get("confidence", memory.confidence_score) if previous_revision else 0.0), 4)
        if previous_revision
        else round(memory.confidence_score, 4),
        source_episode_id=episode.id,
        supersedes_revision_id=previous_revision.id if operation == "supersede" and previous_revision else None,
        conflict_group_id=str(memory.details.get("conflict_group", "")) or None,
        valid_from=now,
        valid_to=None,
        author_type="system",
        reason_codes=[operation, label, str(memory.details.get("source", "memory_write"))],
    )
    db.add(revision)
    db.flush()

    fact.current_revision_id = revision.id
    memory.details = {
        **memory.details,
        "fact_id": str(fact.id),
        "fact_revision_id": str(revision.id),
    }
    return fact, revision


def _append_memory_episode(db: Session, payload: MemoryCreate) -> MemoryEpisode:
    source_type = str(payload.metadata.get("origin", payload.metadata.get("source", "memory_write"))).strip() or "memory_write"
    source_ref = str(payload.metadata.get("source_ref", payload.metadata.get("memory_label", ""))).strip() or None
    episode = MemoryEpisode(
        user_id=payload.user_id,
        persona_id=payload.persona_id,
        conversation_id=payload.conversation_id,
        source_message_id=payload.source_message_id,
        source_type=source_type,
        source_ref=source_ref,
        speaker_role=str(payload.metadata.get("speaker_role", "")) or None,
        occurred_at=datetime.now(timezone.utc),
        raw_text=payload.content,
        structured_payload={
            "memory_type": payload.memory_type.value,
            "memory_label": payload.metadata.get("memory_label"),
            "source": payload.metadata.get("source"),
            "origin": payload.metadata.get("origin"),
            "state": payload.metadata.get("state"),
            "fact_key": payload.metadata.get("fact_key"),
            "dedupe_key": payload.metadata.get("dedupe_key"),
            "write_strategy": payload.metadata.get("write_strategy"),
        },
        summary_short=normalize_whitespace(payload.content)[:500],
        importance=payload.importance_score,
        emotional_weight=float(payload.metadata.get("emotional_weight", 0.0) or 0.0),
    )
    db.add(episode)
    db.flush()
    return episode


def _should_extract_candidate(payload: MemoryCreate) -> bool:
    label = _memory_label(payload)
    origin = str(payload.metadata.get("origin", payload.metadata.get("source", "manual"))).strip()
    if origin == "assistant_message":
        return False
    if label not in {"instruction", "preference", "episodic"}:
        return False
    return len(_normalized_content(payload.content).split()) >= 3


def _candidate_action_for_label(label: str) -> str:
    if label in {"instruction", "preference"}:
        return "review_fact"
    if label == "episodic":
        return "review_episode"
    return "observe"


def _upsert_memory_candidate(
    db: Session,
    *,
    payload: MemoryCreate,
    memory: Memory,
    episode: MemoryEpisode,
    fact: MemoryFact | None,
    revision: MemoryRevision | None,
) -> MemoryCandidate | None:
    if not _should_extract_candidate(payload):
        return None

    label = _memory_label(payload)
    normalized_key = str(payload.metadata.get("fact_key") or payload.metadata.get("dedupe_key") or "").strip()
    if not normalized_key:
        normalized_key = _build_dedupe_key(payload.content) or "general"

    existing = db.scalar(
        select(MemoryCandidate).where(
            MemoryCandidate.episode_id == episode.id,
            MemoryCandidate.candidate_type == label,
            MemoryCandidate.normalized_key == normalized_key,
        )
    )
    if existing:
        existing.extracted_text = payload.content
        existing.proposed_value = {
            **dict(existing.proposed_value or {}),
            "content": payload.content,
            "memory_id": str(memory.id),
            "memory_type": memory.memory_type.value,
            "memory_label": label,
            "fact_write_gated": bool(memory.details.get("fact_write_gated")),
            "fact_id": str(fact.id) if fact else None,
            "fact_revision_id": str(revision.id) if revision else None,
        }
        existing.salience_score = max(existing.salience_score, payload.importance_score)
        existing.confidence_score = max(existing.confidence_score, payload.confidence_score)
        existing.sensitivity = str(payload.metadata.get("sensitivity", existing.sensitivity))
        existing.reason_codes = sorted(
            {
                *[str(item) for item in existing.reason_codes or []],
                label,
                str(payload.metadata.get("source", "memory_write")),
            }
        )
        return existing

    candidate = MemoryCandidate(
        user_id=payload.user_id,
        persona_id=payload.persona_id,
        episode_id=episode.id,
        candidate_type=label,
        extracted_text=payload.content,
        normalized_key=normalized_key,
        proposed_value={
            "content": payload.content,
            "memory_id": str(memory.id),
            "memory_type": memory.memory_type.value,
            "memory_label": label,
            "fact_write_gated": bool(memory.details.get("fact_write_gated")),
            "source": payload.metadata.get("source"),
            "origin": payload.metadata.get("origin"),
            "fact_id": str(fact.id) if fact else None,
            "fact_revision_id": str(revision.id) if revision else None,
        },
        proposed_action=_candidate_action_for_label(label),
        salience_score=payload.importance_score,
        confidence_score=payload.confidence_score,
        sensitivity=str(payload.metadata.get("sensitivity", "normal")),
        reason_codes=[
            label,
            str(payload.metadata.get("source", "memory_write")),
            str(payload.metadata.get("write_strategy", "memory_write")),
        ],
        auto_commit=False,
        status="pending",
        reviewer_type=None,
        processed_at=None,
    )
    db.add(candidate)
    db.flush()
    return candidate


def _metadata_bool(metadata: dict[str, Any], key: str, *, default: bool = False) -> bool:
    value = metadata.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _should_gate_fact_write(payload: MemoryCreate) -> bool:
    if not _should_extract_candidate(payload):
        return False
    label = _memory_label(payload)
    if label not in {"instruction", "preference"}:
        return False
    sensitivity = str(payload.metadata.get("sensitivity", "normal")).strip().lower()
    if _metadata_bool(payload.metadata, "requires_review"):
        return True
    if _metadata_bool(payload.metadata, "auto_commit", default=True) is False:
        return True
    if sensitivity in REVIEW_REQUIRED_SENSITIVITY:
        return True
    return (
        payload.importance_score < FACT_AUTO_COMMIT_MIN_IMPORTANCE
        or payload.confidence_score < FACT_AUTO_COMMIT_MIN_CONFIDENCE
    )


def _mark_conflicting_memories(
    *,
    memory: Memory,
    conflicts: list[Memory],
) -> None:
    if not conflicts:
        return

    conflict_group = f"{memory.details.get('fact_key', 'conflict')}::{memory.id}"
    memory.details = {
        **memory.details,
        "conflict_group": conflict_group,
        "current_version": True,
    }
    for conflict in conflicts:
        conflict.details = {
            **conflict.details,
            "state": "archived" if _memory_state(conflict.details) == "active" else _memory_state(conflict.details),
            "current_version": False,
            "superseded_by": str(memory.id),
            "conflict_group": conflict_group,
        }
        _sync_memory_scores(conflict)


def _memory_payload_for_review(memory: Memory) -> MemoryCreate:
    return MemoryCreate(
        user_id=memory.user_id,
        persona_id=memory.persona_id,
        conversation_id=memory.conversation_id,
        source_message_id=memory.source_message_id,
        memory_type=memory.memory_type,
        content=memory.content,
        importance_score=memory.importance_score,
        confidence_score=memory.confidence_score,
        metadata=dict(memory.details or {}),
    )


def _candidate_memory(db: Session, candidate: MemoryCandidate) -> Memory | None:
    memory_id = str((candidate.proposed_value or {}).get("memory_id", "")).strip()
    if not memory_id:
        return None
    try:
        return db.scalar(select(Memory).where(Memory.id == UUID(memory_id)))
    except ValueError:
        return None


def _approve_memory_candidate(db: Session, candidate: MemoryCandidate) -> None:
    now = datetime.now(timezone.utc)
    candidate.status = "approved"
    candidate.processed_at = now

    if candidate.proposed_value.get("fact_id"):
        return

    memory = _candidate_memory(db, candidate)
    if memory is None:
        return

    memory.details = {
        **dict(memory.details or {}),
        "state": "active",
        "current_version": True,
        "fact_write_gated": False,
        "review_status": "approved",
        "reviewed_candidate_id": str(candidate.id),
    }
    _sync_memory_scores(memory)

    payload = _memory_payload_for_review(memory)
    conflicts = _find_conflicting_candidates(db, payload)
    _mark_conflicting_memories(memory=memory, conflicts=conflicts)

    episode = db.scalar(select(MemoryEpisode).where(MemoryEpisode.id == candidate.episode_id))
    if episode is None:
        episode = _append_memory_episode(db, payload)

    fact, revision = _upsert_memory_fact(
        db,
        payload=payload,
        memory=memory,
        episode=episode,
        operation="supersede" if conflicts else "create",
    )
    candidate.proposed_value = {
        **dict(candidate.proposed_value or {}),
        "fact_id": str(fact.id),
        "fact_revision_id": str(revision.id),
        "approved_at": now.isoformat(),
    }
    _persist_profile_snapshot(
        db,
        user_id=memory.user_id,
        persona_id=memory.persona_id,
        profile_snapshot=build_memory_profile(db, user_id=memory.user_id, persona_id=memory.persona_id),
    )


def _reject_memory_candidate(db: Session, candidate: MemoryCandidate, *, status: str = "rejected") -> None:
    now = datetime.now(timezone.utc)
    candidate.status = status
    candidate.processed_at = now
    memory = _candidate_memory(db, candidate)
    if memory is None:
        return
    if candidate.proposed_value.get("fact_id"):
        return
    memory.details = {
        **dict(memory.details or {}),
        "state": "ignored",
        "current_version": False,
        "fact_write_gated": True,
        "review_status": status,
        "reviewed_candidate_id": str(candidate.id),
    }
    _sync_memory_scores(memory)


def write_memory(db: Session, payload: MemoryCreate) -> Memory:
    payload.metadata.setdefault("source", payload.metadata.get("origin", "manual"))
    payload.metadata.setdefault("memory_label", "session")
    payload.metadata.setdefault("state", "active")
    payload.metadata.setdefault("pinned", False)
    payload.metadata.setdefault("current_version", True)
    payload.metadata.setdefault("write_strategy", _write_strategy(_memory_label(payload)))
    payload.metadata.setdefault("dedupe_key", _build_dedupe_key(payload.content))
    payload.metadata.setdefault("fact_key", _extract_fact_key(payload.content, label=_memory_label(payload)))
    payload.metadata.setdefault("polarity", _infer_polarity(payload.content))
    payload.metadata.setdefault("reinforcement_count", 1)
    payload.metadata.setdefault("duplicate_count", 1)
    payload.metadata.setdefault("memory_bucket", _memory_bucket(payload))
    episode = _append_memory_episode(db, payload)
    fact_write_gated = _should_gate_fact_write(payload)

    if _should_skip_memory_write(payload):
        skip_hash = _hash_content(payload.content)
        skipped = db.scalar(
            select(Memory).where(
                Memory.user_id == payload.user_id,
                Memory.memory_type == payload.memory_type,
                Memory.content_hash == skip_hash,
            )
        )
        if skipped:
            return skipped
        memory = Memory(
            user_id=payload.user_id,
            persona_id=payload.persona_id,
            conversation_id=payload.conversation_id,
            source_message_id=payload.source_message_id,
            memory_type=payload.memory_type,
            content=payload.content,
            content_hash=skip_hash,
            embedding_model="hash-embedding-v1",
            vector_id="pending",
            importance_score=payload.importance_score,
            confidence_score=payload.confidence_score,
            details={**payload.metadata, "state": "ignored", "write_skipped": True},
        )
        db.add(memory)
        db.flush()
        memory.vector_id = str(memory.id)
        _sync_memory_scores(memory)
        _upsert_memory_candidate(db, payload=payload, memory=memory, episode=episode, fact=None, revision=None)
        db.commit()
        db.refresh(memory)
        return memory

    content_hash = _hash_content(payload.content)
    existing = _find_near_duplicate(db, payload, content_hash)
    if existing:
        reinforcement_count = int(existing.details.get("reinforcement_count", existing.details.get("duplicate_count", 1))) + 1
        existing.importance_score = min(0.99, max(existing.importance_score, payload.importance_score) + 0.04)
        existing.confidence_score = min(0.99, max(existing.confidence_score, payload.confidence_score) + 0.03)
        existing.last_accessed_at = datetime.now(timezone.utc)
        existing_has_fact = bool(existing.details.get("fact_id"))
        existing.details = {
            **existing.details,
            **payload.metadata,
            "deduplicated": True,
            "duplicate_count": int(existing.details.get("duplicate_count", 1)) + 1,
            "reinforcement_count": reinforcement_count,
            "current_version": False if fact_write_gated and not existing_has_fact else True,
            "state": "pending_review" if fact_write_gated and not existing_has_fact else _memory_state(existing.details),
            "fact_write_gated": bool(fact_write_gated and not existing_has_fact),
        }
        _sync_memory_scores(existing)
        if fact_write_gated and not existing_has_fact:
            _upsert_memory_candidate(
                db,
                payload=payload,
                memory=existing,
                episode=episode,
                fact=None,
                revision=None,
            )
            db.commit()
            db.refresh(existing)
            return existing

        fact, revision = _upsert_memory_fact(
            db,
            payload=payload,
            memory=existing,
            episode=episode,
            operation="reinforce",
        )
        _upsert_memory_candidate(
            db,
            payload=payload,
            memory=existing,
            episode=episode,
            fact=fact,
            revision=revision,
        )
        _persist_profile_snapshot(
            db,
            user_id=payload.user_id,
            persona_id=payload.persona_id,
            profile_snapshot=build_memory_profile(db, user_id=payload.user_id, persona_id=payload.persona_id),
        )
        db.commit()
        db.refresh(existing)
        return existing

    conflicting_candidates = _find_conflicting_candidates(db, payload)
    memory = Memory(
        user_id=payload.user_id,
        persona_id=payload.persona_id,
        conversation_id=payload.conversation_id,
        source_message_id=payload.source_message_id,
        memory_type=payload.memory_type,
        content=payload.content,
        content_hash=content_hash,
        embedding_model="hash-embedding-v1",
        vector_id="pending",
        importance_score=payload.importance_score,
        confidence_score=payload.confidence_score,
        details=payload.metadata,
    )
    db.add(memory)
    db.flush()
    memory.vector_id = str(memory.id)

    if fact_write_gated:
        memory.details = {
            **memory.details,
            "state": "pending_review",
            "current_version": False,
            "fact_write_gated": True,
        }
    else:
        _mark_conflicting_memories(memory=memory, conflicts=conflicting_candidates)

    vector = embedding_provider.embed(memory.content)
    vector_index.upsert(
        memory_id=str(memory.id),
        vector=vector,
        payload={
            "user_id": str(memory.user_id),
            "persona_id": str(memory.persona_id) if memory.persona_id else None,
            "memory_type": memory.memory_type.value,
            "memory_label": memory.details.get("memory_label"),
            "fact_key": memory.details.get("fact_key"),
        },
    )
    _sync_memory_scores(memory)
    if fact_write_gated:
        _upsert_memory_candidate(
            db,
            payload=payload,
            memory=memory,
            episode=episode,
            fact=None,
            revision=None,
        )
        db.commit()
        db.refresh(memory)
        return memory

    fact, revision = _upsert_memory_fact(
        db,
        payload=payload,
        memory=memory,
        episode=episode,
        operation="supersede" if conflicting_candidates else "create",
    )
    _upsert_memory_candidate(
        db,
        payload=payload,
        memory=memory,
        episode=episode,
        fact=fact,
        revision=revision,
    )
    _persist_profile_snapshot(
        db,
        user_id=payload.user_id,
        persona_id=payload.persona_id,
        profile_snapshot=build_memory_profile(db, user_id=payload.user_id, persona_id=payload.persona_id),
    )
    db.commit()
    db.refresh(memory)
    return memory


def list_memory_candidates(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 50,
) -> list[MemoryCandidate]:
    statement = select(MemoryCandidate)
    if status:
        statement = statement.where(MemoryCandidate.status == status)
    statement = statement.order_by(desc(MemoryCandidate.created_at)).limit(max(1, min(limit, 200)))
    return db.scalars(statement).all()


def update_memory_candidate(
    db: Session,
    candidate_id: str,
    *,
    proposed_action: str | None = None,
    salience_score: float | None = None,
    confidence_score: float | None = None,
    sensitivity: str | None = None,
    reason_codes: list[Any] | None = None,
    auto_commit: bool | None = None,
    status: str | None = None,
    reviewer_type: str | None = None,
) -> MemoryCandidate:
    candidate = db.scalar(select(MemoryCandidate).where(MemoryCandidate.id == UUID(candidate_id)))
    if candidate is None:
        raise ValueError("Memory candidate not found")

    if proposed_action is not None:
        candidate.proposed_action = proposed_action
    if salience_score is not None:
        candidate.salience_score = salience_score
    if confidence_score is not None:
        candidate.confidence_score = confidence_score
    if sensitivity is not None:
        candidate.sensitivity = sensitivity
    if reason_codes is not None:
        candidate.reason_codes = reason_codes
    if auto_commit is not None:
        candidate.auto_commit = auto_commit
    if reviewer_type is not None:
        candidate.reviewer_type = reviewer_type
    if status == "approved":
        _approve_memory_candidate(db, candidate)
    elif status in {"rejected", "ignored"}:
        _reject_memory_candidate(db, candidate, status=status)
    elif status is not None:
        candidate.status = status

    db.commit()
    db.refresh(candidate)
    return candidate


def _fact_decay_amount(fact: MemoryFact, *, now: datetime) -> float:
    policy = str(fact.decay_policy or "default").strip().lower()
    rate = DECAY_POLICY_RATES.get(policy, DECAY_POLICY_RATES["default"])
    if rate <= 0:
        return 0.0

    anchor = (
        _aware_datetime(fact.last_used_at)
        or _aware_datetime(fact.last_confirmed_at)
        or _aware_datetime(fact.updated_at)
        or _aware_datetime(fact.created_at)
        or now
    )
    age_days = max((now - anchor).total_seconds() / 86400, 0)
    grace_days = DECAY_POLICY_GRACE_DAYS.get(policy, DECAY_POLICY_GRACE_DAYS["default"])
    active_days = max(age_days - grace_days, 0)
    if active_days <= 0:
        return 0.0

    reinforcement_slowdown = 1 + min(int(fact.reinforcement_count or 0), 12) * 0.25
    return min(0.45, (active_days * rate) / reinforcement_slowdown)


def _mark_fact_archived(db: Session, fact: MemoryFact, *, now: datetime, reason: str) -> None:
    fact.status = "archived"
    fact.effective_to = now
    fact.details = {
        **dict(fact.details or {}),
        "archived_by": "memory_maintenance",
        "archive_reason": reason,
        "archived_at": now.isoformat(),
    }
    if fact.current_revision_id:
        revision = db.scalar(select(MemoryRevision).where(MemoryRevision.id == fact.current_revision_id))
        if revision and revision.valid_to is None:
            revision.valid_to = now

    memory = _memory_row_for_fact(db, fact)
    if memory is not None:
        memory.details = {
            **dict(memory.details or {}),
            "state": "archived",
            "current_version": False,
            "archived_by": "memory_maintenance",
            "archive_reason": reason,
        }
        _sync_memory_scores(memory)


def _affected_profile_keys_for_facts(facts: list[MemoryFact]) -> set[tuple[UUID, UUID | None]]:
    return {(fact.user_id, fact.persona_id) for fact in facts}


def _rebuild_profiles_for_keys(db: Session, keys: set[tuple[UUID, UUID | None]]) -> int:
    rebuilt = 0
    for user_id, persona_id in sorted(keys, key=lambda item: (str(item[0]), str(item[1] or ""))):
        _persist_profile_snapshot(
            db,
            user_id=user_id,
            persona_id=persona_id,
            profile_snapshot=build_memory_profile(db, user_id=user_id, persona_id=persona_id),
        )
        rebuilt += 1
    return rebuilt


def run_memory_maintenance(
    db: Session,
    *,
    now: datetime | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    run_at = now or datetime.now(timezone.utc)
    run_at = _aware_datetime(run_at) or datetime.now(timezone.utc)
    report: dict[str, Any] = {
        "run_at": run_at.isoformat(),
        "dry_run": dry_run,
        "facts_scanned": 0,
        "facts_decayed": 0,
        "facts_archived": 0,
        "candidates_scanned": 0,
        "candidates_ignored": 0,
        "profiles_rebuilt": 0,
        "decayed_fact_ids": [],
        "archived_fact_ids": [],
        "ignored_candidate_ids": [],
    }
    changed_facts: list[MemoryFact] = []

    active_facts = db.scalars(
        select(MemoryFact).where(MemoryFact.status == "active").order_by(desc(MemoryFact.updated_at))
    ).all()
    report["facts_scanned"] = len(active_facts)
    for fact in active_facts:
        decay_amount = _fact_decay_amount(fact, now=run_at)
        if decay_amount <= 0:
            continue

        report["facts_decayed"] += 1
        report["decayed_fact_ids"].append(str(fact.id))
        changed_facts.append(fact)
        if dry_run:
            continue

        fact.stability_score = round(max(0.0, fact.stability_score - decay_amount), 4)
        fact.confidence = round(max(0.0, fact.confidence - decay_amount * 0.35), 4)
        if fact.decay_policy in {"session", "volatile"}:
            fact.importance = round(max(0.0, fact.importance - decay_amount * 0.25), 4)
        fact.details = {
            **dict(fact.details or {}),
            "last_decay_at": run_at.isoformat(),
            "last_decay_amount": round(decay_amount, 4),
            "maintenance_policy": fact.decay_policy,
        }
        if (
            fact.stability_score <= FACT_ARCHIVE_STABILITY_THRESHOLD
            and fact.importance <= FACT_ARCHIVE_IMPORTANCE_THRESHOLD
        ):
            _mark_fact_archived(db, fact, now=run_at, reason="decayed_below_threshold")
            report["facts_archived"] += 1
            report["archived_fact_ids"].append(str(fact.id))

    cutoff = run_at - timedelta(days=STALE_CANDIDATE_DAYS)
    pending_candidates = db.scalars(
        select(MemoryCandidate)
        .where(MemoryCandidate.status == "pending")
        .order_by(desc(MemoryCandidate.created_at))
    ).all()
    report["candidates_scanned"] = len(pending_candidates)
    for candidate in pending_candidates:
        created_at = _aware_datetime(candidate.created_at)
        if created_at is None or created_at > cutoff:
            continue

        report["candidates_ignored"] += 1
        report["ignored_candidate_ids"].append(str(candidate.id))
        if dry_run:
            continue

        _reject_memory_candidate(db, candidate, status="ignored")
        candidate.reason_codes = [
            *[str(item) for item in candidate.reason_codes or []],
            "maintenance_stale_candidate",
        ]

    affected_keys = _affected_profile_keys_for_facts(changed_facts)
    if not dry_run and affected_keys:
        report["profiles_rebuilt"] = _rebuild_profiles_for_keys(db, affected_keys)
        db.commit()
    elif dry_run:
        db.rollback()
    else:
        db.commit()

    return report


def search_memories(
    db: Session,
    *,
    user_id: str,
    query: str,
    persona_id: str | None = None,
    memory_types: list[MemoryType] | None = None,
    limit: int = 5,
) -> list[Memory]:
    route = classify_memory_query(query)
    vector = embedding_provider.embed(query)
    ids = vector_index.search(vector=vector, user_id=user_id, persona_id=persona_id, limit=limit)
    allowed = {memory_type.value for memory_type in memory_types} if memory_types else None

    rows: list[Memory] = []
    if ids:
        for item in ids:
            try:
                memory_id = UUID(item)
            except ValueError:
                continue
            row = db.scalar(select(Memory).where(Memory.id == memory_id))
            if row:
                rows.append(row)
    else:
        query_tokens = set(tokenize(query))
        statement = (
            select(Memory)
            .where(Memory.user_id == UUID(user_id))
            .order_by(desc(Memory.updated_at))
            .limit(50)
        )
        if persona_id:
            statement = statement.where(Memory.persona_id == UUID(persona_id))
        if memory_types:
            statement = statement.where(Memory.memory_type.in_(memory_types))
        rows = db.scalars(statement).all()

    user_uuid = UUID(user_id)
    persona_uuid = UUID(persona_id) if persona_id else None
    fact_seed_rows: list[Memory] = []
    if route == "profile":
        fact_seed_rows = _fact_backed_memories(
            db,
            user_id=user_uuid,
            persona_id=persona_uuid,
            fact_types=("preference", "identity"),
            limit=limit,
        )
    elif route == "instruction":
        fact_seed_rows = _fact_backed_memories(
            db,
            user_id=user_uuid,
            persona_id=persona_uuid,
            fact_types=("instruction",),
            limit=limit,
        )
    elif route == "episodic":
        statement = (
            select(Memory)
            .where(Memory.user_id == user_uuid)
            .order_by(desc(Memory.updated_at))
            .limit(max(limit * 2, 10))
        )
        if persona_uuid:
            statement = statement.where(Memory.persona_id == persona_uuid)
        episodic_rows = db.scalars(statement).all()
        fact_seed_rows = [item for item in episodic_rows if _memory_label(item) == "episodic"][:limit]

    if fact_seed_rows:
        merged_rows: dict[str, Memory] = {str(item.id): item for item in fact_seed_rows}
        for row in rows:
            merged_rows.setdefault(str(row.id), row)
        rows = list(merged_rows.values())

    query_tokens = set(tokenize(query))
    candidates = [item for item in rows if _is_searchable_memory(item)]
    if allowed:
        candidates = [item for item in candidates if item.memory_type.value in allowed]

    ordered = sorted(
        candidates,
        key=lambda item: (
            1 if route == "profile" and _memory_label(item) == "preference" else 0,
            1 if route == "instruction" and _memory_label(item) == "instruction" else 0,
            1 if route == "episodic" and _memory_label(item) == "episodic" else 0,
            1 if item.details.get("pinned") else 0,
            1 if item.details.get("current_version", True) else 0,
            len(query_tokens.intersection(tokenize(item.content))),
            _memory_strength(item),
            item.updated_at,
        ),
        reverse=True,
    )[:limit]

    now = datetime.now(timezone.utc)
    for memory in ordered:
        memory.access_count += 1
        memory.last_accessed_at = now
        _sync_memory_scores(memory)
    if ordered:
        db.commit()
    return ordered


def update_memory(db: Session, memory_id: str, payload: MemoryUpdate) -> Memory:
    memory = db.scalar(select(Memory).where(Memory.id == UUID(memory_id)))
    if not memory:
        raise ValueError("Memory not found")

    if payload.importance_score is not None:
        memory.importance_score = payload.importance_score
    if payload.confidence_score is not None:
        memory.confidence_score = payload.confidence_score
    if payload.metadata is not None:
        memory.details = {
            **memory.details,
            **payload.metadata,
        }

    _sync_memory_scores(memory)
    _persist_profile_snapshot(
        db,
        user_id=memory.user_id,
        persona_id=memory.persona_id,
        profile_snapshot=build_memory_profile(db, user_id=memory.user_id, persona_id=memory.persona_id),
    )
    db.commit()
    db.refresh(memory)
    return memory


def debug_memory_state(db: Session) -> MemoryDebugResponse:
    recent = db.scalars(select(Memory).order_by(desc(Memory.created_at)).limit(10)).all()
    recent_episodes = db.scalars(select(MemoryEpisode).order_by(desc(MemoryEpisode.created_at)).limit(10)).all()
    recent_facts = db.scalars(select(MemoryFact).order_by(desc(MemoryFact.updated_at)).limit(10)).all()
    recent_revisions = db.scalars(
        select(MemoryRevision).order_by(desc(MemoryRevision.created_at)).limit(10)
    ).all()
    recent_candidates = db.scalars(
        select(MemoryCandidate).order_by(desc(MemoryCandidate.created_at)).limit(10)
    ).all()
    total = db.scalar(select(func.count()).select_from(Memory)) or 0
    total_episodes = db.scalar(select(func.count()).select_from(MemoryEpisode)) or 0
    total_facts = db.scalar(select(func.count()).select_from(MemoryFact)) or 0
    total_revisions = db.scalar(select(func.count()).select_from(MemoryRevision)) or 0
    candidate_counts = {
        "pending": 0,
        "approved": 0,
        "rejected": 0,
        "ignored": 0,
    }

    profile_snapshot: dict[str, Any] = {}
    user_profile_snapshot: dict[str, Any] = {}
    relationship_state_snapshot: dict[str, Any] = {}
    anchor_user_id: UUID | None = None
    anchor_persona_id: UUID | None = None
    if recent:
        anchor_user_id = recent[0].user_id
        anchor_persona_id = recent[0].persona_id
    elif recent_facts:
        anchor_user_id = recent_facts[0].user_id
        anchor_persona_id = recent_facts[0].persona_id

    if anchor_user_id is not None:
        profile_snapshot = build_memory_profile(
            db,
            user_id=anchor_user_id,
            persona_id=anchor_persona_id,
        )
        user_profile_snapshot = _serialize_user_profile(
            db.scalar(select(UserProfile).where(UserProfile.user_id == anchor_user_id))
        )
        if anchor_persona_id is not None:
            relationship_state_snapshot = _serialize_relationship_state(
                db.scalar(
                    select(RelationshipState).where(
                        RelationshipState.user_id == anchor_user_id,
                        RelationshipState.persona_id == anchor_persona_id,
                    )
                )
            )

    lifecycle_counts = {
        "active": 0,
        "pinned": 0,
        "archived": 0,
        "ignored": 0,
        "superseded": 0,
    }
    conflict_map: dict[str, list[Memory]] = {}
    all_rows = db.scalars(select(Memory).order_by(desc(Memory.updated_at))).all()
    for memory in all_rows:
        state = _memory_state(memory.details)
        lifecycle_counts[state] = lifecycle_counts.get(state, 0) + 1
        if not memory.details.get("current_version", True):
            lifecycle_counts["superseded"] += 1
        conflict_group = str(memory.details.get("conflict_group", "")).strip()
        if conflict_group:
            conflict_map.setdefault(conflict_group, []).append(memory)

    for candidate in db.scalars(select(MemoryCandidate)).all():
        candidate_counts[candidate.status] = candidate_counts.get(candidate.status, 0) + 1

    conflict_groups = [
        {
            "group_id": group_id,
            "fact_key": str(group[0].details.get("fact_key", "")),
            "items": [
                {
                    "id": str(item.id),
                    "content": item.content,
                    "state": _memory_state(item.details),
                    "current_version": bool(item.details.get("current_version", True)),
                    "polarity": item.details.get("polarity"),
                }
                for item in sorted(group, key=lambda row: row.updated_at, reverse=True)
            ],
        }
        for group_id, group in conflict_map.items()
        if len(group) > 1
    ]

    return MemoryDebugResponse(
        qdrant_available=vector_index.ensure_collection(),
        collection_name=settings.qdrant_collection,
        total_memories=total,
        total_episodes=total_episodes,
        total_facts=total_facts,
        total_revisions=total_revisions,
        candidate_counts=candidate_counts,
        recent_memories=recent,
        recent_episodes=recent_episodes,
        recent_facts=recent_facts,
        recent_revisions=recent_revisions,
        recent_candidates=recent_candidates,
        profile_summary=str(profile_snapshot.get("summary_text", "")),
        profile_snapshot=profile_snapshot,
        user_profile_snapshot=user_profile_snapshot,
        relationship_state_snapshot=relationship_state_snapshot,
        conflict_groups=conflict_groups,
        lifecycle_counts=lifecycle_counts,
    )
