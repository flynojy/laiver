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
    async def complete(self, request: ModelCompletionRequest) -> ModelCompletionResponse:
        if self.is_mock_transport:
            return await self._mock_complete(request)

        payload = {
            "model": request.model or self.model_name,
            "messages": [_message_dump(message) for message in request.messages],
            "stream": False,
        }

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
            },
        )

    async def stream(self, request: ModelCompletionRequest) -> AsyncIterator[str]:
        if self.is_mock_transport:
            async for chunk in self._mock_stream(request):
                yield chunk
            return

        payload = {
            "model": request.model or self.model_name,
            "messages": [_message_dump(message) for message in request.messages],
            "stream": True,
        }

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

    def _resolve_api_key(self, provider_row: ModelProvider | None) -> str:
        if not provider_row:
            return settings.deepseek_api_key

        api_key_ref = (provider_row.api_key_ref or "").strip()
        if not api_key_ref:
            if provider_row.provider_type == ProviderType.DEEPSEEK:
                return settings.deepseek_api_key
            return ""
        if api_key_ref.startswith("env:"):
            return os.getenv(api_key_ref.split(":", 1)[1], "")
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
                supports_streaming=True,
                supports_tool_calling=bool(provider_settings.get("supports_tool_calling", False)),
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
        provider = self.resolve_provider(str(request.provider_id) if request.provider_id else None)
        return await provider.complete(request)

    async def stream(self, request: ModelCompletionRequest) -> AsyncIterator[str]:
        provider = self.resolve_provider(str(request.provider_id) if request.provider_id else None)
        async for chunk in provider.stream(request):
            yield chunk

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
                completion_ok=False,
                stream_ok=False,
                tool_call_ok=False,
                error=f"{provider.provider_name.upper()} API key is not configured. Live validation was skipped.",
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
            return ModelProviderValidationResponse(
                provider_id=provider_row.id if provider_row else None,
                provider_name=provider.name,
                provider_type=provider_type,
                model_name=provider.model_name,
                base_url=provider.base_url,
                api_key_configured=api_key_configured,
                mode="live",
                completion_ok=completion_ok,
                stream_ok=stream_ok,
                tool_call_ok=tool_call_ok,
                completion_preview=completion_preview,
                stream_preview=stream_preview,
                tool_calls=tool_calls,
                usage=usage,
                error=str(exc),
                checked_at=checked_at,
            )


def build_tool_message(tool_call_id: str, name: str, payload: dict) -> ModelMessage:
    return ModelMessage(
        role="tool",
        content=json.dumps(payload, ensure_ascii=False),
        name=name,
        tool_call_id=tool_call_id,
    )
