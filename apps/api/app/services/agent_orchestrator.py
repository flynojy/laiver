from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import MessageRole
from app.models.conversation import Conversation, Message
from app.models.user import Persona
from app.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    AgentDebugInfo,
    AnswerExplanation,
    ConversationControls,
)
from app.schemas.memory import MemoryCreate
from app.schemas.runtime import ModelCompletionRequest, ModelMessage
from app.services.conversation_summary_service import (
    apply_compression_to_conversation,
    build_conversation_compression,
)
from app.services.memory_service import (
    build_memory_profile,
    classify_memory_query,
    infer_memory_profile,
    search_memories,
    write_memory,
)
from app.services.model_router import ModelRouterService, build_tool_message
from app.services.skill_runtime import SkillExecutionResult, skill_runtime


def _build_conversation_title(content: str) -> str:
    compact = " ".join(content.strip().split())
    return compact[:48] or "New Conversation"


def _persona_fields_used(persona: Persona | None) -> list[str]:
    if not persona:
        return []

    fields = ["tone", "verbosity", "response_style", "relationship_style"]
    if persona.description:
        fields.append("description")
    if persona.common_topics:
        fields.append("common_topics")
    if persona.common_phrases:
        fields.append("common_phrases")
    return fields


def _build_system_prompt(persona: Persona | None, memories: list, skills: list[str]) -> str:
    persona_section = (
        f"Persona name: {persona.name}\n"
        f"Description: {persona.description or 'No extra description'}\n"
        f"Tone: {persona.tone}\n"
        f"Verbosity: {persona.verbosity}\n"
        f"Common topics: {', '.join(persona.common_topics)}\n"
        f"Common phrases: {', '.join(persona.common_phrases)}\n"
        f"Response style: {persona.response_style}\n"
        f"Relationship style: {persona.relationship_style}\n"
        "Apply the tone, verbosity, common topics, common phrases, response style, and relationship style directly in the answer.\n"
        if persona
        else "No explicit persona configured. Be helpful, structured, and concise.\n"
    )
    memory_section = "\n".join(f"- [{item.memory_type.value}] {item.content}" for item in memories) or "- None"
    skill_section = ", ".join(skills) or "none"
    return (
        "You are the core orchestrated personal agent.\n"
        f"{persona_section}\n"
        f"Relevant memories:\n{memory_section}\n\n"
        f"Available skills: {skill_section}\n"
        "When skill results are provided, explicitly use them in your final answer."
    )


def _build_memory_profile_message(profile_summary: str | None) -> ModelMessage | None:
    if not profile_summary:
        return None
    return ModelMessage(
        role="system",
        content=(
            "Long-term memory profile:\n"
            f"{profile_summary}\n"
            "Prefer the latest stable instruction or preference when older memories conflict."
        ),
    )


def _build_skill_grounding_message(executions: list[SkillExecutionResult]) -> ModelMessage | None:
    if not executions:
        return None

    lines = [
        "Skill grounding context:",
        "Use the following verified tool outputs directly when they are relevant.",
    ]
    for execution in executions:
        if execution.error:
            lines.append(f"- {execution.skill.slug} failed: {execution.error}")
            continue
        for item in skill_runtime.summarize_execution(execution):
            lines.append(f"- {item}")
    return ModelMessage(role="system", content="\n".join(lines))


def _uses_handler(execution: SkillExecutionResult, handler_slug: str) -> bool:
    return skill_runtime.handler_slug_for_skill(execution.skill) == handler_slug


def _build_conversation_summary_message(summary_text: str | None, summarized_message_count: int) -> ModelMessage | None:
    if not summary_text:
        return None
    return ModelMessage(
        role="system",
        content=(
            f"Long-horizon conversation summary for {summarized_message_count} earlier messages:\n"
            f"{summary_text}"
        ),
    )


