import type {
  LocalAdapterRuntimeState,
  ModelProviderConfig,
  ModelProviderValidationResult
} from "@agent/shared";

import type {
  LocalAdapterRuntimeViewModel,
  ProviderCardViewModel,
  ProviderFormState,
  ProviderFormType,
  ProviderValidationViewModel
} from "./view-models";
import { PROVIDER_PRESETS } from "./view-models";

export function buildProviderForm(providerType: ProviderFormType): ProviderFormState {
  const preset = PROVIDER_PRESETS[providerType];
  return {
    name: preset.name,
    providerType,
    baseUrl: preset.baseUrl,
    modelName: preset.modelName,
    apiKeyRef: preset.apiKeyRef,
    isDefault: false,
    isEnabled: true
  };
}

export function toProviderCardViewModel(
  provider: ModelProviderConfig,
  runtime?: LocalAdapterRuntimeState | null
): ProviderCardViewModel {
  return {
    id: provider.id,
    name: provider.name,
    providerType: provider.provider_type,
    modelName: provider.model_name,
    baseUrl: provider.base_url,
    apiKeyRef: provider.api_key_ref,
    isDefault: provider.is_default,
    isEnabled: provider.is_enabled ?? true,
    statusLabel: provider.is_default ? "default" : provider.is_enabled ?? true ? "enabled" : "disabled",
    runtime: runtime ? toRuntimeViewModel(runtime) : null
  };
}

export function toRuntimeViewModel(runtime: LocalAdapterRuntimeState): LocalAdapterRuntimeViewModel {
  return {
    status: runtime.status,
    resident: runtime.resident,
    device: runtime.device,
    adapterPath: runtime.adapter_path,
    baseModel: runtime.base_model,
    loadCount: runtime.load_count,
    requestCount: runtime.request_count,
    activeRequestCount: runtime.active_request_count,
    idleSeconds: runtime.idle_seconds ?? 0,
    idleTimeoutSeconds: runtime.idle_timeout_seconds,
    generateTimeoutSeconds: runtime.generate_timeout_seconds,
    memoryAllocatedMb: runtime.memory_allocated_mb,
    memoryReservedMb: runtime.memory_reserved_mb,
    lastEvictionReason: runtime.last_eviction_reason,
    error: runtime.error
  };
}

export function toValidationViewModel(result: ModelProviderValidationResult): ProviderValidationViewModel {
  return {
    providerId: result.provider_id,
    providerName: result.provider_name,
    modelName: result.model_name,
    providerType: result.provider_type,
    mode: result.mode,
    healthStatus: result.health_status,
    routePolicy: result.route_policy,
    fallbackPolicy: result.fallback_policy,
    fallbackAvailable: result.fallback_available,
    apiKeyConfigured: result.api_key_configured,
    completionOk: result.completion_ok,
    streamOk: result.stream_ok,
    toolCallOk: result.tool_call_ok,
    completionPreview: result.completion_preview,
    streamPreview: result.stream_preview,
    toolCallsJson: JSON.stringify(result.tool_calls, null, 2),
    errorLabel: result.error_code ? `${result.error_code}: ${result.error}` : result.error,
    recommendation: result.recommendation
  };
}
