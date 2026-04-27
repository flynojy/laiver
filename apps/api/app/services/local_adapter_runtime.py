from __future__ import annotations

import gc
import importlib
import importlib.util
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock, RLock
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.enums import ProviderType
from app.models.runtime import ModelProvider
from app.schemas.runtime import LocalAdapterRuntimeRead


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _render_local_prompt(messages: list[dict[str, str]]) -> str:
    chunks: list[str] = []
    for message in messages:
        role = str(message.get("role", "user")).strip().lower()
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        chunks.append(f"<|{role}|>\n{content}")
    chunks.append("<|assistant|>\n")
    return "\n".join(chunks)


@dataclass
class LocalAdapterRuntimeEntry:
    cache_key: str
    provider_ids: set[UUID]
    provider_name: str
    model_name: str
    base_model: str
    adapter_path: str
    inference_mode: str
    status: str = "idle"
    device: str | None = None
    runtime: dict[str, Any] | None = None
    last_error: str | None = None
    loaded_at: datetime | None = None
    last_used_at: datetime | None = None
    load_count: int = 0
    request_count: int = 0
    active_request_count: int = 0
    evict_count: int = 0
    load_duration_ms: int | None = None
    memory_allocated_mb: float | None = None
    memory_reserved_mb: float | None = None
    last_evicted_at: datetime | None = None
    last_eviction_reason: str | None = None
    entry_lock: Lock = field(default_factory=Lock, repr=False)


