from __future__ import annotations

import asyncio
import json
import os
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import ProviderType
from app.models.runtime import ModelProvider
from app.services.local_adapter_runtime import get_local_adapter_runtime_manager
from app.schemas.runtime import (
    ModelCompletionRequest,
    ModelCompletionResponse,
    ModelMessage,
    ModelProviderValidationRequest,
    ModelProviderValidationResponse,
    ModelToolCall,
    ToolDefinition,
)

settings = get_settings()

DEFAULT_ROUTE_POLICY = "default_enabled_provider"
EXPLICIT_ROUTE_POLICY = "explicit_provider"
DEFAULT_FALLBACK_POLICY = "mock_on_error"
NO_FALLBACK_POLICY = "none"


def _message_dump(message: ModelMessage) -> dict:
    return message.model_dump(exclude_none=True)


def _parse_tool_calls(payload: list[dict] | None) -> list[ModelToolCall]:
    tool_calls: list[ModelToolCall] = []
    for item in payload or []:
        function_payload = item.get("function", {})
        arguments = function_payload.get("arguments", "{}")
        try:
            parsed_arguments = json.loads(arguments) if isinstance(arguments, str) else arguments
        except json.JSONDecodeError:
            parsed_arguments = {"raw": arguments}
        tool_calls.append(
            ModelToolCall(
                id=item.get("id", "tool-call"),
                name=function_payload.get("name", "unknown"),
                arguments=parsed_arguments if isinstance(parsed_arguments, dict) else {"raw": parsed_arguments},
            )
        )
    return tool_calls


