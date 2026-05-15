"use client";

import { useEffect, useMemo, useState } from "react";

import type { SkillInvocationRecord, SkillRecord } from "@agent/shared";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  deleteSkill,
  disableSkill,
  enableSkill,
  installSkillPackage,
  listSkillInvocations,
  listSkills,
  seedSkills
} from "@/features/skills/client";

import { toSkillCardViewModel, toSkillInvocationViewModel } from "@/features/skills/mappers";

function InvocationList({ invocations }: { invocations: ReturnType<typeof toSkillInvocationViewModel>[] }) {
  if (invocations.length === 0) {
    return <p className="text-sm text-[var(--muted-foreground)]">No invocation records yet.</p>;
  }

  return (
    <div className="space-y-3">
      {invocations.map((item) => (
        <div key={item.id} className="rounded-[1.25rem] border border-[color:var(--border)] bg-[#fffdf9] p-4">
          <div className="flex flex-wrap gap-2">
            {item.badges.map((badge) => (
              <Badge key={badge}>{badge}</Badge>
            ))}
          </div>
          <p className="mt-2 text-xs text-[var(--muted-foreground)]">{item.traceId}</p>
          <p className="mt-1 text-xs text-[var(--muted-foreground)]">{item.timingLabel}</p>
          <pre className="mt-3 overflow-x-auto rounded-2xl bg-[#faf8f4] p-3 text-xs leading-6">
            {item.outputJson}
          </pre>
          {item.error ? <p className="mt-2 text-xs text-red-600">{item.error}</p> : null}
        </div>
      ))}
    </div>
  );
}

