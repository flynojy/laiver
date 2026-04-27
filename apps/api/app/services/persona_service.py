from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.import_job import NormalizedMessage
from app.models.user import Persona
from app.schemas.persona import PersonaCreate, PersonaExtractionRequest
from app.utils.text import (
    extract_keywords,
    extract_phrases,
    infer_relationship_style,
    infer_response_style,
    infer_tone,
    infer_verbosity,
    normalize_whitespace,
)


def _snippet(text: str, limit: int = 160) -> str:
    clean = normalize_whitespace(text)
    return clean if len(clean) <= limit else f"{clean[:limit].rstrip()}..."


def _pick_source_texts(rows: list[NormalizedMessage], fallback: list[str]) -> list[str]:
    user_rows = [row.content for row in rows if getattr(row.role, "value", row.role) == "user"]
    return user_rows or fallback


def _pick_speaker_texts(rows: list[NormalizedMessage], speaker: str) -> list[str]:
    target = normalize_whitespace(speaker)
    if not target:
        return []
    return [
        row.content
        for row in rows
        if normalize_whitespace(getattr(row, "speaker", "")) == target and row.content.strip()
    ]


def _collect_evidence(texts: list[str], topics: list[str], phrases: list[str]) -> dict[str, list[str]]:
    longest = sorted((_snippet(text) for text in texts if text.strip()), key=len, reverse=True)
    topic_samples = [
        _snippet(text)
        for text in texts
        if any(topic in text.lower() for topic in topics[:3])
    ]
    phrase_samples = [
        _snippet(text)
        for text in texts
        if any(phrase in text.lower() for phrase in phrases[:3])
    ]
    tone_samples = [
        _snippet(text)
        for text in texts
        if any(token in text.lower() for token in ("thanks", "thank", "please", "must"))
        or any(token in text for token in ("谢谢", "感谢", "请", "必须"))
    ]
    return {
        "summary": longest[:3],
        "topics": topic_samples[:3] or longest[:2],
        "phrases": phrase_samples[:3] or longest[:2],
        "tone": tone_samples[:3] or longest[:2],
        "verbosity": longest[:3],
    }


def _build_confidence_scores(texts: list[str], topics: list[str], phrases: list[str]) -> dict[str, float]:
    message_count = len(texts)
    avg_length = sum(len(text.split()) for text in texts) / max(message_count, 1)
    return {
        "tone": round(min(0.95, 0.45 + message_count * 0.05), 2),
        "verbosity": round(min(0.95, 0.4 + min(avg_length, 24) / 40), 2),
        "topics": round(min(0.95, 0.35 + len(topics) * 0.07 + message_count * 0.03), 2),
        "phrases": round(min(0.9, 0.25 + len(phrases) * 0.15), 2),
        "overall": round(min(0.95, 0.4 + message_count * 0.05 + len(topics) * 0.03), 2),
    }


def _build_persona_payload(payload: PersonaExtractionRequest, texts: list[str]) -> PersonaCreate:
    common_topics = extract_keywords(texts)
    common_phrases = extract_phrases(texts)
    tone = infer_tone(texts)
    verbosity = infer_verbosity(texts)
    response_style = infer_response_style(texts)
    relationship_style = infer_relationship_style(texts)
    confidence_scores = _build_confidence_scores(texts, common_topics, common_phrases)
    evidence_samples = _collect_evidence(texts, common_topics, common_phrases)
    description = payload.description or (
        f"A {tone} persona with {verbosity} answers, often discussing "
        f"{', '.join(common_topics[:3]) or 'general conversations'}."
    )
    return PersonaCreate(
        user_id=payload.user_id,
        source_import_id=payload.import_id,
        name=payload.name,
        description=description,
        tone=tone,
        verbosity=verbosity,
        common_phrases=common_phrases,
        common_topics=common_topics,
        response_style=response_style,
        relationship_style=relationship_style,
        confidence_scores=confidence_scores,
        evidence_samples=evidence_samples,
        is_default=payload.set_default,
    )


def extract_persona(db: Session, payload: PersonaExtractionRequest) -> tuple[Persona, int]:
    if payload.import_id:
        rows = db.scalars(
            select(NormalizedMessage)
            .where(NormalizedMessage.import_id == payload.import_id)
            .order_by(NormalizedMessage.sequence_index)
        ).all()
        fallback = [row.content for row in rows]
        speaker_texts = _pick_speaker_texts(rows, payload.source_speaker or "")
        texts = speaker_texts or _pick_source_texts(rows, fallback)
        message_count = len(texts)
    else:
        sample_rows = [
            item
            for item in payload.sample_messages
            if item.get("content")
        ]
        if payload.source_speaker:
            texts = [
                str(item.get("content", ""))
                for item in sample_rows
                if normalize_whitespace(str(item.get("speaker", ""))) == normalize_whitespace(payload.source_speaker)
            ]
        else:
            texts = [str(item.get("content", "")) for item in sample_rows]
        message_count = len(texts)

    persona_data = _build_persona_payload(payload, texts or [""])
    if payload.persist:
        if payload.set_default:
            existing_default = db.scalars(
                select(Persona).where(Persona.user_id == payload.user_id, Persona.is_default.is_(True))
            ).all()
            for row in existing_default:
                row.is_default = False

        persona = Persona(**persona_data.model_dump(), extracted_at=datetime.now(timezone.utc))
        db.add(persona)
        db.commit()
        db.refresh(persona)
        return persona, message_count

    persona = Persona(**persona_data.model_dump(), extracted_at=datetime.now(timezone.utc))
    return persona, message_count
