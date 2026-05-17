"use client";

import type { ModelProviderConfig, ModelProviderValidationResult, UUID } from "@agent/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type ModelSwitcherProps = {
  providers: ModelProviderConfig[];
  selectedProviderId: UUID | "";
  validation: ModelProviderValidationResult | null;
  loading: boolean;
  onSelect: (providerId: UUID) => void;
  onSwitchDefault: (providerId: UUID) => void;
  onValidate: (providerId: UUID) => void;
};

function statusLabel(provider: ModelProviderConfig, validation: ModelProviderValidationResult | null) {
  if (!provider.is_enabled) {
    return "disabled";
  }
  if (validation && validation.provider_id === provider.id) {
    return validation.health_status;
  }
  return provider.is_default ? "current" : "available";
}

function statusVariant(label: string): "sync" | "standby" | "alert" | "idle" | "default" {
  if (label === "healthy" || label === "current") return "sync";
  if (label === "available") return "standby";
  if (label === "degraded") return "standby";
  if (label === "unhealthy" || label === "disabled") return "alert";
  return "default";
}

export function ModelSwitcher({
  providers,
  selectedProviderId,
  validation,
  loading,
  onSelect,
  onSwitchDefault,
  onValidate
}: ModelSwitcherProps) {
  const defaultProvider = providers.find((provider) => provider.is_default) ?? providers[0] ?? null;
  const selectedProvider = providers.find((provider) => provider.id === selectedProviderId) ?? defaultProvider;
  const defaultValidation =
    validation && validation.provider_id === defaultProvider?.id ? validation : null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Model Switcher</CardTitle>
        <CardDescription>
          Switch the agent default provider after checking health and fallback status.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-[8px] border border-[color:var(--border-strong)] bg-[var(--surface-2)] p-4">
          <div className="flex flex-wrap gap-2">
            <Badge variant="alert">current</Badge>
            {defaultProvider ? <Badge>{defaultProvider.provider_type}</Badge> : null}
            {defaultValidation ? (
              <Badge variant={statusVariant(defaultValidation.health_status)}>
                {defaultValidation.health_status}
              </Badge>
            ) : null}
          </div>
          <p className="mt-3 font-medium">{defaultProvider?.name ?? "No default provider"}</p>
          <p className="mt-1 font-mono text-xs text-[var(--foreground-muted)]">
            {defaultProvider ? defaultProvider.model_name : "Create or bootstrap a provider before switching."}
          </p>
          {defaultValidation ? (
            <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.16em] text-[var(--foreground-muted)]">
              FALLBACK {defaultValidation.fallback_policy}{" "}
              {defaultValidation.fallback_available ? "AVAILABLE" : "UNAVAILABLE"}
            </p>
          ) : null}
        </div>

        <div className="space-y-2">
          {providers.map((provider) => {
            const isSelected = provider.id === selectedProvider?.id;
            const canSwitch = Boolean(provider.id) && provider.is_enabled && !provider.is_default;
            return (
              <button
                key={provider.id}
                type="button"
                className={[
                  "w-full rounded-[8px] border p-3 text-left transition",
                  isSelected
                    ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                    : "border-[color:var(--border)] bg-[var(--surface-2)] hover:border-[color:var(--border-strong)]"
                ].join(" ")}
                onClick={() => provider.id && onSelect(provider.id)}
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap gap-2">
                      <Badge>{provider.provider_type}</Badge>
                      <Badge variant={statusVariant(statusLabel(provider, validation))}>
                        {statusLabel(provider, validation)}
                      </Badge>
                      {provider.is_default ? <Badge variant="alert">default</Badge> : null}
                    </div>
                    <p className="mt-2 font-medium">{provider.name}</p>
                    <p className="mt-1 font-mono text-xs text-[var(--foreground-muted)]">
                      {provider.model_name}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      disabled={loading || !provider.id}
                      onClick={(event) => {
                        event.stopPropagation();
                        if (provider.id) {
                          onValidate(provider.id);
                        }
                      }}
                    >
                      Check
                    </Button>
                    {canSwitch ? (
                      <Button
                        type="button"
                        size="sm"
                        disabled={loading}
                        onClick={(event) => {
                          event.stopPropagation();
                          if (provider.id) {
                            onSwitchDefault(provider.id);
                          }
                        }}
                      >
                        Use
                      </Button>
                    ) : null}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
