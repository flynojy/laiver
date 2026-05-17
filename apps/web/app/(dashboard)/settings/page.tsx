"use client";

import { useEffect, useMemo, useState } from "react";

import type { LocalAdapterRuntimeState, ModelProviderConfig } from "@agent/shared";

import { ModelSwitcher } from "@/components/model-switcher";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  buildProviderForm,
  toProviderCardViewModel,
  toValidationViewModel
} from "@/features/providers/mappers";
import { PROVIDER_PRESETS } from "@/features/providers/view-models";
import type {
  LocalAdapterRuntimeViewModel,
  ProviderCardViewModel,
  ProviderFormState,
  ProviderFormType,
  ProviderValidationViewModel
} from "@/features/providers/view-models";
import {
  bootstrapModelProvider,
  createModelProvider,
  evictLocalAdapter,
  listLocalAdapterRuntime,
  listModelProviders,
  updateModelProvider,
  validateModelProvider,
  warmLocalAdapter
} from "@/features/providers/client";

function ValidationBadge({ label, ok }: { label: string; ok: boolean }) {
  return (
    <Badge>
      {label}: {ok ? "ok" : "pending"}
    </Badge>
  );
}

function RuntimeSummary({ runtime }: { runtime: LocalAdapterRuntimeViewModel }) {
  return (
    <div className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-3 text-xs text-sky-900">
      <div className="flex flex-wrap gap-2">
        <Badge>{runtime.status}</Badge>
        {runtime.resident ? <Badge>resident</Badge> : <Badge>cold</Badge>}
        {runtime.device ? <Badge>{runtime.device}</Badge> : null}
      </div>
      <p className="mt-2 break-all">adapter: {runtime.adapterPath}</p>
      <p className="mt-1 break-all">base: {runtime.baseModel}</p>
      <p className="mt-1">
        loads {runtime.loadCount} / requests {runtime.requestCount} / active {runtime.activeRequestCount}
      </p>
      <p className="mt-1">
        idle {runtime.idleSeconds}s / ttl {runtime.idleTimeoutSeconds}s / timeout {runtime.generateTimeoutSeconds}s
      </p>
      {runtime.memoryAllocatedMb != null || runtime.memoryReservedMb != null ? (
        <p className="mt-1">
          memory {runtime.memoryAllocatedMb ?? 0} MB / reserved {runtime.memoryReservedMb ?? 0} MB
        </p>
      ) : null}
      {runtime.lastEvictionReason ? <p className="mt-1">last eviction: {runtime.lastEvictionReason}</p> : null}
      {runtime.error ? <p className="mt-1 text-red-700">{runtime.error}</p> : null}
    </div>
  );
}

function providerSettingsFor(form: ProviderFormState) {
  return {
    supports_streaming: true,
    supports_tool_calling: form.providerType !== "ollama",
    ...(form.providerType === "ollama" ? { num_ctx: 1024, num_predict: 256, think: false } : {})
  };
}

