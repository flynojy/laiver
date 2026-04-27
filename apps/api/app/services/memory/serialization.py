from typing import Any

from app.models.relationship_state import RelationshipState
from app.models.user_profile import UserProfile


def serialize_user_profile(profile: UserProfile | None) -> dict[str, Any]:
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


def serialize_relationship_state(state: RelationshipState | None) -> dict[str, Any]:
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
            state.last_meaningful_interaction_at.isoformat()
            if state.last_meaningful_interaction_at
            else None
        ),
        "last_repair_at": state.last_repair_at.isoformat() if state.last_repair_at else None,
        "summary": state.summary,
        "version": state.version,
    }
