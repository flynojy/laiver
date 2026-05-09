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
    <Card className="bg-white/88">
      <CardHeader>
        <CardTitle>Model Switcher</CardTitle>
        <CardDescription>Switch the agent default provider after checking health and fallback status.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-lg border border-[color:var(--border)] bg-[var(--muted)] p-4">
          <div className="flex flex-wrap gap-2">
            <Badge>current</Badge>
            {defaultProvider ? <Badge>{defaultProvider.provider_type}</Badge> : null}
            {defaultValidation ? <Badge>{defaultValidation.health_status}</Badge> : null}
          </div>
          <p className="mt-3 font-medium">{defaultProvider?.name ?? "No default provider"}</p>
          <p className="mt-1 text-sm text-[var(--muted-foreground)]">
            {defaultProvider ? defaultProvider.model_name : "Create or bootstrap a provider before switching."}
          </p>
          {defaultValidation ? (
            <p className="mt-2 text-xs text-[var(--muted-foreground)]">
              fallback {defaultValidation.fallback_policy}{" "}
              {defaultValidation.fallback_available ? "available" : "unavailable"}
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
                  "w-full rounded-lg border p-3 text-left transition",
                  isSelected ? "border-[var(--accent)] bg-white" : "border-[color:var(--border)] bg-[var(--muted)]"
                ].join(" ")}
                onClick={() => provider.id && onSelect(provider.id)}
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap gap-2">
                      <Badge>{provider.provider_type}</Badge>
                      <Badge>{statusLabel(provider, validation)}</Badge>
                      {provider.is_default ? <Badge>default</Badge> : null}
                    </div>
                    <p className="mt-2 font-medium">{provider.name}</p>
                    <p className="mt-1 text-xs text-[var(--muted-foreground)]">{provider.model_name}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="secondary"
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