def _build_mock_grounded_response(
    *,
    message: str,
    executions: list[SkillExecutionResult],
    persona: Persona | None,
    conversation_summary: str | None = None,
) -> tuple[str, str]:
    sections: list[str] = []
    fallback_status = "mock_provider_default"

    memory_execution = next((item for item in executions if _uses_handler(item, "memory-search") and item.success), None)
    if memory_execution:
        matches = memory_execution.output.get("matches", [])
        if matches:
            fallback_status = "mock_provider_grounded"
            sections.append("Based on related memory, here is the most relevant preference I found:")
            for match in matches[:2]:
                content = str(match.get("content", "")).strip()
                if content:
                    sections.append(f"- {content}")

    task_execution = next((item for item in executions if _uses_handler(item, "task-extractor") and item.success), None)
    if task_execution:
        tasks = task_execution.output.get("tasks", [])
        if tasks:
            fallback_status = "mock_provider_grounded"
            sections.append("Structured action items:")
            for index, task in enumerate(tasks[:5], start=1):
                title = str(task.get("title", "Untitled task")).strip()
                priority = str(task.get("priority", "low")).strip()
                summary = str(task.get("summary", "")).strip()
                sections.append(f"{index}. {title} [{priority}]")
                if summary and summary != title:
                    sections.append(f"   {summary}")

    failed = [item for item in executions if item.error]
    if failed:
        fallback_status = "skill_error_fallback"
        sections.append("One or more skills failed, so I used the available grounded context and a safe fallback response.")
        for item in failed:
            sections.append(f"- {item.skill.slug}: {item.error}")

    if conversation_summary and not sections:
        fallback_status = "mock_provider_compressed_context"
        sections.append("Long-horizon conversation summary:")
        sections.append(conversation_summary)

    if not sections:
        tone = persona.tone if persona else "clear and supportive"
        verbosity = persona.verbosity if persona else "concise"
        if verbosity == "detailed":
            sections.append(f"I'll answer in a {tone} and more detailed way.")
            sections.append("Mock mode is active, so this response uses local fallback behavior rather than a live model completion.")
            sections.append("I will keep the structure explicit and expand the reasoning where it helps.")
        else:
            sections.append(f"I'll keep this {tone} and concise.")
            sections.append("Mock mode is active, so this response uses local fallback behavior rather than a live model completion.")
        if persona and persona.common_topics:
            sections.append(f"Current persona focus: {', '.join(persona.common_topics[:3])}.")
        if persona and persona.common_phrases:
            sections.append(f"Signature phrasing to keep in view: {persona.common_phrases[0]}")
        sections.append(f"I will use the current conversation context and stay aligned with the request: {message}")
    elif persona:
        if persona.verbosity == "detailed":
            sections.append(f"I'll keep the tone {persona.tone} and add detail where it improves clarity.")
        else:
            sections.append(f"I'll keep the tone {persona.tone} and stay concise.")
        if persona.common_phrases:
            sections.append(f"Preferred phrasing cue: {persona.common_phrases[0]}")

    return "\n".join(sections), fallback_status


def _merge_controls(payload: AgentChatRequest, conversation: Conversation) -> ConversationControls:
    stored_controls = ConversationControls.model_validate((conversation.context or {}).get("controls", {}))
    return stored_controls.model_copy(
        update=payload.controls.model_dump(exclude_none=True) if payload.controls else {}
    )


def _counted_memories(*items) -> list:
    return [
        item
        for item in items
        if item is not None
        and not item.details.get("write_skipped")
        and str(item.details.get("state", "active")) != "ignored"
    ]


