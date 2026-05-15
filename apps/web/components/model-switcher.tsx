"use client";

import type { UUID } from "@agent/shared";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ProviderCardViewModel, ProviderValidationViewModel } from "@/features/providers/view-models";

type ModelSwitcherProps = {
  providers: ProviderCardViewModel[];
  selectedProviderId: UUID | "";
  validation: ProviderValidationViewModel | null;
  loading: boolean;
  onSelect: (providerId: UUID) => void;
  onSwitchDefault: (providerId: UUID) => void;
  onValidate: (providerId: UUID) => void;
};

export function ModelSwitcher({
  providers,
  selectedProviderId,
  validation,
  loading,
  onSelect,
  onSwitchDefault,
  onValidate
}: ModelSwitcherProps) {
  const defaultProvider = providers.find((provider) => provider.isDefault) ?? providers[0] ?? null;
  const selectedProvider = providers.find((provider) => provider.id === selectedProviderId) ?? defaultProvider;
  const defaultValidation = validation && validation.providerId === defaultProvider?.id ? validation : null;

  return (
    <Card className="bg-white/88">
      <CardHeader>
        <CardTitle>Model Switcher</CardTitle>
        <CardDescription>Switch the agent default provider after checking health and fallback status.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-lg border border-[color:var(--border)] bg-[#faf8f4] p-4">
          <div className="flex flex-wrap gap-2">
            <Badge>current</Badge>
            {defaultProvider ? <Badge>{defaultProvider.providerType}</Badge> : null}
            {defaultValidation ? <Badge>{defaultValidation.healthStatus}</Badge> : null}
          </div>
          <p className="mt-3 font-medium">{defaultProvider?.name ?? "No default provider"}</p>
          <p className="mt-1 text-sm text-[var(--muted-foreground)]">
            {defaultProvider ? defaultProvider.modelName : "Create or bootstrap a provider before switching."}
          </p>
          {defaultValidation ? (
            <p className="mt-2 text-xs text-[var(--muted-foreground)]">
              fallback {defaultValidation.fallbackPolicy} {defaultValidation.fallbackAvailable ? "available" : "unavailable"}
            </p>
          ) : null}
        </div>

        <div className="space-y-2">
          {providers.map((provider) => {
            const isSelected = provider.id === selectedProvider?.id;
            const canSwitch = Boolean(provider.id) && provider.isEnabled && !provider.isDefault;
            return (
              <button
                key={provider.id}
                type="button"
                className={[
                  "w-full rounded-lg border p-3 text-left transition",
                  isSelected ? "border-[var(--accent)] bg-white" : "border-[color:var(--border)] bg-[#faf8f4]"
                ].join(" ")}
                onClick={() => provider.id && onSelect(provider.id)}
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap gap-2">
                      <Badge>{provider.providerType}</Badge>
                      <Badge>{provider.statusLabel}</Badge>
                      {provider.isDefault ? <Badge>default</Badge> : null}
                    </div>
                    <p className="mt-2 font-medium">{provider.name}</p>
                    <p className="mt-1 text-xs text-[var(--muted-foreground)]">{provider.modelName}</p>
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
