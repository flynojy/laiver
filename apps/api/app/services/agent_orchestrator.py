from __future__ import annotations

import re
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
from app.services.memory.routing import classify_memory_query
from app.services.memory_service import (
    build_memory_profile,
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
            sections.append("我记得和这件事相关的信息：")
            for match in matches[:2]:
                content = str(match.get("content", "")).strip()
                if content:
                    sections.append(f"- {content}")

    task_execution = next((item for item in executions if _uses_handler(item, "task-extractor") and item.success), None)
    if task_execution:
        tasks = task_execution.output.get("tasks", [])
        if tasks:
            fallback_status = "mock_provider_grounded"
            sections.append("我先帮你整理成几个待办：")
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
        sections.append("有些工具调用失败了，所以我先根据当前上下文给你一个保守回复。")
        for item in failed:
            sections.append(f"- {item.skill.slug}: {item.error}")

    if conversation_summary and not sections:
        fallback_status = "mock_provider_compressed_context"
        sections.append("我参考了前面对话摘要：")
        sections.append(conversation_summary)

    if not sections:
        if persona:
            phrases = [item for item in persona.common_phrases[:2] if item]
            if message.strip() in {"你好", "嗨", "hello", "Hello", "hi", "Hi"}:
                greeting = phrases[0] if phrases else "早安"
                sections.append(f"{greeting}。看到你发来消息，我就安心一点。")
                sections.append("今天也想听你多说一点，不管是学校、心情，还是只是想叫我一声。")
            elif persona.verbosity == "detailed":
                sections.append(f"我在听。你刚才说的是：{message}")
                sections.append("我会按我们现在的关系和语气认真回应你，尽量说得清楚一点。")
            else:
                sections.append(f"我在。你刚才说：{message}")
                sections.append("我会陪你把这件事慢慢说清楚。")
        else:
            sections.append(f"我在。你刚才说：{message}")
            sections.append("我会根据当前对话继续帮你。")
    elif persona:
        if persona.verbosity == "detailed":
            sections.append("我会按现在的语气多补一点细节。")
        else:
            sections.append("我会按现在的语气简洁回应。")
        if persona.common_phrases:
            sections.append(f"{persona.common_phrases[0]}")

    return "\n".join(sections), fallback_status


def _extract_user_like_statement(message: str) -> str | None:
    compact = " ".join(message.strip().split())
    if any(token in compact for token in ("什么", "吗", "嘛", "?", "？", "what")):
        return None
    patterns = [
        r"^我喜欢吃(?P<item>.+)$",
        r"^我喜欢(?P<item>.+)$",
        r"^我爱吃(?P<item>.+)$",
        r"^我爱(?P<item>.+)$",
        r"^I like (?P<item>.+)$",
        r"^I love (?P<item>.+)$",
    ]
    for pattern in patterns:
        match = re.match(pattern, compact, flags=re.IGNORECASE)
        if not match:
            continue
        item = match.group("item").strip(" 。.，,！!？?")
        return item or None
    return None


def _extract_liked_items_from_text(text: str) -> list[str]:
    items: list[str] = []
    if any(token in text for token in ("我喜欢什么", "我喜欢吃什么", "我爱吃什么", "what do i like")):
        return items
    patterns = [
        r"我喜欢吃([^。！？\n，,]+)",
        r"我喜欢([^。！？\n，,]+)",
        r"我爱吃([^。！？\n，,]+)",
        r"我爱([^。！？\n，,]+)",
        r"I like ([^.\n,!?]+)",
        r"I love ([^.\n,!?]+)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            item = match.group(1).strip(" 。.，,！!？?")
            item = re.sub(r"^(吃|喝)\s*", "", item).strip()
            if any(token in item for token in ("什么", "吗", "嘛", "?", "？", "what")):
                continue
            if item and item not in items:
                items.append(item)
    return items


def _answer_like_question(message: str, executions: list[SkillExecutionResult], recent_messages: list[Message]) -> str | None:
    compact = " ".join(message.strip().split()).lower()
    asks_like = any(
        token in compact
        for token in (
            "我喜欢什么",
            "我喜欢吃什么",
            "我爱吃什么",
            "what do i like",
            "what food do i like",
        )
    )
    if not asks_like:
        return None

    evidence_texts: list[str] = []
    for execution in executions:
        if not (_uses_handler(execution, "memory-search") and execution.success):
            continue
        for match in execution.output.get("matches", []):
            content = str(match.get("content", "")).strip()
            if content:
                evidence_texts.append(content)

    for item in reversed(recent_messages):
        if item.role == MessageRole.USER:
            evidence_texts.append(item.content)

    liked_items: list[str] = []
    for text in evidence_texts:
        for item in _extract_liked_items_from_text(text):
            if item not in liked_items:
                liked_items.append(item)

    if not liked_items:
        return "我还没有可靠地记住你喜欢什么。你可以直接告诉我一次，我会认真记下来。"

    if len(liked_items) == 1:
        return f"你喜欢{liked_items[0]}。我记住了。"
    return f"你喜欢{'、'.join(liked_items[:4])}。我记住了。"


def _build_local_chat_response(
    *,
    message: str,
    persona: Persona | None,
    executions: list[SkillExecutionResult],
    recent_messages: list[Message],
) -> str | None:
    like_answer = _answer_like_question(message, executions, recent_messages)
    if like_answer:
        return like_answer

    liked_item = _extract_user_like_statement(message)
    if liked_item:
        if persona:
            return f"我记住了，你喜欢{liked_item}。下次看到{liked_item}，我大概会先想到你。"
        return f"记住了，你喜欢{liked_item}。"

    stripped = message.strip()
    greetings = {"你好", "嗨", "hello", "Hello", "hi", "Hi"}
    if stripped in greetings and persona:
        phrases = [item for item in persona.common_phrases[:2] if item]
        greeting = phrases[0] if phrases else "早安"
        return f"{greeting}。你来找我了，我有点开心。今天想和我聊什么？"

    return None


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
        ModelCompletionRequest(
            provider_id=payload.provider_id,
            messages=prompt_messages + precomputed_tool_messages,
            tools=tool_definitions,
        )
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
            ModelCompletionRequest(
                provider_id=payload.provider_id,
                messages=rerun_messages,
                tools=tool_definitions,
            )
        )

    model_mode = "mock" if completion.finish_reason == "mock" else "live"
    response_content = completion.content
    fallback_status = "not_used"

    if model_mode == "mock":
        local_chat_response = _build_local_chat_response(
            message=payload.message,
            persona=persona,
            executions=executions,
            recent_messages=history_messages,
        )
        if local_chat_response:
            response_content = local_chat_response
            fallback_status = "mock_provider_conversational"
        else:
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
            "model_think_enabled": completion.usage.get("think_enabled"),
            "model_think_gate": completion.usage.get("think_gate"),
            "model_think_reason": completion.usage.get("think_reason"),
            "route_policy": completion.route_policy,
            "fallback_policy": completion.fallback_policy,
            "provider_fallback_used": completion.fallback_used,
            "provider_fallback_reason": completion.fallback_reason,
            "attempted_providers": completion.attempted_providers,
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
            model_think_enabled=completion.usage.get("think_enabled"),
            model_think_gate=completion.usage.get("think_gate"),
            model_think_reason=completion.usage.get("think_reason"),
            route_policy=completion.route_policy,
            fallback_policy=completion.fallback_policy,
            provider_fallback_used=completion.fallback_used,
            provider_fallback_reason=completion.fallback_reason,
            attempted_providers=completion.attempted_providers,
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