async def respond(db: Session, payload: AgentChatRequest) -> AgentChatResponse:
    trace_id = str(uuid4())
    conversation = None
    if payload.conversation_id:
        conversation = db.scalar(select(Conversation).where(Conversation.id == payload.conversation_id))
    if not conversation:
        conversation = Conversation(
            user_id=payload.user_id,
            persona_id=payload.persona_id,
            title=_build_conversation_title(payload.message),
            channel="web",
            context={"controls": payload.controls.model_dump() if payload.controls else {}},
        )
        db.add(conversation)
        db.flush()

    merged_controls = _merge_controls(payload, conversation)
    conversation.context = {
        **(conversation.context or {}),
        "controls": merged_controls.model_dump(),
    }

    if payload.persona_id and payload.persona_id != conversation.persona_id:
        conversation.persona_id = payload.persona_id

    existing_messages = db.scalars(
        select(Message).where(Message.conversation_id == conversation.id).order_by(Message.sequence_index)
    ).all()
    next_index = len(existing_messages)

    user_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=payload.message,
        sequence_index=next_index,
        context={"trace_id": trace_id},
    )
    db.add(user_message)
    db.flush()

    persona = None
    if payload.persona_id or conversation.persona_id:
        persona = db.scalar(select(Persona).where(Persona.id == (payload.persona_id or conversation.persona_id)))

    memory_query_route = classify_memory_query(payload.message)
    memories = search_memories(
        db,
        user_id=str(payload.user_id),
        persona_id=str(payload.persona_id or conversation.persona_id)
        if payload.persona_id or conversation.persona_id
        else None,
        query=payload.message,
        limit=5,
    )
    memory_profile = build_memory_profile(
        db,
        user_id=payload.user_id,
        persona_id=payload.persona_id or conversation.persona_id,
    )

    pre_prompt_compression = build_conversation_compression(
        existing_messages + [user_message],
        existing_summary=conversation.summary,
    )

    tool_definitions = skill_runtime.tool_definitions(db) if merged_controls.skills_enabled else []
    system_prompt = _build_system_prompt(persona, memories, [item.function["name"] for item in tool_definitions])
    prompt_messages = [ModelMessage(role="system", content=system_prompt)]
    memory_profile_message = _build_memory_profile_message(memory_profile.get("summary_text"))
    if memory_profile_message:
        prompt_messages.append(memory_profile_message)
    conversation_summary_message = _build_conversation_summary_message(
        pre_prompt_compression.summary_text,
        pre_prompt_compression.summarized_message_count,
    )
    if conversation_summary_message:
        prompt_messages.append(conversation_summary_message)
    history_messages = pre_prompt_compression.recent_messages
    prompt_messages.extend(
        [ModelMessage(role=item.role.value, content=item.content) for item in history_messages]
    )

    router = ModelRouterService(db)
    skills_used: list[str] = []
    executions: list[SkillExecutionResult] = []
    precomputed_tool_messages: list[ModelMessage] = []
    planned_skill_calls = (
        skill_runtime.plan_invocations(
            db,
            payload.message,
            context={
                "user_id": payload.user_id,
                "persona_id": payload.persona_id or conversation.persona_id,
                "recent_messages": history_messages,
                "memory_hits": memories,
            },
        )
        if merged_controls.skills_enabled
        else []
    )

    for planned_call in planned_skill_calls:
        execution = await skill_runtime.execute(
            name=planned_call.tool_name,
            arguments=planned_call.arguments,
            context={
                "user_id": payload.user_id,
                "persona_id": payload.persona_id or conversation.persona_id,
                "recent_messages": history_messages,
                "memory_hits": memories,
            },
            db=db,
            trace_id=trace_id,
            conversation_id=conversation.id,
            message_id=user_message.id,
            trigger_source=planned_call.trigger_source,
            skill=planned_call.skill,
        )
        executions.append(execution)
        if execution.skill.slug not in skills_used:
            skills_used.append(execution.skill.slug)
        precomputed_tool_messages.append(
            build_tool_message(
                f"planner-{execution.invocation.id}",
                execution.tool_name,
                execution.output if execution.success else {"error": execution.error},
            )
        )

    grounding_message = _build_skill_grounding_message(executions)
    if grounding_message:
        prompt_messages.append(grounding_message)

    completion = await router.complete(
        ModelCompletionRequest(messages=prompt_messages + precomputed_tool_messages, tools=tool_definitions)
    )

    if completion.tool_calls and merged_controls.skills_enabled:
        tool_messages = []
        for tool_call in completion.tool_calls:
            execution = await skill_runtime.execute(
                name=tool_call.name,
                arguments=tool_call.arguments,
                context={
                    "user_id": payload.user_id,
                    "persona_id": payload.persona_id or conversation.persona_id,
                    "recent_messages": history_messages,
                    "memory_hits": memories,
                },
                db=db,
                trace_id=trace_id,
                conversation_id=conversation.id,
                message_id=user_message.id,
                trigger_source="model",
            )
            executions.append(execution)
            if execution.skill.slug not in skills_used:
                skills_used.append(execution.skill.slug)
            tool_messages.append(
                build_tool_message(
                    tool_call.id,
                    execution.tool_name,
                    execution.output if execution.success else {"error": execution.error},
                )
            )

        grounding_message = _build_skill_grounding_message(executions)
        rerun_messages = prompt_messages + precomputed_tool_messages + tool_messages
        if grounding_message:
            rerun_messages = prompt_messages[:-1] + [grounding_message] + precomputed_tool_messages + tool_messages
        completion = await router.complete(
            ModelCompletionRequest(messages=rerun_messages, tools=tool_definitions)
        )

    model_mode = "mock" if completion.finish_reason == "mock" else "live"
    response_content = completion.content
    fallback_status = "not_used"

    if model_mode == "mock":
        response_content, fallback_status = _build_mock_grounded_response(
            message=payload.message,
            executions=executions,
            persona=persona,
            conversation_summary=pre_prompt_compression.summary_text,
        )
    elif any(execution.error for execution in executions):
        fallback_status = "skill_error_notice"
    elif executions:
        fallback_status = "grounded_by_skill_context"

    skill_invocation_reads = [execution.as_read() for execution in executions]
    skill_invocation_summary = [skill_runtime.invocation_summary(execution) for execution in executions]
    skill_output_summary = [
        item
        for execution in executions
        for item in skill_runtime.summarize_execution(execution)
    ]

    assistant_message = Message(
        conversation_id=conversation.id,
        parent_message_id=user_message.id,
        role=MessageRole.ASSISTANT,
        content=response_content,
        model_name=completion.model,
        sequence_index=next_index + 1,
        token_usage=completion.usage,
        context={
            "trace_id": trace_id,
            "provider_name": completion.provider,
            "model_name": completion.model,
            "model_mode": model_mode,
            "skills_used": skills_used,
            "skill_invocation_count": len(skill_invocation_reads),
            "skill_invocation_summary": skill_invocation_summary,
            "skill_output_summary": skill_output_summary,
            "fallback_status": fallback_status,
            "persona_id": str(persona.id) if persona else None,
            "persona_name": persona.name if persona else None,
            "persona_fields_used": _persona_fields_used(persona),
            "skills_enabled": merged_controls.skills_enabled,
            "memory_write_enabled": merged_controls.memory_write_enabled,
            "memory_hit_ids": [str(item.id) for item in memories],
            "memory_query_route": memory_query_route,
        },
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)

    persisted_messages = db.scalars(
        select(Message).where(Message.conversation_id == conversation.id).order_by(Message.sequence_index)
    ).all()
    persisted_compression = build_conversation_compression(
        persisted_messages,
        existing_summary=conversation.summary,
    )
    apply_compression_to_conversation(conversation, persisted_compression)
    db.commit()
    db.refresh(conversation)

    written_memories = []
    if merged_controls.memory_write_enabled:
        user_memory_type, user_label, user_importance, user_confidence = infer_memory_profile(
            payload.message, origin="user_message"
        )
        written_user_memory = write_memory(
            db,
            MemoryCreate(
                user_id=payload.user_id,
                persona_id=payload.persona_id or conversation.persona_id,
                conversation_id=conversation.id,
                source_message_id=user_message.id,
                memory_type=user_memory_type,
                content=payload.message,
                importance_score=user_importance,
                confidence_score=user_confidence,
                metadata={
                    "origin": "user_message",
                    "source": "user_message",
                    "memory_label": user_label,
                    "trace_id": trace_id,
                },
            ),
        )

        assistant_memory_type, assistant_label, assistant_importance, assistant_confidence = infer_memory_profile(
            response_content, origin="assistant_message"
        )
        written_assistant_memory = write_memory(
            db,
            MemoryCreate(
                user_id=payload.user_id,
                persona_id=payload.persona_id or conversation.persona_id,
                conversation_id=conversation.id,
                source_message_id=assistant_message.id,
                memory_type=assistant_memory_type,
                content=response_content,
                importance_score=assistant_importance,
                confidence_score=assistant_confidence,
                metadata={
                    "origin": "assistant_message",
                    "source": "assistant_message",
                    "memory_label": assistant_label,
                    "trace_id": trace_id,
                },
            ),
        )
        written_memories = _counted_memories(written_user_memory, written_assistant_memory)

    assistant_message.context = {
        **assistant_message.context,
        "memory_write_count": len(written_memories),
        "memory_write_ids": [str(item.id) for item in written_memories],
    }
    db.commit()
    db.refresh(assistant_message)

    explanation = AnswerExplanation(
        memories_used=memories if any(_uses_handler(execution, "memory-search") and execution.success for execution in executions) else [],
        persona_fields_used=_persona_fields_used(persona),
        skill_outputs_used=skill_output_summary,
    )

    return AgentChatResponse(
        conversation_id=conversation.id,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
        response=response_content,
        persona=persona,
        debug=AgentDebugInfo(
            trace_id=trace_id,
            provider_name=completion.provider,
            model_name=completion.model,
            model_mode=model_mode,
            persona_id=persona.id if persona else None,
            persona_name=persona.name if persona else None,
            memory_write_count=len(written_memories),
            conversation_summary=pre_prompt_compression.summary_text,
            compression_active=pre_prompt_compression.compression_active,
            summarized_message_count=pre_prompt_compression.summarized_message_count,
            recent_message_count=pre_prompt_compression.recent_message_count,
            memory_query_route=memory_query_route,
            memory_hits=memories,
            memory_writes=written_memories,
            skills_used=skills_used,
            skill_invocations=skill_invocation_reads,
            skill_invocation_summary=skill_invocation_summary,
            skill_output_summary=skill_output_summary,
            skills_enabled=merged_controls.skills_enabled,
            memory_write_enabled=merged_controls.memory_write_enabled,
            explanation=explanation,
            fallback_status=fallback_status,
        ),
    )
