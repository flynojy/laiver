"use client";

import { useEffect, useMemo, useState } from "react";

import type {
  LocalAdapterRuntimeState,
  ModelProviderConfig,
  ModelProviderValidationResult,
  ProviderType
} from "@agent/shared";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  bootstrapModelProvider,
  createModelProvider,
  evictLocalAdapter,
  listModelProviders,
  listLocalAdapterRuntime,
  updateModelProvider,
  validateModelProvider,
  warmLocalAdapter
} from "@/lib/api";

type ManualProviderType = Exclude<ProviderType, "local_adapter">;

type ProviderFormState = {
  name: string;
  provider_type: ManualProviderType;
  base_url: string;
  model_name: string;
  api_key_ref: string;
  is_default: boolean;
  is_enabled: boolean;
};

const PROVIDER_PRESETS: Record<
  ManualProviderType,
  { name: string; base_url: string; model_name: string; api_key_ref: string; helper: string }
> = {
  deepseek: {
    name: "DeepSeek",
    base_url: "https://api.deepseek.com",
    model_name: "deepseek-chat",
    api_key_ref: "env:DEEPSEEK_API_KEY",
    helper: "适合直接接 DeepSeek 官方 API。"
  },
  openai_compatible: {
    name: "OpenAI Compatible",
    base_url: "https://api.openai.com/v1",
    model_name: "gpt-4o-mini",
    api_key_ref: "env:OPENAI_API_KEY",
    helper: "适合 OpenAI、Groq、Together、Moonshot 等兼容 Chat Completions 的服务。"
  },
  ollama: {
    name: "Ollama",
    base_url: "http://localhost:11434",
    model_name: "qwen2.5:7b",
    api_key_ref: "",
    helper: "适合本机 Ollama。默认走本地 `http://localhost:11434/api/chat`。"
  }
};

function ValidationBadge({ label, ok }: { label: string; ok: boolean }) {
  return <Badge>{label}: {ok ? "ok" : "pending"}</Badge>;
}

function buildPresetForm(providerType: ManualProviderType): ProviderFormState {
  const preset = PROVIDER_PRESETS[providerType];
  return {
    name: preset.name,
    provider_type: providerType,
    base_url: preset.base_url,
    model_name: preset.model_name,
    api_key_ref: preset.api_key_ref,
    is_default: false,
    is_enabled: true
  };
}