def _error_detail(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        body = exc.response.text.strip()
        if body:
            return body
    return str(exc)


class BaseModelProvider(ABC):
    def __init__(
        self,
        *,
        name: str,
        model_name: str,
        base_url: str,
        api_key: str,
        provider_name: str,
        requires_api_key: bool = False,
        supports_streaming: bool = True,
        supports_tool_calling: bool = True,
    ) -> None:
        self.name = name
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.provider_name = provider_name
        self.requires_api_key = requires_api_key
        self.supports_streaming = supports_streaming
        self.supports_tool_calling = supports_tool_calling

    @property
    def is_mock_transport(self) -> bool:
        return self.base_url.startswith("mock://")

    def _last_user_message(self, request: ModelCompletionRequest) -> str:
        for message in reversed(request.messages):
            if message.role == "user":
                return message.content
        return request.messages[-1].content if request.messages else ""

    def _extract_exact_reply(self, prompt: str) -> str | None:
        marker = "Reply with the exact text:"
        if marker not in prompt:
            return None
        reply = prompt.split(marker, 1)[1].strip()
        return reply.strip("\"' ")

    def _mock_content(self, request: ModelCompletionRequest) -> str:
        user_prompt = self._last_user_message(request)
        exact = self._extract_exact_reply(user_prompt)
        if exact:
            return exact
        if request.tools and self.supports_tool_calling:
            return ""
        return f"{self.provider_name} mock live response: {user_prompt}".strip()

    def _mock_tool_calls(self, request: ModelCompletionRequest) -> list[ModelToolCall]:
        if not request.tools or not self.supports_tool_calling:
            return []
        first_tool = request.tools[0].function
        return [
            ModelToolCall(
                id="mock-tool-call",
                name=str(first_tool.get("name", "tool")),
                arguments={"status": "ok"},
            )
        ]

    async def _mock_complete(self, request: ModelCompletionRequest) -> ModelCompletionResponse:
        return ModelCompletionResponse(
            content=self._mock_content(request),
            model=request.model or self.model_name,
            provider=self.provider_name,
            finish_reason="stop",
            tool_calls=self._mock_tool_calls(request),
            usage={"mode": "mock_transport"},
        )

    async def _mock_stream(self, request: ModelCompletionRequest) -> AsyncIterator[str]:
        content = self._mock_content(request) or "streaming-ok"
        yield content

    @abstractmethod
    async def complete(self, request: ModelCompletionRequest) -> ModelCompletionResponse:
        raise NotImplementedError

    @abstractmethod
    async def stream(self, request: ModelCompletionRequest) -> AsyncIterator[str]:
        raise NotImplementedError


def _ollama_options(request: ModelCompletionRequest, provider_settings: dict[str, Any]) -> dict[str, Any]:
    options: dict[str, Any] = {
        "temperature": request.temperature,
        "num_predict": request.max_tokens,
    }
    for source_key, target_key in (
        ("num_ctx", "num_ctx"),
        ("num_gpu", "num_gpu"),
        ("num_thread", "num_thread"),
        ("top_k", "top_k"),
        ("top_p", "top_p"),
        ("repeat_penalty", "repeat_penalty"),
        ("use_mmap", "use_mmap"),
        ("main_gpu", "main_gpu"),
    ):
        if source_key in provider_settings:
            options[target_key] = provider_settings[source_key]
    return options


def _coerce_bool_setting(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on", "enabled", "always"}:
            return True
        if normalized in {"0", "false", "no", "off", "disabled", "never"}:
            return False
    return None


def _last_user_content(request: ModelCompletionRequest) -> str:
    for message in reversed(request.messages):
        if message.role == "user":
            return message.content or ""
    return request.messages[-1].content if request.messages else ""


def _ollama_think_decision(request: ModelCompletionRequest, provider_settings: dict[str, Any]) -> dict[str, Any]:
    for key in ("think", "ollama_think", "enable_thinking"):
        if key in provider_settings:
            override = _coerce_bool_setting(provider_settings[key])
            if override is not None:
                return {
                    "enabled": override,
                    "gate": "settings_override",
                    "reason": key,
                }

    mode = str(provider_settings.get("think_mode", "auto")).strip().lower()
    mode_override = _coerce_bool_setting(mode)
    if mode_override is not None:
        return {
            "enabled": mode_override,
            "gate": "settings_override",
            "reason": "think_mode",
        }
    if mode and mode not in {"auto", "heuristic"}:
        return {
            "enabled": False,
            "gate": "fast_reply",
            "reason": f"unknown_think_mode:{mode}",
        }

    last_user = _last_user_content(request)
    normalized = last_user.lower()
    message_count = len(request.messages)
    total_chars = sum(len(message.content or "") for message in request.messages)

    if request.tools:
        return {
            "enabled": True,
            "gate": "tool_or_memory_heavy",
            "reason": "tools_attached",
        }

    if message_count >= 10 or total_chars >= 4000:
        return {
            "enabled": True,
            "gate": "tool_or_memory_heavy",
            "reason": "long_context",
        }

    reasoning_markers = (
        "分析",
        "推理",
        "思考",
        "为什么",
        "怎麼",
        "怎么",
        "比较",
        "权衡",
        "规划",
        "计划",
        "方案",
        "排查",
        "诊断",
        "复杂",
        "多步",
        "步骤",
        "冲突",
        "记忆",
        "总结",
        "debug",
        "diagnose",
        "reason",
        "analyze",
        "compare",
        "tradeoff",
        "plan",
        "multi-step",
    )
    if any(marker in normalized for marker in reasoning_markers):
        return {
            "enabled": True,
            "gate": "need_reasoning",
            "reason": "reasoning_marker",
        }

    question_count = last_user.count("?") + last_user.count("？")
    if question_count >= 2 or len(last_user) >= 240:
        return {
            "enabled": True,
            "gate": "need_reasoning",
            "reason": "question_or_length",
        }

    return {
        "enabled": False,
        "gate": "fast_reply",
        "reason": "simple_or_short",
    }


def _ollama_think_enabled(request: ModelCompletionRequest, provider_settings: dict[str, Any]) -> bool:
    return bool(_ollama_think_decision(request, provider_settings)["enabled"])


class ChatCompletionsProvider(BaseModelProvider):
    async def complete(self, request: ModelCompletionRequest) -> ModelCompletionResponse:
        if self.is_mock_transport:
            return await self._mock_complete(request)

        if self.requires_api_key and not self.api_key:
            return ModelCompletionResponse(
                content=f"{self.provider_name} API key is not configured. This is a mock fallback response for local MVP testing.",
                model=request.model or self.model_name,
                provider=self.provider_name,
                finish_reason="mock",
            )

        payload = {
            "model": request.model or self.model_name,
            "messages": [_message_dump(message) for message in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.tools and self.supports_tool_calling:
            payload["tools"] = [tool.model_dump() for tool in request.tools]
            payload["tool_choice"] = "auto"

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        choice = data["choices"][0]
        message = choice["message"]
        return ModelCompletionResponse(
            content=message.get("content", "") or "",
            model=data.get("model", request.model or self.model_name),
            provider=self.provider_name,
            finish_reason=choice.get("finish_reason", "stop"),
            tool_calls=_parse_tool_calls(message.get("tool_calls")),
            usage=data.get("usage", {}),
        )

    async def stream(self, request: ModelCompletionRequest) -> AsyncIterator[str]:
        if self.is_mock_transport:
            async for chunk in self._mock_stream(request):
                yield chunk
            return

        if self.requires_api_key and not self.api_key:
            yield f"{self.provider_name} API key is not configured. Streaming is running in mock mode."
            return

        payload = {
            "model": request.model or self.model_name,
            "messages": [_message_dump(message) for message in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }
        if request.tools and self.supports_tool_calling:
            payload["tools"] = [tool.model_dump() for tool in request.tools]

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    chunk = line.removeprefix("data:").strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        data = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content


class DeepSeekProvider(ChatCompletionsProvider):
    def __init__(self, *, name: str, model_name: str, base_url: str, api_key: str) -> None:
        super().__init__(
            name=name,
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            provider_name=ProviderType.DEEPSEEK.value,
            requires_api_key=True,
            supports_streaming=True,
            supports_tool_calling=True,
        )


class OpenAICompatibleProvider(ChatCompletionsProvider):
    def __init__(
        self,
        *,
        name: str,
        model_name: str,
        base_url: str,
        api_key: str,
        requires_api_key: bool,
        supports_streaming: bool = True,
        supports_tool_calling: bool = True,
    ) -> None:
        super().__init__(
            name=name,
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            provider_name=ProviderType.OPENAI_COMPATIBLE.value,
            requires_api_key=requires_api_key,
            supports_streaming=supports_streaming,
            supports_tool_calling=supports_tool_calling,
        )


class OllamaProvider(BaseModelProvider):
    def __init__(self, *, settings: dict[str, Any] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.settings = settings or {}

    async def complete(self, request: ModelCompletionRequest) -> ModelCompletionResponse:
        if self.is_mock_transport:
            return await self._mock_complete(request)

        think_decision = _ollama_think_decision(request, self.settings)
        payload = {
            "model": request.model or self.model_name,
            "messages": [_message_dump(message) for message in request.messages],
            "stream": False,
            "think": think_decision["enabled"],
            "options": _ollama_options(request, self.settings),
        }
        if request.tools and self.supports_tool_calling:
            payload["tools"] = [tool.model_dump() for tool in request.tools]

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        message = data.get("message", {})
        return ModelCompletionResponse(
            content=message.get("content", "") or "",
            model=data.get("model", request.model or self.model_name),
            provider=self.provider_name,
            finish_reason="stop" if data.get("done", True) else "length",
            tool_calls=_parse_tool_calls(message.get("tool_calls")),
            usage={
                "prompt_eval_count": data.get("prompt_eval_count"),
                "eval_count": data.get("eval_count"),
                "total_duration": data.get("total_duration"),
                "think_enabled": think_decision["enabled"],
                "think_gate": think_decision["gate"],
                "think_reason": think_decision["reason"],
            },
        )

    async def stream(self, request: ModelCompletionRequest) -> AsyncIterator[str]:
        if self.is_mock_transport:
            async for chunk in self._mock_stream(request):
                yield chunk
            return

        think_decision = _ollama_think_decision(request, self.settings)
        payload = {
            "model": request.model or self.model_name,
            "messages": [_message_dump(message) for message in request.messages],
            "stream": True,
            "think": think_decision["enabled"],
            "options": _ollama_options(request, self.settings),
        }
        if request.tools and self.supports_tool_calling:
            payload["tools"] = [tool.model_dump() for tool in request.tools]

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                headers={"Content-Type": "application/json"},
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    content = data.get("message", {}).get("content")
                    if content:
                        yield content
                    if data.get("done"):
                        break

class LocalAdapterProvider(BaseModelProvider):
    def __init__(
        self,
        *,
        provider_row: ModelProvider,
        name: str,
        model_name: str,
        base_url: str,
        settings: dict[str, Any],
    ) -> None:
        super().__init__(
            name=name,
            model_name=model_name,
            base_url=base_url,
            api_key="",
            provider_name=ProviderType.LOCAL_ADAPTER.value,
            requires_api_key=False,
            supports_streaming=bool(settings.get("supports_streaming", False)),
            supports_tool_calling=bool(settings.get("supports_tool_calling", False)),
        )
        self.provider_row = provider_row
        self.settings = settings
        self.adapter_path = str(settings.get("adapter_path", "")).strip()
        self.base_model_ref = str(settings.get("base_model", model_name)).strip()
        self.inference_mode = str(settings.get("inference_mode", "transformers")).strip().lower()
        self.runtime_manager = get_local_adapter_runtime_manager()

    @property
    def is_mock_inference(self) -> bool:
        return self.inference_mode == "mock" or self.base_model_ref.startswith("mock://")

    def _missing_dependency_response(self, request: ModelCompletionRequest, error: str) -> ModelCompletionResponse:
        return ModelCompletionResponse(
            content=f"Local adapter inference is unavailable: {error}",
            model=request.model or self.model_name,
            provider=self.provider_name,
            finish_reason="mock",
            usage={"mode": "local_adapter_unavailable", "error": error},
        )

    async def complete(self, request: ModelCompletionRequest) -> ModelCompletionResponse:
        try:
            content, usage, resolved_model = await asyncio.to_thread(
                self.runtime_manager.generate,
                self.provider_row,
                messages=[_message_dump(message) for message in request.messages],
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )
        except Exception as exc:
            return self._missing_dependency_response(request, str(exc))

        return ModelCompletionResponse(
            content=content,
            model=request.model or resolved_model,
            provider=self.provider_name,
            finish_reason="stop",
            usage=usage,
        )

    async def stream(self, request: ModelCompletionRequest) -> AsyncIterator[str]:
        completion = await self.complete(request)
        yield completion.content


class ModelRouterService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _select_provider_row(self, provider_id: str | None = None) -> ModelProvider | None:
        provider_row = None
        if provider_id:
            provider_row = self.db.scalar(select(ModelProvider).where(ModelProvider.id == uuid.UUID(provider_id)))
        if not provider_row:
            provider_row = self.db.scalar(
                select(ModelProvider).where(
                    ModelProvider.is_default.is_(True),
                    ModelProvider.is_enabled.is_(True),
                )
            )
        return provider_row

    def _route_policy_for(self, provider_row: ModelProvider | None, provider_id: str | None) -> str:
        provider_settings = provider_row.settings if provider_row else {}
        configured = str((provider_settings or {}).get("route_policy", "")).strip()
        if configured:
            return configured
        return EXPLICIT_ROUTE_POLICY if provider_id else DEFAULT_ROUTE_POLICY

    def _fallback_policy_for(self, provider_row: ModelProvider | None) -> str:
        provider_settings = provider_row.settings if provider_row else {}
        configured = str((provider_settings or {}).get("fallback_policy", "")).strip()
        return configured or DEFAULT_FALLBACK_POLICY

    def _fallback_available(self, provider_row: ModelProvider | None, provider: BaseModelProvider) -> bool:
        return self._fallback_policy_for(provider_row) != NO_FALLBACK_POLICY and not provider.is_mock_transport

    def _provider_attempt_label(
        self,
        provider_row: ModelProvider | None,
        provider: BaseModelProvider,
    ) -> str:
        if provider_row:
            return f"{provider_row.provider_type.value}:{provider_row.name}"
        return f"{provider.provider_name}:{provider.name}"

    def _classify_provider_error(self, exc: Exception) -> str:
        if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
            return "timeout"
        if isinstance(exc, httpx.HTTPStatusError):
            status_code = exc.response.status_code
            if status_code in {401, 403}:
                return "auth_failed"
            if status_code == 429:
                return "rate_limited"
            if status_code >= 500:
                return "provider_unavailable"
            return "provider_http_error"
        if isinstance(exc, httpx.RequestError):
            return "provider_unreachable"
        if isinstance(exc, ValueError):
            return "invalid_provider"
        return "provider_error"

    def _provider_recommendation(
        self,
        *,
        provider_type: ProviderType,
        error_code: str | None,
        error: str | None,
    ) -> str | None:
        error_text = (error or "").lower()
        if provider_type == ProviderType.OLLAMA:
            if "memory layout cannot be allocated" in error_text:
                return (
                    "Ollama reported a Windows runner memory-layout allocation failure. "
                    "Reboot to clear resident GPU memory, then retry with a smaller num_ctx or model. "
                    "If it still fails, use a smaller Qwen3 quant/model or move this runtime to WSL2/Linux."
                )
            if error_code == "provider_unreachable":
                return "Start Ollama and confirm the API responds at /api/tags before validating this provider."
            if error_code == "provider_unavailable":
                return "Ollama is reachable but failed during generation. Check Ollama logs, GPU memory, model tag, and context size."
        if error_code == "auth_failed":
            return "Check the provider API key reference and restart the API after updating .env."
        if error_code == "rate_limited":
            return "The provider is rate limited. Retry later or switch the default provider temporarily."
        if error_code == "timeout":
            return "The provider did not finish in time. Lower max tokens/context or use a faster runtime."
        if error_code == "provider_unreachable":
            return "Confirm the provider base URL is correct and reachable from this machine."
        if error_code == "provider_unavailable":
            return "The provider returned a server error. Check provider status or use fallback while it recovers."
        return None

    def _with_route_metadata(
        self,
        response: ModelCompletionResponse,
        *,
        route_policy: str,
        fallback_policy: str,
        attempted_providers: list[str],
        fallback_used: bool = False,
        fallback_reason: str | None = None,
    ) -> ModelCompletionResponse:
        return response.model_copy(
            update={
                "route_policy": route_policy,
                "fallback_policy": fallback_policy,
                "fallback_used": fallback_used,
                "fallback_reason": fallback_reason,
                "attempted_providers": attempted_providers,
            }
        )

    def _fallback_completion(
        self,
        request: ModelCompletionRequest,
        *,
        provider_row: ModelProvider | None,
        provider: BaseModelProvider,
        route_policy: str,
        fallback_policy: str,
        attempted_providers: list[str],
        reason: str,
        error: str,
    ) -> ModelCompletionResponse:
        return ModelCompletionResponse(
            content=(
                f"{provider.provider_name} provider failed with {reason}. "
                "This is a local mock fallback response for MVP testing."
            ),
            model=request.model or provider.model_name,
            provider=provider.provider_name,
            finish_reason="mock",
            usage={
                "mode": "router_mock_fallback",
                "reason": reason,
                "error": error,
                "provider_id": str(provider_row.id) if provider_row else None,
                "provider_name": provider.name,
            },
            route_policy=route_policy,
            fallback_policy=fallback_policy,
            fallback_used=True,
            fallback_reason=reason,
            attempted_providers=attempted_providers,
        )

    def _resolve_api_key(self, provider_row: ModelProvider | None) -> str:
        if not provider_row:
            return settings.deepseek_api_key

        api_key_ref = (provider_row.api_key_ref or "").strip()
        if not api_key_ref:
            if provider_row.provider_type == ProviderType.DEEPSEEK:
                return settings.deepseek_api_key
            return ""
        if api_key_ref.startswith("env:"):
            env_name = api_key_ref.split(":", 1)[1]
            env_value = os.getenv(env_name, "")
            if env_value:
                return env_value
            if env_name == "DEEPSEEK_API_KEY":
                return settings.deepseek_api_key
            return ""
        if api_key_ref.startswith("literal:"):
            return api_key_ref.split(":", 1)[1]
        return api_key_ref

    def _provider_from_row(self, provider_row: ModelProvider) -> BaseModelProvider:
        api_key = self._resolve_api_key(provider_row)
        provider_settings = provider_row.settings or {}

        if provider_row.provider_type == ProviderType.DEEPSEEK:
            return DeepSeekProvider(
                name=provider_row.name,
                model_name=provider_row.model_name,
                base_url=provider_row.base_url,
                api_key=api_key,
            )

        if provider_row.provider_type == ProviderType.OPENAI_COMPATIBLE:
            return OpenAICompatibleProvider(
                name=provider_row.name,
                model_name=provider_row.model_name,
                base_url=provider_row.base_url,
                api_key=api_key,
                requires_api_key=bool((provider_row.api_key_ref or "").strip()),
                supports_streaming=bool(provider_settings.get("supports_streaming", True)),
                supports_tool_calling=bool(provider_settings.get("supports_tool_calling", True)),
            )

        if provider_row.provider_type == ProviderType.OLLAMA:
            return OllamaProvider(
                name=provider_row.name,
                model_name=provider_row.model_name,
                base_url=provider_row.base_url or "http://localhost:11434",
                api_key="",
                provider_name=ProviderType.OLLAMA.value,
                requires_api_key=False,
                supports_streaming=bool(provider_settings.get("supports_streaming", True)),
                supports_tool_calling=bool(provider_settings.get("supports_tool_calling", False)),
                settings=provider_settings,
            )

        if provider_row.provider_type == ProviderType.LOCAL_ADAPTER:
            return LocalAdapterProvider(
                provider_row=provider_row,
                name=provider_row.name,
                model_name=provider_row.model_name,
                base_url=provider_row.base_url,
                settings=provider_settings,
            )

        raise ValueError(f"Unsupported model provider type: {provider_row.provider_type}")

    def resolve_provider(self, provider_id: str | None = None) -> BaseModelProvider:
        provider_row = self._select_provider_row(provider_id)
        if provider_row:
            return self._provider_from_row(provider_row)

        return DeepSeekProvider(
            name="DeepSeek Default",
            model_name=settings.deepseek_model,
            base_url=settings.deepseek_base_url,
            api_key=settings.deepseek_api_key,
        )

    async def complete(self, request: ModelCompletionRequest) -> ModelCompletionResponse:
        provider_id = str(request.provider_id) if request.provider_id else None
        provider_row = self._select_provider_row(provider_id)
        provider = self._provider_from_row(provider_row) if provider_row else self.resolve_provider(None)
        route_policy = self._route_policy_for(provider_row, provider_id)
        fallback_policy = self._fallback_policy_for(provider_row)
        attempted_providers = [self._provider_attempt_label(provider_row, provider)]

        try:
            completion = await provider.complete(request)
        except Exception as exc:
            reason = self._classify_provider_error(exc)
            if fallback_policy == NO_FALLBACK_POLICY:
                raise
            return self._fallback_completion(
                request,
                provider_row=provider_row,
                provider=provider,
                route_policy=route_policy,
                fallback_policy=fallback_policy,
                attempted_providers=attempted_providers,
                reason=reason,
                error=str(exc),
            )

        fallback_used = completion.finish_reason == "mock"
        fallback_reason = None
        if fallback_used:
            fallback_reason = "api_key_missing" if provider.requires_api_key and not provider.api_key else "provider_mock"
        return self._with_route_metadata(
            completion,
            route_policy=route_policy,
            fallback_policy=fallback_policy,
            attempted_providers=attempted_providers,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        )

    async def stream(self, request: ModelCompletionRequest) -> AsyncIterator[str]:
        provider_id = str(request.provider_id) if request.provider_id else None
        provider_row = self._select_provider_row(provider_id)
        provider = self._provider_from_row(provider_row) if provider_row else self.resolve_provider(None)
        route_policy = self._route_policy_for(provider_row, provider_id)
        fallback_policy = self._fallback_policy_for(provider_row)
        attempted_providers = [self._provider_attempt_label(provider_row, provider)]

        try:
            async for chunk in provider.stream(request):
                yield chunk
        except Exception as exc:
            if fallback_policy == NO_FALLBACK_POLICY:
                raise
            fallback = self._fallback_completion(
                request,
                provider_row=provider_row,
                provider=provider,
                route_policy=route_policy,
                fallback_policy=fallback_policy,
                attempted_providers=attempted_providers,
                reason=self._classify_provider_error(exc),
                error=str(exc),
            )
            yield fallback.content

    async def validate(self, request: ModelProviderValidationRequest) -> ModelProviderValidationResponse:
        provider_row = self._select_provider_row(str(request.provider_id) if request.provider_id else None)
        provider = self.resolve_provider(str(request.provider_id) if request.provider_id else None)
        provider_type = provider_row.provider_type if provider_row else ProviderType(provider.provider_name)
        checked_at = datetime.now(timezone.utc)
        api_key_configured = bool(provider.api_key)

        if provider.requires_api_key and not api_key_configured:
            return ModelProviderValidationResponse(
                provider_id=provider_row.id if provider_row else None,
                provider_name=provider.name,
                provider_type=provider_type,
                model_name=provider.model_name,
                base_url=provider.base_url,
                api_key_configured=False,
                mode="mock",
                health_status="skipped",
                route_policy=self._route_policy_for(
                    provider_row, str(request.provider_id) if request.provider_id else None
                ),
                fallback_policy=self._fallback_policy_for(provider_row),
                fallback_available=self._fallback_available(provider_row, provider),
                completion_ok=False,
                stream_ok=False,
                tool_call_ok=False,
                error_code="api_key_missing",
                error=f"{provider.provider_name.upper()} API key is not configured. Live validation was skipped.",
                recommendation="Add the provider API key to .env, then restart the API before validating again.",
                checked_at=checked_at,
            )

        completion_preview = ""
        stream_preview = ""
        tool_calls: list[ModelToolCall] = []
        usage: dict = {}
        completion_ok = False
        stream_ok = False
        tool_call_ok = False
        notes: list[str] = []

        try:
            completion = await provider.complete(
                ModelCompletionRequest(
                    provider_id=request.provider_id,
                    messages=[
                        ModelMessage(role="system", content="You are a connectivity probe. Follow the user exactly."),
                        ModelMessage(role="user", content=request.prompt),
                    ],
                    temperature=0.0,
                    max_tokens=64,
                )
            )
            completion_preview = completion.content
            usage = completion.usage
            completion_ok = completion.finish_reason != "mock"

            if request.check_stream:
                if provider.supports_streaming:
                    chunks: list[str] = []
                    async for chunk in provider.stream(
                        ModelCompletionRequest(
                            provider_id=request.provider_id,
                            messages=[
                                ModelMessage(
                                    role="user",
                                    content="Reply with the exact text: streaming-ok",
                                )
                            ],
                            temperature=0.0,
                            max_tokens=32,
                        )
                    ):
                        chunks.append(chunk)
                        if len("".join(chunks)) >= 64:
                            break
                    stream_preview = "".join(chunks).strip()
                    stream_ok = bool(stream_preview)
                else:
                    notes.append("Provider does not advertise streaming support.")

            if request.check_tool_call:
                if provider.supports_tool_calling:
                    tool_probe = await provider.complete(
                        ModelCompletionRequest(
                            provider_id=request.provider_id,
                            messages=[
                                ModelMessage(
                                    role="user",
                                    content=request.tool_prompt,
                                )
                            ],
                            tools=[
                                ToolDefinition(
                                    function={
                                        "name": "echo_status",
                                        "description": "Returns the current validation status.",
                                        "parameters": {
                                            "type": "object",
                                            "properties": {
                                                "status": {"type": "string"},
                                            },
                                            "required": ["status"],
                                        },
                                    }
                                )
                            ],
                            temperature=0.0,
                            max_tokens=128,
                        )
                    )
                    tool_calls = tool_probe.tool_calls
                    tool_call_ok = bool(tool_probe.tool_calls)
                    if tool_probe.usage:
                        usage = tool_probe.usage
                else:
                    notes.append("Provider does not advertise tool-calling support.")

            return ModelProviderValidationResponse(
                provider_id=provider_row.id if provider_row else None,
                provider_name=provider.name,
                provider_type=provider_type,
                model_name=provider.model_name,
                base_url=provider.base_url,
                api_key_configured=api_key_configured,
                mode="live",
                health_status="healthy" if completion_ok else "degraded",
                route_policy=self._route_policy_for(
                    provider_row, str(request.provider_id) if request.provider_id else None
                ),
                fallback_policy=self._fallback_policy_for(provider_row),
                fallback_available=self._fallback_available(provider_row, provider),
                completion_ok=completion_ok,
                stream_ok=stream_ok if request.check_stream else False,
                tool_call_ok=tool_call_ok if request.check_tool_call else False,
                completion_preview=completion_preview,
                stream_preview=stream_preview,
                tool_calls=tool_calls,
                usage=usage,
                error=" ".join(notes) if notes else None,
                checked_at=checked_at,
            )
        except Exception as exc:
            error_code = self._classify_provider_error(exc)
            error = _error_detail(exc)
            return ModelProviderValidationResponse(
                provider_id=provider_row.id if provider_row else None,
                provider_name=provider.name,
                provider_type=provider_type,
                model_name=provider.model_name,
                base_url=provider.base_url,
                api_key_configured=api_key_configured,
                mode="live",
                health_status="unhealthy",
                route_policy=self._route_policy_for(
                    provider_row, str(request.provider_id) if request.provider_id else None
                ),
                fallback_policy=self._fallback_policy_for(provider_row),
                fallback_available=self._fallback_available(provider_row, provider),
                completion_ok=completion_ok,
                stream_ok=stream_ok,
                tool_call_ok=tool_call_ok,
                completion_preview=completion_preview,
                stream_preview=stream_preview,
                tool_calls=tool_calls,
                usage=usage,
                error_code=error_code,
                error=error,
                recommendation=self._provider_recommendation(
                    provider_type=provider_type,
                    error_code=error_code,
                    error=error,
                ),
                checked_at=checked_at,
            )


def build_tool_message(tool_call_id: str, name: str, payload: dict) -> ModelMessage:
    return ModelMessage(
        role="tool",
        content=json.dumps(payload, ensure_ascii=False),
        name=name,
        tool_call_id=tool_call_id,
    )
