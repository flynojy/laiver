"use client";

import { useEffect, useMemo, useState } from "react";

import type { FineTuneJobDetail, FineTuneJobRecord, UUID } from "@agent/shared";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  createFineTuneJob,
  getFineTuneJob,
  launchFineTuneJob,
  listFineTuneJobs,
  listImports,
  registerFineTuneProvider,
  updateModelProvider,
  type ImportDetail
} from "@/lib/api";

function speakerOptionsForImport(importRow: ImportDetail | null) {
  if (!importRow) {
    return [];
  }
  const summary = importRow.import_job.normalized_summary ?? {};
  const speakerStats = summary.speaker_stats;
  if (speakerStats && typeof speakerStats === "object") {
    return Object.entries(speakerStats)
      .map(([speaker, value]) => ({
        speaker,
        count:
          value && typeof value === "object" && "message_count" in value
            ? Number((value as { message_count?: number }).message_count ?? 0)
            : 0
      }))
      .sort((left, right) => right.count - left.count);
  }

  const counts = new Map<string, number>();
  for (const message of importRow.normalized_messages) {
    counts.set(message.speaker, (counts.get(message.speaker) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([speaker, count]) => ({ speaker, count }))
    .sort((left, right) => right.count - left.count);
}

function DatasetPreview({ detail }: { detail: FineTuneJobDetail | null }) {
  if (!detail) {
    return <p className="text-sm text-[var(--muted-foreground)]">Create or select a job to inspect the generated dataset preview.</p>;
  }

  return (
    <div className="space-y-4">
      {detail.dataset_preview.map((sample, index) => (
        <div key={`${detail.job.id}-${index}`} className="rounded-[1rem] border border-[color:var(--border)] bg-[#faf8f4] p-4">
          <p className="text-sm font-medium">Sample {index + 1}</p>
          <div className="mt-3 space-y-2 text-sm">
            {sample.messages.map((message, messageIndex) => (
              <div key={messageIndex} className="rounded-md bg-white px-3 py-2">
                <p className="text-xs uppercase tracking-[0.15em] text-[var(--muted-foreground)]">{message.role}</p>
                <p className="mt-1 whitespace-pre-wrap">{message.content}</p>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function TrainingPage() {
  const [imports, setImports] = useState<ImportDetail[]>([]);
  const [jobs, setJobs] = useState<FineTuneJobRecord[]>([]);
  const [selectedImportId, setSelectedImportId] = useState<UUID>("");
  const [selectedJobId, setSelectedJobId] = useState<UUID>("");
  const [selectedSpeaker, setSelectedSpeaker] = useState("");
  const [jobName, setJobName] = useState("Laiver Local Fine-Tune");
  const [backend, setBackend] = useState<"local_lora" | "local_qlora">("local_qlora");
  const [baseModel, setBaseModel] = useState("Qwen/Qwen2.5-7B-Instruct");
  const [contextWindow, setContextWindow] = useState("6");
  const [detail, setDetail] = useState<FineTuneJobDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [launching, setLaunching] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  async function refresh(activeJobId?: string) {
    const [importRows, jobRows] = await Promise.all([listImports(), listFineTuneJobs()]);
    setImports(importRows);
    setJobs(jobRows);
    const nextImportId = selectedImportId || importRows[0]?.import_job.id || "";
    setSelectedImportId(nextImportId);
    const nextJobId = activeJobId ?? jobRows[0]?.id ?? "";
    setSelectedJobId(nextJobId);
    if (nextJobId) {
      setDetail(await getFineTuneJob(nextJobId));
    } else {
      setDetail(null);
    }
  }

  async function refreshJobDetail(jobId: UUID) {
    setSelectedJobId(jobId);
    setDetail(await getFineTuneJob(jobId));
  }

  useEffect(() => {
    refresh().catch((reason) => {
      setError(reason instanceof Error ? reason.message : "Training page bootstrap failed.");
    });
  }, []);

  useEffect(() => {
    if (!selectedJobId || detail?.job.status !== "running") {
      return undefined;
    }
    const timer = window.setInterval(() => {
      refresh(selectedJobId).catch((reason) => {
        setError(reason instanceof Error ? reason.message : "Training job refresh failed.");
      });
    }, 4000);
    return () => window.clearInterval(timer);
  }, [detail?.job.status, selectedJobId]);

  const selectedImport = useMemo(
    () => imports.find((item) => item.import_job.id === selectedImportId) ?? imports[0] ?? null,
    [imports, selectedImportId]
  );
  const speakers = useMemo(() => speakerOptionsForImport(selectedImport), [selectedImport]);

  useEffect(() => {
    const defaultSpeaker =
      (selectedImport?.import_job.normalized_summary?.conversation_owner as string | undefined) ??
      speakers[0]?.speaker ??
      "";
    setSelectedSpeaker(defaultSpeaker);
    if (selectedImport) {
      setJobName(`${selectedImport.import_job.file_name} Fine-Tune`);
    }
  }, [selectedImport, speakers]);

  async function handleCreateJob() {
    if (!selectedImport || !selectedSpeaker) {
      setError("Choose an import and target speaker first.");
      return;
    }

    setLoading(true);
    setError("");
    setStatus("");
    try {
      const created = await createFineTuneJob({
        user_id: selectedImport.import_job.user_id as UUID,
        import_id: selectedImport.import_job.id,
        name: jobName,
        source_speaker: selectedSpeaker,
        backend,
        base_model: baseModel,
        context_window: Number(contextWindow)
      });
      setDetail(created);
      setStatus(`${created.job.name} created. Dataset export is ready for local training.`);
      await refresh(created.job.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Fine-tune job creation failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleLaunchJob() {
    if (!detail) {
      return;
    }

    setLaunching(true);
    setError("");
    setStatus("");
    try {
      const job = await launchFineTuneJob(detail.job.id);
      await refresh(job.id);
      setStatus(`${job.name} has started. Laiver will keep refreshing the local training status.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Training launch failed.");
    } finally {
      setLaunching(false);
    }
  }

  async function handleRegisterProvider() {
    if (!detail) {
      return;
    }
    setRegistering(true);
    setError("");
    setStatus("");
    try {
      const provider = await registerFineTuneProvider(detail.job.id);
      await refresh(detail.job.id);
      setStatus(`${provider.name} is now available in the provider registry.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Provider registration failed.");
    } finally {
      setRegistering(false);
    }
  }

  async function handleSetRegisteredProviderDefault() {
    if (!detail?.registered_provider?.id) {
      return;
    }
    setLoading(true);
    setError("");
    setStatus("");
    try {
      await updateModelProvider(detail.registered_provider.id, { is_default: true });
      await refresh(detail.job.id);
      setStatus(`${detail.registered_provider.name} is now the default model provider.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Updating the default provider failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Local Fine-Tuning"
        title="Training Jobs"
        description="Turn imported chat history into local LoRA or QLoRA datasets, launch training locally, and register the finished adapter as a selectable model."
        badge="Dataset + Model"
      />

      {error ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
      {status ? <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{status}</div> : null}

      <div className="grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
        <div className="space-y-4">
          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Create Job</CardTitle>
              <CardDescription>Choose an imported conversation, a target speaker, and the local training mode.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="training-import">Source Import</Label>
                <select
                  id="training-import"
                  className="h-11 w-full rounded-md border border-[color:var(--border)] bg-white px-3 text-sm"
                  value={selectedImportId}
                  onChange={(event) => setSelectedImportId(event.target.value)}
                >
                  {imports.map((item) => (
                    <option key={item.import_job.id} value={item.import_job.id}>
                      {item.import_job.file_name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="training-speaker">Target Speaker</Label>
                <select
                  id="training-speaker"
                  className="h-11 w-full rounded-md border border-[color:var(--border)] bg-white px-3 text-sm"
                  value={selectedSpeaker}
                  onChange={(event) => setSelectedSpeaker(event.target.value)}
                >
                  {speakers.map((item) => (
                    <option key={item.speaker} value={item.speaker}>
                      {item.speaker} ({item.count})
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="training-name">Job Name</Label>
                <Input id="training-name" value={jobName} onChange={(event) => setJobName(event.target.value)} />
              </div>

              <div className="space-y-2">
                <Label htmlFor="training-backend">Training Backend</Label>
                <select
                  id="training-backend"
                  className="h-11 w-full rounded-md border border-[color:var(--border)] bg-white px-3 text-sm"
                  value={backend}
                  onChange={(event) => setBackend(event.target.value as "local_lora" | "local_qlora")}
                >
                  <option value="local_qlora">Local QLoRA</option>
                  <option value="local_lora">Local LoRA</option>
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="training-model">Base Model</Label>
                <Input id="training-model" value={baseModel} onChange={(event) => setBaseModel(event.target.value)} />
              </div>

              <div className="space-y-2">
                <Label htmlFor="training-context">Context Window</Label>
                <Input id="training-context" value={contextWindow} onChange={(event) => setContextWindow(event.target.value)} />
              </div>

              <Button disabled={loading || !selectedImport} onClick={handleCreateJob}>
                {loading ? "Preparing..." : "Create Fine-Tune Job"}
              </Button>
            </CardContent>
          </Card>

          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Jobs</CardTitle>
              <CardDescription>Generated datasets stay local and can be reused for later training runs.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {jobs.length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">No training jobs yet.</p>
              ) : (
                jobs.map((job) => (
                  <button
                    key={job.id}
                    className="w-full rounded-[1rem] border border-[color:var(--border)] bg-[#faf8f4] px-4 py-4 text-left"
                    onClick={async () => {
                      await refreshJobDetail(job.id);
                    }}
                  >
                    <div className="flex flex-wrap gap-2">
                      <Badge>{job.status}</Badge>
                      <Badge>{job.backend}</Badge>
                    </div>
                    <p className="mt-3 font-medium">{job.name}</p>
                    <p className="mt-2 text-sm text-[var(--muted-foreground)]">{job.base_model}</p>
                    <p className="mt-2 text-xs text-[var(--muted-foreground)]">
                      train {job.train_examples} / val {job.validation_examples} / test {job.test_examples}
                    </p>
                  </button>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Job Detail</CardTitle>
              <CardDescription>Inspect the dataset, launch the local runner, and watch the finished adapter register into the model registry.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {detail ? (
                <>
                  <div className="flex flex-wrap gap-2">
                    <Badge>{detail.job.status}</Badge>
                    <Badge>{detail.job.backend}</Badge>
                    <Badge>{detail.job.source_speaker}</Badge>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <Button disabled={launching || detail.job.status === "running"} onClick={handleLaunchJob}>
                      {launching ? "Launching..." : detail.job.status === "running" ? "Training Running" : "Launch Local Training"}
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={registering || detail.job.status !== "completed"}
                      onClick={handleRegisterProvider}
                    >
                      {registering ? "Registering..." : "Register Provider"}
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={async () => {
                        await refresh(detail.job.id);
                      }}
                    >
                      Refresh Status
                    </Button>
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="rounded-[1rem] border border-[color:var(--border)] bg-[#faf8f4] p-4 text-sm">
                      <p className="font-medium">Dataset</p>
                      <p className="mt-2 break-all text-[var(--muted-foreground)]">{detail.job.dataset_path}</p>
                      <p className="mt-3 font-medium">Config</p>
                      <p className="mt-2 break-all text-[var(--muted-foreground)]">{detail.job.config_path}</p>
                    </div>
                    <div className="rounded-[1rem] border border-[color:var(--border)] bg-[#faf8f4] p-4 text-sm">
                      <p className="font-medium">Output</p>
                      <p className="mt-2 break-all text-[var(--muted-foreground)]">{detail.job.output_dir}</p>
                      <p className="mt-3 font-medium">Split</p>
                      <p className="mt-2 text-[var(--muted-foreground)]">
                        train {detail.job.train_examples} / validation {detail.job.validation_examples} / test {detail.job.test_examples}
                      </p>
                    </div>
                  </div>
                  {detail.job.artifact_path ? (
                    <div className="rounded-[1rem] border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
                      <p className="font-medium">Adapter Artifact</p>
                      <p className="mt-2 break-all">{detail.job.artifact_path}</p>
                    </div>
                  ) : null}
                  {detail.registered_provider ? (
                    <div className="rounded-[1rem] border border-sky-200 bg-sky-50 p-4 text-sm text-sky-900">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium">Registered Provider</p>
                        <Badge>{detail.registered_provider.provider_type}</Badge>
                        {detail.registered_provider.is_default ? <Badge>default</Badge> : null}
                        {detail.registered_provider.is_enabled ? <Badge>enabled</Badge> : <Badge>disabled</Badge>}
                      </div>
                      <p className="mt-2">{detail.registered_provider.name}</p>
                      <p className="mt-2 break-all text-xs text-sky-700">{detail.registered_provider.base_url}</p>
                      {!detail.registered_provider.is_default ? (
                        <div className="mt-3">
                          <Button variant="secondary" disabled={loading} onClick={handleSetRegisteredProviderDefault}>
                            Set Registered Provider as Default
                          </Button>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                  {detail.job.error_message ? (
                    <div className="rounded-[1rem] border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                      <p className="font-medium">Last Error</p>
                      <p className="mt-2 whitespace-pre-wrap">{detail.job.error_message}</p>
                    </div>
                  ) : null}
                  <div className="rounded-[1rem] border border-[color:var(--border)] bg-[#faf8f4] p-4 text-sm">
                    <p className="font-medium">Launcher Command</p>
                    <pre className="mt-3 overflow-x-auto whitespace-pre-wrap text-xs leading-6">{detail.job.launcher_command}</pre>
                  </div>
                </>
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">No training job selected yet.</p>
              )}
            </CardContent>
          </Card>

          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Dataset Preview</CardTitle>
              <CardDescription>The last assistant message in each sample is the target speaker response used for fine-tuning.</CardDescription>
            </CardHeader>
            <CardContent>
              <DatasetPreview detail={detail} />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