export default function SkillsPage() {
  const [skills, setSkills] = useState<SkillRecord[]>([]);
  const [invocations, setInvocations] = useState<SkillInvocationRecord[]>([]);
  const [activeSkillId, setActiveSkillId] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [selectedPackage, setSelectedPackage] = useState<File | null>(null);

  async function refresh(activeId?: string) {
    const [skillRows, invocationRows] = await Promise.all([listSkills(), listSkillInvocations()]);
    setSkills(skillRows);
    setInvocations(invocationRows);
    setActiveSkillId(activeId ?? skillRows[0]?.id ?? "");
  }

  useEffect(() => {
    async function bootstrap() {
      await seedSkills();
      await refresh();
    }

    bootstrap().catch((reason) => {
      setError(reason instanceof Error ? reason.message : "Skill page bootstrap failed.");
    });
  }, []);

  const activeSkill = useMemo(
    () => skills.find((skill) => skill.id === activeSkillId) ?? skills[0] ?? null,
    [activeSkillId, skills]
  );
  const activeSkillViewModel = useMemo(
    () => (activeSkill ? toSkillCardViewModel(activeSkill) : null),
    [activeSkill]
  );
  const invocationViewModels = useMemo(() => invocations.slice(0, 8).map(toSkillInvocationViewModel), [invocations]);

  async function handleToggle(skill: SkillRecord) {
    setLoading(true);
    setError("");
    setStatus("");
    try {
      if (skill.status === "active") {
        await disableSkill(skill.id);
        setStatus(`${skill.title} disabled.`);
      } else {
        await enableSkill(skill.id);
        setStatus(`${skill.title} enabled.`);
      }
      await refresh(skill.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Skill status update failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleInstall() {
    if (!selectedPackage) {
      setError("Choose a skill package first.");
      return;
    }

    setLoading(true);
    setError("");
    setStatus("");
    try {
      const skill = await installSkillPackage(selectedPackage);
      setSelectedPackage(null);
      setStatus(`${skill.title} installed.`);
      await refresh(skill.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Skill install failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRemove(skill: SkillRecord) {
    setLoading(true);
    setError("");
    setStatus("");
    try {
      await deleteSkill(skill.id);
      setStatus(`${skill.title} removed.`);
      await refresh(skills.find((item) => item.id !== skill.id)?.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Skill removal failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Skill Runtime"
        title="Skill Registry"
        description="Install community skill packages, sync builtin skills, and inspect the runtime state that the agent actually uses."
        badge="Builtin + Community"
      />

      {error ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
      {status ? <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{status}</div> : null}

      <div className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
        <div className="space-y-4">
          <Card className="bg-white/88">
            <CardHeader className="flex flex-row items-center justify-between gap-4">
              <div>
                <CardTitle>Registered Skills</CardTitle>
                <CardDescription>Local builtin skills and installed community packages share one runtime registry.</CardDescription>
              </div>
              <Button
                variant="secondary"
                disabled={loading}
                onClick={async () => {
                  setLoading(true);
                  setError("");
                  setStatus("");
                  try {
                    await seedSkills();
                    await refresh(activeSkillId);
                    setStatus("Builtin skills synced.");
                  } catch (reason) {
                    setError(reason instanceof Error ? reason.message : "Skill sync failed.");
                  } finally {
                    setLoading(false);
                  }
                }}
              >
                Sync Builtins
              </Button>
            </CardHeader>
            <CardContent className="space-y-3">
              {skills.map((skill) => {
                const vm = toSkillCardViewModel(skill);
                return (
                  <button
                    key={skill.id}
                    className="w-full rounded-[1.25rem] border border-[color:var(--border)] bg-[#faf8f4] px-4 py-4 text-left"
                    onClick={() => setActiveSkillId(skill.id)}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium">{vm.title}</p>
                      <Badge>{vm.status}</Badge>
                      <Badge>{vm.typeLabel}</Badge>
                      {vm.proxyLabel ? <Badge>{vm.proxyLabel}</Badge> : null}
                    </div>
                    <p className="mt-2 text-sm text-[var(--muted-foreground)]">{vm.description}</p>
                    <p className="mt-2 text-xs uppercase tracking-[0.2em] text-[var(--muted-foreground)]">
                      {vm.slug} | {vm.versionLabel}
                    </p>
                  </button>
                );
              })}
            </CardContent>
          </Card>

          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Install Community Skill</CardTitle>
              <CardDescription>
                Import a `skill.json` package or a `.zip` archive containing `skill.json`. Add `runtime.json` when the
                package should proxy an approved local handler.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <input
                type="file"
                accept=".json,.zip,application/json,application/zip"
                onChange={(event) => setSelectedPackage(event.target.files?.[0] ?? null)}
                className="block w-full text-sm text-[var(--muted-foreground)] file:mr-4 file:rounded-md file:border-0 file:bg-[#faf8f4] file:px-4 file:py-2 file:text-sm file:font-medium"
              />
              <div className="rounded-[1.25rem] border border-[color:var(--border)] bg-[#faf8f4] p-4 text-sm text-[var(--muted-foreground)]">
                <p>Selected package: {selectedPackage?.name ?? "none"}</p>
                <p className="mt-2">Current approved handlers: `memory-search`, `task-extractor`.</p>
              </div>
              <Button disabled={loading || !selectedPackage} onClick={handleInstall}>
                Install Package
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Skill Detail</CardTitle>
              <CardDescription>Inspect the installed manifest, runtime config, and execution mode for the selected skill.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {activeSkill && activeSkillViewModel ? (
                <>
                  <div className="flex flex-wrap gap-2">
                    <Badge>{activeSkillViewModel.slug}</Badge>
                    <Badge>{activeSkillViewModel.status}</Badge>
                    <Badge>{activeSkillViewModel.typeLabel}</Badge>
                    <Badge>{activeSkillViewModel.versionLabel}</Badge>
                    <Badge>{activeSkillViewModel.handlerLabel}</Badge>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <Button disabled={loading} onClick={() => handleToggle(activeSkill)}>
                      {activeSkillViewModel.toggleLabel}
                    </Button>
                    {activeSkillViewModel.isCommunity ? (
                      <Button variant="secondary" disabled={loading} onClick={() => handleRemove(activeSkill)}>
                        Remove Community Skill
                      </Button>
                    ) : null}
                  </div>
                  <div className="grid gap-4 xl:grid-cols-2">
                    <div>
                      <p className="mb-2 text-sm font-medium">Manifest</p>
                      <pre className="overflow-x-auto rounded-[1.5rem] bg-[#faf8f4] p-4 text-xs leading-6">
                        {activeSkillViewModel.manifestJson}
                      </pre>
                    </div>
                    <div>
                      <p className="mb-2 text-sm font-medium">Runtime Config</p>
                      <pre className="overflow-x-auto rounded-[1.5rem] bg-[#faf8f4] p-4 text-xs leading-6">
                        {activeSkillViewModel.runtimeConfigJson}
                      </pre>
                    </div>
                  </div>
                </>
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">No skills registered yet.</p>
              )}
            </CardContent>
          </Card>

          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Recent Invocations</CardTitle>
              <CardDescription>Actual runtime calls logged by the backend skill registry.</CardDescription>
            </CardHeader>
            <CardContent>
              <InvocationList invocations={invocationViewModels} />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