export default function SettingsPage() {
  const [providers, setProviders] = useState<ModelProviderConfig[]>([]);
  const [runtimeStates, setRuntimeStates] = useState<LocalAdapterRuntimeState[]>([]);
  const [validation, setValidation] = useState<ProviderValidationViewModel | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeProviderId, setActiveProviderId] = useState("");
  const [form, setForm] = useState<ProviderFormState>(buildProviderForm("openai_compatible"));

  const providerCards = useMemo(() => {
    const runtimeByProviderId = new Map(runtimeStates.map((item) => [item.provider_id, item]));
    return providers.map((provider) => toProviderCardViewModel(provider, provider.id ? runtimeByProviderId.get(provider.id) : null));
  }, [providers, runtimeStates]);

  const activeProvider = useMemo<ProviderCardViewModel | null>(
    () => providerCards.find((provider) => provider.id === activeProviderId) ?? providerCards[0] ?? null,
    [activeProviderId, providerCards]
  );
  const activePreset = PROVIDER_PRESETS[form.providerType];

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

  async function handleCreateProvider() {
    setLoading(true);
    setError("");
    try {
      const created = await createModelProvider({
        name: form.name,
        provider_type: form.providerType,
        base_url: form.baseUrl,
        model_name: form.modelName,
        api_key_ref: form.apiKeyRef || null,
        is_default: form.isDefault,
        is_enabled: form.isEnabled,
        settings: providerSettingsFor(form)
      });
      setForm(buildProviderForm(form.providerType));
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
      setValidation(toValidationViewModel(result));
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

      {error ? <div className="rounded-2xl border border-[var(--danger)] bg-[color:var(--danger)]/10 px-4 py-3 text-sm text-[var(--danger)]">{error}</div> : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <Card className="bg-[var(--surface)]">
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
            {providerCards.map((provider) => (
              <div key={provider.id} className="rounded-[1.25rem] border border-[color:var(--border)] bg-[#faf8f4] p-4">
                {provider.runtime ? (
                  <div className="mb-4">
                    <RuntimeSummary runtime={provider.runtime} />
                  </div>
                ) : null}
                <button className="w-full text-left" onClick={() => setActiveProviderId(provider.id ?? "")}>
                  <div className="flex flex-wrap gap-2">
                    <Badge>{provider.providerType}</Badge>
                    {provider.isDefault ? <Badge>default</Badge> : null}
                    {provider.isEnabled ? <Badge>enabled</Badge> : <Badge>disabled</Badge>}
                  </div>
                  <p className="mt-3 font-medium">{provider.name}</p>
                  <p className="mt-2 text-sm text-[var(--muted-foreground)]">{provider.modelName}</p>
                  <p className="mt-2 break-all text-xs text-[var(--muted-foreground)]">{provider.baseUrl}</p>
                  {provider.apiKeyRef ? (
                    <p className="mt-2 break-all text-xs text-[var(--muted-foreground)]">key ref: {provider.apiKeyRef}</p>
                  ) : null}
                </button>
                <div className="mt-4 flex flex-wrap gap-3">
                  {!provider.isDefault ? (
                    <Button variant="secondary" disabled={loading} onClick={() => handleQuickAction(provider.id ?? "", { is_default: true })}>
                      Set Default
                    </Button>
                  ) : null}
                  <Button
                    variant="secondary"
                    disabled={loading}
                    onClick={() => handleQuickAction(provider.id ?? "", { is_enabled: !provider.isEnabled })}
                  >
                    {provider.isEnabled ? "Disable" : "Enable"}
                  </Button>
                  <Button variant="secondary" disabled={loading} onClick={() => handleValidate(provider.id)}>
                    Validate
                  </Button>
                  {provider.providerType === "local_adapter" && provider.id ? (
                    <Button variant="secondary" disabled={loading} onClick={() => handleWarmLocalAdapter(provider.id ?? "")}>
                      Warm
                    </Button>
                  ) : null}
                  {provider.providerType === "local_adapter" && provider.id ? (
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
          <ModelSwitcher
            providers={providerCards}
            selectedProviderId={activeProviderId}
            validation={validation}
            loading={loading}
            onSelect={setActiveProviderId}
            onSwitchDefault={(providerId) => handleQuickAction(providerId, { is_default: true })}
            onValidate={handleValidate}
          />

          <Card className="bg-[var(--surface)]">
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
                  value={form.providerType}
                  onChange={(event) => setForm(buildProviderForm(event.target.value as ProviderFormType))}
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
                  value={form.baseUrl}
                  onChange={(event) => setForm((current) => ({ ...current, baseUrl: event.target.value }))}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="provider-model">Model Name</Label>
                <Input
                  id="provider-model"
                  value={form.modelName}
                  onChange={(event) => setForm((current) => ({ ...current, modelName: event.target.value }))}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="provider-api-key-ref">API Key Ref</Label>
                <Input
                  id="provider-api-key-ref"
                  value={form.apiKeyRef}
                  placeholder={form.providerType === "ollama" ? "Leave empty for local Ollama" : "env:OPENAI_API_KEY"}
                  onChange={(event) => setForm((current) => ({ ...current, apiKeyRef: event.target.value }))}
                />
                <p className="text-xs text-[var(--muted-foreground)]">
                  Use `env:YOUR_KEY_NAME` or `literal:actual-key`. Ollama can stay empty.
                </p>
              </div>

              <label className="flex items-center gap-3 text-sm">
                <input
                  type="checkbox"
                  checked={form.isDefault}
                  onChange={(event) => setForm((current) => ({ ...current, isDefault: event.target.checked }))}
                />
                Set as default provider
              </label>

              <label className="flex items-center gap-3 text-sm">
                <input
                  type="checkbox"
                  checked={form.isEnabled}
                  onChange={(event) => setForm((current) => ({ ...current, isEnabled: event.target.checked }))}
                />
                Enable immediately
              </label>

              <Button disabled={loading} onClick={handleCreateProvider}>
                Add Provider
              </Button>
            </CardContent>
          </Card>

          <Card className="bg-[var(--surface)]">
            <CardHeader>
              <CardTitle>Validation Result</CardTitle>
              <CardDescription>Check completion, streaming, and tool-calling support before switching the agent to a new model.</CardDescription>
            </CardHeader>
            <CardContent>
              {validation ? (
                <div className="space-y-4">
                  <div className="flex flex-wrap gap-2">
                    <Badge>{validation.mode}</Badge>
                    <Badge>{validation.healthStatus}</Badge>
                    <Badge>{validation.providerType}</Badge>
                    <ValidationBadge label="completion" ok={validation.completionOk} />
                    <ValidationBadge label="stream" ok={validation.streamOk} />
                    <ValidationBadge label="tool" ok={validation.toolCallOk} />
                  </div>
                  <p className="text-sm text-[var(--muted-foreground)]">
                    {validation.providerName} / {validation.modelName}
                  </p>
                  <p className="text-xs text-[var(--muted-foreground)]">
                    API key configured: {validation.apiKeyConfigured ? "yes" : "no"}
                  </p>
                  <p className="text-xs text-[var(--muted-foreground)]">
                    Route: {validation.routePolicy} / Fallback: {validation.fallbackPolicy}
                    {validation.fallbackAvailable ? " available" : " unavailable"}
                  </p>
                  <div className="space-y-3 text-xs text-[var(--muted-foreground)]">
                    <div>
                      <p className="font-medium text-[color:var(--foreground)]">Completion Preview</p>
                      <p className="mt-1 whitespace-pre-wrap">{validation.completionPreview || "No completion content returned."}</p>
                    </div>
                    <div>
                      <p className="font-medium text-[color:var(--foreground)]">Stream Preview</p>
                      <p className="mt-1 whitespace-pre-wrap">{validation.streamPreview || "No stream content returned."}</p>
                    </div>
                    <div>
                      <p className="font-medium text-[color:var(--foreground)]">Tool Calls</p>
                      <pre className="mt-1 overflow-x-auto rounded-2xl bg-[#faf8f4] p-3 leading-6">
                        {validation.toolCallsJson}
                      </pre>
                    </div>
                  </div>
                  {validation.errorLabel ? (
                    <p className="rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
                      {validation.errorLabel}
                    </p>
                  ) : null}
                  {validation.recommendation ? (
                    <p className="rounded-2xl border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-800">
                      {validation.recommendation}
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

          {activeProvider?.providerType === "local_adapter" && activeProvider.id ? (
            <Card className="bg-white/88">
              <CardHeader>
                <CardTitle>Resident Runtime</CardTitle>
                <CardDescription>Keep the selected local adapter warm in memory so reply latency stays stable between turns.</CardDescription>
              </CardHeader>
              <CardContent>
                {activeProvider.runtime ? (
                  <div className="space-y-3">
                    <RuntimeSummary runtime={activeProvider.runtime} />
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