class LocalAdapterRuntimeManager:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._entries: dict[str, LocalAdapterRuntimeEntry] = {}
        self._provider_index: dict[UUID, str] = {}
        self._lock = RLock()

    def _settings_for(self, provider_row: ModelProvider) -> dict[str, Any]:
        return dict(provider_row.settings or {})

    def _cache_key(self, provider_row: ModelProvider) -> str:
        settings = self._settings_for(provider_row)
        base_model = str(settings.get("base_model", provider_row.model_name)).strip()
        adapter_path = str(settings.get("adapter_path", "")).strip()
        return f"{base_model}::{adapter_path}"

    def _inference_mode(self, provider_row: ModelProvider) -> str:
        return str(self._settings_for(provider_row).get("inference_mode", "transformers")).strip().lower()

    def _base_model(self, provider_row: ModelProvider) -> str:
        return str(self._settings_for(provider_row).get("base_model", provider_row.model_name)).strip()

    def _adapter_path(self, provider_row: ModelProvider) -> str:
        return str(self._settings_for(provider_row).get("adapter_path", "")).strip()

    def _ensure_entry(self, provider_row: ModelProvider) -> LocalAdapterRuntimeEntry:
        cache_key = self._cache_key(provider_row)
        entry = self._entries.get(cache_key)
        if entry is None:
            entry = LocalAdapterRuntimeEntry(
                cache_key=cache_key,
                provider_ids={provider_row.id},
                provider_name=provider_row.name,
                model_name=provider_row.model_name,
                base_model=self._base_model(provider_row),
                adapter_path=self._adapter_path(provider_row),
                inference_mode=self._inference_mode(provider_row),
            )
            self._entries[cache_key] = entry
        else:
            entry.provider_ids.add(provider_row.id)
            entry.provider_name = provider_row.name
            entry.model_name = provider_row.model_name
            entry.base_model = self._base_model(provider_row)
            entry.adapter_path = self._adapter_path(provider_row)
            entry.inference_mode = self._inference_mode(provider_row)

        self._provider_index[provider_row.id] = cache_key
        return entry

    def _find_entry_by_provider_id(self, provider_id: UUID) -> LocalAdapterRuntimeEntry | None:
        cache_key = self._provider_index.get(provider_id)
        if cache_key:
            return self._entries.get(cache_key)
        return None

    def _dependency_missing(self) -> list[str]:
        required = ["torch", "transformers", "peft"]
        return [name for name in required if importlib.util.find_spec(name) is None]

    def _runtime_summary(self, entry: LocalAdapterRuntimeEntry, provider_id: UUID) -> LocalAdapterRuntimeRead:
        idle_seconds = None
        if entry.last_used_at is not None:
            idle_seconds = max(0, int((_now() - entry.last_used_at).total_seconds()))
        return LocalAdapterRuntimeRead(
            provider_id=provider_id,
            provider_name=entry.provider_name,
            provider_type=ProviderType.LOCAL_ADAPTER,
            model_name=entry.model_name,
            base_model=entry.base_model,
            adapter_path=entry.adapter_path,
            inference_mode=entry.inference_mode,
            status=entry.status,
            resident=entry.runtime is not None or entry.status == "mock_ready",
            device=entry.device,
            load_count=entry.load_count,
            request_count=entry.request_count,
            active_request_count=entry.active_request_count,
            evict_count=entry.evict_count,
            load_duration_ms=entry.load_duration_ms,
            memory_allocated_mb=entry.memory_allocated_mb,
            memory_reserved_mb=entry.memory_reserved_mb,
            idle_seconds=idle_seconds,
            idle_timeout_seconds=self.settings.local_adapter_idle_ttl_seconds,
            generate_timeout_seconds=self.settings.local_adapter_generate_timeout_seconds,
            loaded_at=entry.loaded_at,
            last_used_at=entry.last_used_at,
            last_evicted_at=entry.last_evicted_at,
            last_eviction_reason=entry.last_eviction_reason,
            error=entry.last_error,
        )

    def status_for_provider(self, provider_row: ModelProvider) -> LocalAdapterRuntimeRead:
        with self._lock:
            self.cleanup_idle()
            entry = self._ensure_entry(provider_row)
            return self._runtime_summary(entry, provider_row.id)

    def list_statuses(self, providers: list[ModelProvider]) -> list[LocalAdapterRuntimeRead]:
        with self._lock:
            self.cleanup_idle()
            return [self.status_for_provider(provider_row) for provider_row in providers]

    def _update_memory_snapshot(self, entry: LocalAdapterRuntimeEntry) -> None:
        runtime = entry.runtime
        if not runtime:
            entry.memory_allocated_mb = None
            entry.memory_reserved_mb = None
            return
        torch_module = runtime.get("torch")
        if torch_module is None or not hasattr(torch_module, "cuda") or not torch_module.cuda.is_available():
            entry.memory_allocated_mb = None
            entry.memory_reserved_mb = None
            return
        try:
            entry.memory_allocated_mb = round(float(torch_module.cuda.memory_allocated()) / (1024 * 1024), 2)
            entry.memory_reserved_mb = round(float(torch_module.cuda.memory_reserved()) / (1024 * 1024), 2)
        except Exception:
            entry.memory_allocated_mb = None
            entry.memory_reserved_mb = None

    def cleanup_idle(self) -> int:
        with self._lock:
            idle_ttl_seconds = max(0, int(self.settings.local_adapter_idle_ttl_seconds))
            if idle_ttl_seconds <= 0:
                cutoff = _now()
            else:
                cutoff = _now() - timedelta(seconds=idle_ttl_seconds)

            evicted = 0
            for entry in self._entries.values():
                if entry.active_request_count > 0:
                    continue
                if entry.runtime is None and entry.status != "mock_ready":
                    continue
                last_used_at = entry.last_used_at or entry.loaded_at
                if last_used_at is None or last_used_at > cutoff:
                    continue
                with entry.entry_lock:
                    if entry.active_request_count > 0:
                        continue
                    last_used_at = entry.last_used_at or entry.loaded_at
                    if last_used_at is None or last_used_at > cutoff:
                        continue
                    self._evict_entry(entry, reason="idle_timeout")
                    evicted += 1
            return evicted

    def _evict_lru_if_needed(self, *, exclude_cache_key: str) -> None:
        loaded_entries = [
            entry
            for key, entry in self._entries.items()
            if key != exclude_cache_key and entry.runtime is not None and entry.status in {"loaded", "mock_ready"}
        ]
        while len(loaded_entries) >= max(1, self.settings.local_adapter_max_resident):
            victim = min(
                loaded_entries,
                key=lambda item: item.last_used_at or item.loaded_at or datetime.min.replace(tzinfo=timezone.utc),
            )
            self._evict_entry(victim)
            loaded_entries = [
                entry
                for key, entry in self._entries.items()
                if key != exclude_cache_key and entry.runtime is not None and entry.status in {"loaded", "mock_ready"}
            ]

    def _load_runtime(self, entry: LocalAdapterRuntimeEntry) -> None:
        missing = self._dependency_missing()
        if missing:
            raise RuntimeError(f"missing dependencies: {', '.join(missing)}")
        if not entry.adapter_path:
            raise RuntimeError("adapter path is empty")
        adapter_dir = Path(entry.adapter_path)
        if not adapter_dir.exists():
            raise RuntimeError(f"adapter path not found: {adapter_dir}")

        torch = importlib.import_module("torch")
        transformers = importlib.import_module("transformers")
        peft = importlib.import_module("peft")

        tokenizer = transformers.AutoTokenizer.from_pretrained(
            adapter_dir.as_posix(),
            trust_remote_code=True,
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token or tokenizer.unk_token
        if tokenizer.pad_token is None:
            tokenizer.add_special_tokens({"pad_token": "<pad>"})

        load_kwargs: dict[str, Any] = {"trust_remote_code": True}
        if torch.cuda.is_available():
            if hasattr(torch.cuda, "is_bf16_supported") and torch.cuda.is_bf16_supported():
                load_kwargs["torch_dtype"] = torch.bfloat16
            else:
                load_kwargs["torch_dtype"] = torch.float16
        else:
            load_kwargs["torch_dtype"] = torch.float32

        base_model = transformers.AutoModelForCausalLM.from_pretrained(entry.base_model, **load_kwargs)
        if torch.cuda.is_available():
            base_model = base_model.to("cuda")
        model = peft.PeftModel.from_pretrained(base_model, adapter_dir.as_posix())
        if torch.cuda.is_available():
            model = model.to("cuda")
        model.eval()

        entry.runtime = {
            "torch": torch,
            "transformers": transformers,
            "tokenizer": tokenizer,
            "model": model,
        }
        entry.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._update_memory_snapshot(entry)

    def warm(self, provider_row: ModelProvider) -> LocalAdapterRuntimeRead:
        with self._lock:
            entry = self._ensure_entry(provider_row)
            with entry.entry_lock:
                entry.last_error = None
                entry.last_eviction_reason = None
                if entry.inference_mode == "mock" or entry.base_model.startswith("mock://"):
                    entry.status = "mock_ready"
                    entry.loaded_at = entry.loaded_at or _now()
                    entry.last_used_at = _now()
                    entry.load_count += 1
                    entry.load_duration_ms = 0
                    entry.memory_allocated_mb = None
                    entry.memory_reserved_mb = None
                    return self._runtime_summary(entry, provider_row.id)

                if entry.runtime is not None and entry.status == "loaded":
                    entry.last_used_at = _now()
                    return self._runtime_summary(entry, provider_row.id)

                self._evict_lru_if_needed(exclude_cache_key=entry.cache_key)
                started = _now()
                try:
                    self._load_runtime(entry)
                    finished = _now()
                    entry.status = "loaded"
                    entry.loaded_at = finished
                    entry.last_used_at = finished
                    entry.load_count += 1
                    entry.load_duration_ms = int((finished - started).total_seconds() * 1000)
                    self._update_memory_snapshot(entry)
                except Exception as exc:
                    entry.runtime = None
                    entry.status = "error"
                    entry.last_error = str(exc)
                return self._runtime_summary(entry, provider_row.id)

    def generate(
        self,
        provider_row: ModelProvider,
        *,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, dict[str, Any], str]:
        with self._lock:
            entry = self._ensure_entry(provider_row)

        summary = self.warm(provider_row)
        if summary.status == "error":
            raise RuntimeError(summary.error or "local adapter runtime failed to warm")

        with entry.entry_lock:
            entry.request_count += 1
            entry.active_request_count += 1
            entry.last_used_at = _now()
            previous_status = entry.status
            entry.status = "generating"
            started = time.monotonic()
            deadline = started + max(0.1, float(self.settings.local_adapter_generate_timeout_seconds))

            try:
                if entry.inference_mode == "mock" or entry.base_model.startswith("mock://"):
                    mock_latency_ms = int(self._settings_for(provider_row).get("mock_latency_ms", 0))
                    if mock_latency_ms > 0:
                        time.sleep(mock_latency_ms / 1000)
                    timed_out = time.monotonic() >= deadline
                    if timed_out:
                        raise TimeoutError("Local adapter generation exceeded the configured timeout.")
                    user_message = ""
                    for message in reversed(messages):
                        if message.get("role") == "user":
                            user_message = str(message.get("content", "")).strip()
                            break
                    return (
                        f"{ProviderType.LOCAL_ADAPTER.value} mock live response: {user_message}".strip(),
                        {
                            "mode": "mock_adapter_resident",
                            "adapter_path": entry.adapter_path,
                            "base_model": entry.base_model,
                            "timed_out": False,
                            "resident": True,
                        },
                        provider_row.model_name,
                    )

                if not entry.runtime:
                    raise RuntimeError("local adapter runtime is not loaded")

                torch = entry.runtime["torch"]
                transformers = entry.runtime["transformers"]
                tokenizer = entry.runtime["tokenizer"]
                model = entry.runtime["model"]

                class DeadlineCriteria(transformers.StoppingCriteria):
                    def __init__(self, stop_at: float) -> None:
                        super().__init__()
                        self.stop_at = stop_at

                    def __call__(self, input_ids, scores, **kwargs) -> bool:  # type: ignore[override]
                        return time.monotonic() >= self.stop_at

                prompt = _render_local_prompt(messages)
                tokenized = tokenizer(prompt, return_tensors="pt")
                device = next(model.parameters()).device
                tokenized = {key: value.to(device) for key, value in tokenized.items()}

                generation_kwargs: dict[str, Any] = {
                    "max_new_tokens": min(max_tokens, int(self._settings_for(provider_row).get("max_new_tokens", 256))),
                    "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
                    "stopping_criteria": transformers.StoppingCriteriaList([DeadlineCriteria(deadline)]),
                }
                if temperature > 0.05:
                    generation_kwargs["do_sample"] = True
                    generation_kwargs["temperature"] = temperature
                else:
                    generation_kwargs["do_sample"] = False

                with torch.inference_mode():
                    generated = model.generate(**tokenized, **generation_kwargs)

                prompt_length = tokenized["input_ids"].shape[1]
                generated_ids = generated[0][prompt_length:]
                content = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
                timed_out = time.monotonic() >= deadline
                self._update_memory_snapshot(entry)
                if timed_out and not content:
                    raise TimeoutError("Local adapter generation exceeded the configured timeout.")
                return (
                    content or "No response generated from the local adapter.",
                    {
                        "mode": "local_adapter_resident",
                        "adapter_path": entry.adapter_path,
                        "base_model": entry.base_model,
                        "resident": True,
                        "load_count": entry.load_count,
                        "request_count": entry.request_count,
                        "timed_out": timed_out,
                    },
                    provider_row.model_name,
                )
            finally:
                entry.active_request_count = max(0, entry.active_request_count - 1)
                entry.last_used_at = _now()
                if entry.status == "generating":
                    entry.status = "mock_ready" if previous_status == "mock_ready" else "loaded"

    def evict(self, provider_row: ModelProvider) -> LocalAdapterRuntimeRead:
        with self._lock:
            entry = self._ensure_entry(provider_row)
            with entry.entry_lock:
                self._evict_entry(entry, reason="manual")
                return self._runtime_summary(entry, provider_row.id)

    def evict_by_provider_id(self, provider_id: UUID) -> None:
        with self._lock:
            entry = self._find_entry_by_provider_id(provider_id)
            if entry is None:
                return
            with entry.entry_lock:
                self._evict_entry(entry, reason="provider_disabled")

    def _evict_entry(self, entry: LocalAdapterRuntimeEntry, *, reason: str) -> None:
        runtime = entry.runtime
        torch_module = runtime.get("torch") if runtime else None
        model = runtime.get("model") if runtime else None
        if model is not None and hasattr(model, "cpu"):
            try:
                model.cpu()
            except Exception:
                pass
        entry.runtime = None
        entry.status = "idle"
        entry.device = None
        entry.last_error = None
        entry.evict_count += 1
        entry.last_evicted_at = _now()
        entry.last_eviction_reason = reason
        entry.memory_allocated_mb = None
        entry.memory_reserved_mb = None
        gc.collect()
        if torch_module is not None and hasattr(torch_module, "cuda") and torch_module.cuda.is_available():
            torch_module.cuda.empty_cache()

    def shutdown(self) -> None:
        with self._lock:
            for entry in list(self._entries.values()):
                with entry.entry_lock:
                    self._evict_entry(entry, reason="shutdown")


_manager: LocalAdapterRuntimeManager | None = None


def get_local_adapter_runtime_manager() -> LocalAdapterRuntimeManager:
    global _manager
    if _manager is None:
        _manager = LocalAdapterRuntimeManager()
    return _manager