export default function SettingsPage() {
  const [providers, setProviders] = useState<ModelProviderConfig[]>([]);
  const [runtimeStates, setRuntimeStates] = useState<LocalAdapterRuntimeState[]>([]);
  const [validation, setValidation] = useState<ModelProviderValidationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeProviderId, setActiveProviderId] = useState("");
  const [form, setForm] = useState<ProviderFormState>(buildPresetForm("openai_compatible"));

  async function refreshProviders(activeId?: string) {
    await bootstrapModelProvider();
    const [rows, localRuntimeRows] = await Promise.all([listModelProviders(), listLocalAdapterRuntime()]);
    setProviders(rows);
    setRuntimeStates(localRuntimeRows);
    setActiveProviderId(activeId ?? rows[0]?.id ?? "");
  }

  useEffect(() => {
    refreshProviders().catch((reason) => {
      setError(reason instanceof Error ? reason.message : "Settings bootstrap failed.");
    });
  }, []);

  const activeProvider = useMemo(
    () => providers.find((provider) => provider.id === activeProviderId) ?? providers[0] ?? null,
    [activeProviderId, providers]
  );
  const runtimeStateByProviderId = useMemo(
    () => new Map(runtimeStates.map((item) => [item.provider_id, item])),
    [runtimeStates]
  );
  const activePreset = PROVIDER_PRESETS[form.provider_type];

  async function handleCreateProvider() {
    setLoading(true);
    setError("");
    try {
      const created = await createModelProvider({
        ...form,
        api_key_ref: form.api_key_ref || null,
        settings: {
          supports_streaming: form.provider_type !== "ollama" ? true : true,
          supports_tool_calling: form.provider_type !== "ollama"
        }
      });
      setForm(buildPresetForm(form.provider_type));
      await refreshProviders(created.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Provider creation failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleQuickAction(providerId: string, payload: Parameters<typeof updateModelProvider>[1]) {
    setLoading(true);
    setError("");
    try {
      await updateModelProvider(providerId, payload);
      await refreshProviders(providerId);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Provider update failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleValidate(providerId?: string) {
    setLoading(true);
    setError("");
    try {
      const result = await validateModelProvider(providerId ? { provider_id: providerId } : {});
      setValidation(result);
      await refreshProviders(providerId ?? activeProviderId);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Provider validation failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleWarmLocalAdapter(providerId: string) {
    setLoading(true);
    setError("");
    try {
      await warmLocalAdapter(providerId);
      await refreshProviders(providerId);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Local adapter warm failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleEvictLocalAdapter(providerId: string) {
    setLoading(true);
    setError("");
    try {
      await evictLocalAdapter(providerId);
      await refreshProviders(providerId);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Local adapter evict failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="System Settings"
        title="Model Providers"
        description="Connect external APIs and local models in one registry, then choose which provider the agent uses by default."
        badge="External + Local"
      />

      {error ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <Card className="bg-white/88">
          <CardHeader className="flex flex-row items-center justify-between gap-4">
            <div>
              <CardTitle>Provider Registry</CardTitle>
              <CardDescription>Current providers can be enabled, disabled, switched to default, and validated individually.</CardDescription>
            </div>
            <div className="flex gap-3">
              <Button
                variant="secondary"
                disabled={loading}
                onClick={async () => {
                  setLoading(true);
                  setError("");
                  try {
                    await refreshProviders(activeProviderId);
                  } catch (reason) {
                    setError(reason instanceof Error ? reason.message : "Provider refresh failed.");
                  } finally {
                    setLoading(false);
                  }
                }}
              >
                Refresh
              </Button>
              <Button disabled={loading} onClick={() => handleValidate(activeProvider?.id)}>
                {loading ? "Checking..." : "Validate Selected"}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {providers.map((provider) => (
              <div key={provider.id} className="rounded-[1.25rem] border border-[color:var(--border)] bg-[#faf8f4] p-4">
                {provider.provider_type === "local_adapter" && provider.id ? (
                  (() => {
                    const runtimeState = runtimeStateByProviderId.get(provider.id);
                    return runtimeState ? (
                      <div className="mb-4 rounded-lg border border-sky-200 bg-sky-50 px-3 py-3 text-xs text-sky-900">
                        <div className="flex flex-wrap gap-2">
                          <Badge>{runtimeState.status}</Badge>
                          {runtimeState.resident ? <Badge>resident</Badge> : <Badge>cold</Badge>}
                          {runtimeState.device ? <Badge>{runtimeState.device}</Badge> : null}
                        </div>
                        <p className="mt-2 break-all">adapter: {runtimeState.adapter_path}</p>
                        <p className="mt-1 break-all">base: {runtimeState.base_model}</p>
                        <p className="mt-1">
                          loads {runtimeState.load_count} / requests {runtimeState.request_count} / active {runtimeState.active_request_count}
                        </p>
                        <p className="mt-1">
                          idle {runtimeState.idle_seconds ?? 0}s / ttl {runtimeState.idle_timeout_seconds}s / timeout {runtimeState.generate_timeout_seconds}s
                        </p>
                        {runtimeState.memory_allocated_mb != null || runtimeState.memory_reserved_mb != null ? (
                          <p className="mt-1">
                            memory {runtimeState.memory_allocated_mb ?? 0} MB / reserved {runtimeState.memory_reserved_mb ?? 0} MB
                          </p>
                        ) : null}
                        {runtimeState.last_eviction_reason ? (
                          <p className="mt-1">
                            last eviction: {runtimeState.last_eviction_reason}
                          </p>
                        ) : null}
                        {runtimeState.error ? <p className="mt-1 text-red-700">{runtimeState.error}</p> : null}
                      </div>
                    ) : null;
                  })()
                ) : null}
                <button className="w-full text-left" onClick={() => setActiveProviderId(provider.id ?? "")}>
                  <div className="flex flex-wrap gap-2">
                    <Badge>{provider.provider_type}</Badge>
                    {provider.is_default ? <Badge>default</Badge> : null}
                    {provider.is_enabled ? <Badge>enabled</Badge> : <Badge>disabled</Badge>}
                  </div>
                  <p className="mt-3 font-medium">{provider.name}</p>
                  <p className="mt-2 text-sm text-[var(--muted-foreground)]">{provider.model_name}</p>
                  <p className="mt-2 break-all text-xs text-[var(--muted-foreground)]">{provider.base_url}</p>
                  {provider.api_key_ref ? (
                    <p className="mt-2 break-all text-xs text-[var(--muted-foreground)]">key ref: {provider.api_key_ref}</p>
                  ) : null}
                </button>
                <div className="mt-4 flex flex-wrap gap-3">
                  {!provider.is_default ? (
                    <Button variant="secondary" disabled={loading} onClick={() => handleQuickAction(provider.id ?? "", { is_default: true })}>
                      Set Default
                    </Button>
                  ) : null}
                  <Button
                    variant="secondary"
                    disabled={loading}
                    onClick={() => handleQuickAction(provider.id ?? "", { is_enabled: !provider.is_enabled })}
                  >
                    {provider.is_enabled ? "Disable" : "Enable"}
                  </Button>
                  <Button variant="secondary" disabled={loading} onClick={() => handleValidate(provider.id)}>
                    Validate
                  </Button>
                  {provider.provider_type === "local_adapter" && provider.id ? (
                    <Button variant="secondary" disabled={loading} onClick={() => handleWarmLocalAdapter(provider.id ?? "")}>
                      Warm
                    </Button>
                  ) : null}
                  {provider.provider_type === "local_adapter" && provider.id ? (
                    <Button variant="secondary" disabled={loading} onClick={() => handleEvictLocalAdapter(provider.id ?? "")}>
                      Evict
                    </Button>
                  ) : null}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Add Provider</CardTitle>
              <CardDescription>
                Create a new provider for DeepSeek, an OpenAI-compatible API, or a local Ollama runtime. Completed fine-tune adapters appear here automatically.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="provider-type">Provider Type</Label>
                <select
                  id="provider-type"
                  className="h-11 w-full rounded-md border border-[color:var(--border)] bg-white px-3 text-sm"
                  value={form.provider_type}
                  onChange={(event) => setForm(buildPresetForm(event.target.value as ManualProviderType))}
                >
                  <option value="openai_compatible">OpenAI Compatible</option>
                  <option value="deepseek">DeepSeek</option>
                  <option value="ollama">Ollama</option>
                </select>
                <p className="text-xs text-[var(--muted-foreground)]">{activePreset.helper}</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="provider-name">Name</Label>
                <Input
                  id="provider-name"
                  value={form.name}
                  onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="provider-base-url">Base URL</Label>
                <Input
                  id="provider-base-url"
                  value={form.base_url}
                  onChange={(event) => setForm((current) => ({ ...current, base_url: event.target.value }))}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="provider-model">Model Name</Label>
                <Input
                  id="provider-model"
                  value={form.model_name}
                  onChange={(event) => setForm((current) => ({ ...current, model_name: event.target.value }))}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="provider-api-key-ref">API Key Ref</Label>
                <Input
                  id="provider-api-key-ref"
                  value={form.api_key_ref}
                  placeholder={form.provider_type === "ollama" ? "Leave empty for local Ollama" : "env:OPENAI_API_KEY"}
                  onChange={(event) => setForm((current) => ({ ...current, api_key_ref: event.target.value }))}
                />
                <p className="text-xs text-[var(--muted-foreground)]">
                  Use `env:YOUR_KEY_NAME` or `literal:actual-key`. Ollama can stay empty.
                </p>
              </div>

              <label className="flex items-center gap-3 text-sm">
                <input
                  type="checkbox"
                  checked={form.is_default}
                  onChange={(event) => setForm((current) => ({ ...current, is_default: event.target.checked }))}
                />
                Set as default provider
              </label>

              <label className="flex items-center gap-3 text-sm">
                <input
                  type="checkbox"
                  checked={form.is_enabled}
                  onChange={(event) => setForm((current) => ({ ...current, is_enabled: event.target.checked }))}
                />
                Enable immediately
              </label>

              <Button disabled={loading} onClick={handleCreateProvider}>
                Add Provider
              </Button>
            </CardContent>
          </Card>

          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Validation Result</CardTitle>
              <CardDescription>Check completion, streaming, and tool-calling support before switching the agent to a new model.</CardDescription>
            </CardHeader>
            <CardContent>
              {validation ? (
                <div className="space-y-4">
                  <div className="flex flex-wrap gap-2">
                    <Badge>{validation.mode}</Badge>
                    <Badge>{validation.provider_type}</Badge>
                    <ValidationBadge label="completion" ok={validation.completion_ok} />
                    <ValidationBadge label="stream" ok={validation.stream_ok} />
                    <ValidationBadge label="tool" ok={validation.tool_call_ok} />
                  </div>
                  <p className="text-sm text-[var(--muted-foreground)]">
                    {validation.provider_name} / {validation.model_name}
                  </p>
                  <p className="text-xs text-[var(--muted-foreground)]">
                    API key configured: {validation.api_key_configured ? "yes" : "no"}
                  </p>
                  <div className="space-y-3 text-xs text-[var(--muted-foreground)]">
                    <div>
                      <p className="font-medium text-[color:var(--foreground)]">Completion Preview</p>
                      <p className="mt-1 whitespace-pre-wrap">{validation.completion_preview || "No completion content returned."}</p>
                    </div>
                    <div>
                      <p className="font-medium text-[color:var(--foreground)]">Stream Preview</p>
                      <p className="mt-1 whitespace-pre-wrap">{validation.stream_preview || "No stream content returned."}</p>
                    </div>
                    <div>
                      <p className="font-medium text-[color:var(--foreground)]">Tool Calls</p>
                      <pre className="mt-1 overflow-x-auto rounded-2xl bg-[#faf8f4] p-3 leading-6">
                        {JSON.stringify(validation.tool_calls, null, 2)}
                      </pre>
                    </div>
                  </div>
                  {validation.error ? (
                    <p className="rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
                      {validation.error}
                    </p>
                  ) : null}
                </div>
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">
                  Build a provider first, then run validation. For local-only testing, `mock://success/openai` and `mock://success/ollama`
                  also work as deterministic dry-run endpoints.
                </p>
              )}
            </CardContent>
          </Card>

          {activeProvider?.provider_type === "local_adapter" && activeProvider.id ? (
            <Card className="bg-white/88">
              <CardHeader>
                <CardTitle>Resident Runtime</CardTitle>
                <CardDescription>Keep the selected local adapter warm in memory so reply latency stays stable between turns.</CardDescription>
              </CardHeader>
              <CardContent>
                {runtimeStateByProviderId.get(activeProvider.id) ? (
                  <div className="space-y-3 text-sm">
                    <div className="flex flex-wrap gap-2">
                      <Badge>{runtimeStateByProviderId.get(activeProvider.id)?.status}</Badge>
                      {runtimeStateByProviderId.get(activeProvider.id)?.resident ? <Badge>resident</Badge> : <Badge>cold</Badge>}
                      {runtimeStateByProviderId.get(activeProvider.id)?.device ? (
                        <Badge>{runtimeStateByProviderId.get(activeProvider.id)?.device}</Badge>
                      ) : null}
                    </div>
                    <p className="break-all text-[var(--muted-foreground)]">
                      {runtimeStateByProviderId.get(activeProvider.id)?.adapter_path}
                    </p>
                    <p className="text-[var(--muted-foreground)]">
                      load {runtimeStateByProviderId.get(activeProvider.id)?.load_count} / request{" "}
                      {runtimeStateByProviderId.get(activeProvider.id)?.request_count} / active{" "}
                      {runtimeStateByProviderId.get(activeProvider.id)?.active_request_count}
                    </p>
                    <p className="text-[var(--muted-foreground)]">
                      idle {runtimeStateByProviderId.get(activeProvider.id)?.idle_seconds ?? 0}s / ttl{" "}
                      {runtimeStateByProviderId.get(activeProvider.id)?.idle_timeout_seconds}s / timeout{" "}
                      {runtimeStateByProviderId.get(activeProvider.id)?.generate_timeout_seconds}s
                    </p>
                    {runtimeStateByProviderId.get(activeProvider.id)?.memory_allocated_mb != null ||
                    runtimeStateByProviderId.get(activeProvider.id)?.memory_reserved_mb != null ? (
                      <p className="text-[var(--muted-foreground)]">
                        memory {runtimeStateByProviderId.get(activeProvider.id)?.memory_allocated_mb ?? 0} MB / reserved{" "}
                        {runtimeStateByProviderId.get(activeProvider.id)?.memory_reserved_mb ?? 0} MB
                      </p>
                    ) : null}
                    <div className="flex flex-wrap gap-3">
                      <Button disabled={loading} onClick={() => handleWarmLocalAdapter(activeProvider.id ?? "")}>
                        Warm Selected
                      </Button>
                      <Button variant="secondary" disabled={loading} onClick={() => handleEvictLocalAdapter(activeProvider.id ?? "")}>
                        Evict Selected
                      </Button>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">This local adapter has not reported runtime state yet.</p>
                )}
              </CardContent>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
