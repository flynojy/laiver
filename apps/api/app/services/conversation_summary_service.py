from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import MessageRole
from app.models.conversation import Conversation, Message
from app.utils.text import normalize_whitespace

SUMMARY_TRIGGER_MESSAGES = 8
SUMMARY_RECENT_WINDOW = 6
SUMMARY_MAX_LINES = 6


@dataclass
class ConversationCompressionContext:
    summary_text: str | None
    recent_messages: list[Message]
    compression_active: bool
    summarized_message_count: int
    recent_message_count: int


def _compact_text(content: str, limit: int = 140) -> str:
    text = normalize_whitespace(content)
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."


def _salience_score(message: Message) -> tuple[int, int]:
    content = message.content.lower()
    score = 0
    if message.role == MessageRole.USER:
        score += 3
    if any(token in content for token in ("remember", "prefer", "always", "todo", "task", "must", "need")):
        score += 4
    if any(token in content for token in ("milestone", "decision", "plan", "summary", "next step")):
        score += 2
    return score, message.sequence_index


def _line_for_message(message: Message) -> str:
    role = "User" if message.role == MessageRole.USER else "Assistant"
    return f"{role}: {_compact_text(message.content)}"


def build_conversation_compression(
    messages: list[Message],
    *,
    existing_summary: str | None = None,
    trigger_count: int = SUMMARY_TRIGGER_MESSAGES,
    recent_window: int = SUMMARY_RECENT_WINDOW,
) -> ConversationCompressionContext:
    if len(messages) <= trigger_count:
        return ConversationCompressionContext(
            summary_text=existing_summary,
            recent_messages=messages,
            compression_active=False,
            summarized_message_count=0,
            recent_message_count=len(messages),
        )

    split_index = max(len(messages) - recent_window, 0)
    older_messages = messages[:split_index]
    recent_messages = messages[split_index:]
    ranked = sorted(older_messages, key=_salience_score, reverse=True)

    selected: list[Message] = []
    seen_content: set[str] = set()
    for message in ranked:
        compact = _compact_text(message.content)
        if compact in seen_content:
            continue
        selected.append(message)
        seen_content.add(compact)
        if len(selected) >= SUMMARY_MAX_LINES:
            break

    selected.sort(key=lambda item: item.sequence_index)
    lines = [_line_for_message(message) for message in selected]
    if existing_summary and existing_summary.strip():
        lines.insert(0, f"Previous summary: {_compact_text(existing_summary, limit=220)}")

    summary_text = "Earlier conversation summary:\n" + "\n".join(f"- {line}" for line in lines)
    return ConversationCompressionContext(
        summary_text=summary_text,
        recent_messages=recent_messages,
        compression_active=True,
        summarized_message_count=len(older_messages),
        recent_message_count=len(recent_messages),
    )


def apply_compression_to_conversation(conversation: Conversation, context: ConversationCompressionContext) -> None:
    conversation.summary = context.summary_text if context.compression_active else None
    conversation.context = {
        **(conversation.context or {}),
        "summary_meta": {
            "compression_active": context.compression_active,
            "summarized_message_count": context.summarized_message_count,
            "recent_message_count": context.recent_message_count,
        },
    }
