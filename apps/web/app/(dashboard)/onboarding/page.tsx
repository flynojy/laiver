"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Loader2, Play, UploadCloud } from "lucide-react";

import type { FineTuneJobDetail, PersonaCard, UUID } from "@agent/shared";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableCell, TableHead, TableRow } from "@/components/ui/table";
import {
  bootstrapModelProvider,
  bootstrapUser,
  commitImport,
  createFineTuneJob,
  extractPersona,
  launchFineTuneJob,
  listFineTuneJobs,
  listImports,
  listModelProviders,
  listPersonas,
  previewImport,
  seedSkills,
  type ImportDetail,
  type ImportPreview
} from "@/lib/api";

type OnboardingStep = "import" | "persona" | "training" | "runtime";

type SpeakerOption = {
  speaker: string;
  count: number;
  isSelf: boolean;
};

function speakerOptionsForImport(importRow: ImportDetail | null): SpeakerOption[] {
  if (!importRow) return [];
  const speakerStats = importRow.import_job.normalized_summary?.speaker_stats;
  if (speakerStats && typeof speakerStats === "object" && !Array.isArray(speakerStats)) {
    return Object.entries(speakerStats)
      .map(([speaker, value]) => {
        const payload = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
        return {
          speaker,
          count: Number(payload.message_count ?? 0),
          isSelf: payload.is_self === true
        };
      })
      .sort((left, right) => right.count - left.count);
  }

  const counts = new Map<string, SpeakerOption>();
  for (const message of importRow.normalized_messages) {
    const current = counts.get(message.speaker) ?? {
      speaker: message.speaker,
      count: 0,
      isSelf: message.metadata?.is_self === true
    };
    current.count += 1;
    counts.set(message.speaker, current);
  }
  return [...counts.values()].sort((left, right) => right.count - left.count);
}

function completedStep(current: OnboardingStep, target: OnboardingStep) {
  const order: OnboardingStep[] = ["import", "persona", "training", "runtime"];
  return order.indexOf(current) > order.indexOf(target);
}

function StepBadge({ done, active }: { done: boolean; active: boolean }) {
  if (done) {
    return <CheckCircle2 className="h-5 w-5 text-emerald-600" />;
  }
  return <span className={active ? "h-3 w-3 rounded-full bg-[var(--accent)]" : "h-3 w-3 rounded-full bg-[#d7d4ce]"} />;
}

export default function OnboardingPage() {
  const [userId, setUserId] = useState<UUID>("");
  const [step, setStep] = useState<OnboardingStep>("import");
  const [imports, setImports] = useState<ImportDetail[]>([]);
  const [personas, setPersonas] = useState<PersonaCard[]>([]);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [committedImport, setCommittedImport] = useState<ImportDetail | null>(null);
  const [selectedSpeaker, setSelectedSpeaker] = useState("");
  const [persona, setPersona] = useState<PersonaCard | null>(null);
  const [jobName, setJobName] = useState("Laiver Local Fine-Tune");
  const [baseModel, setBaseModel] = useState("Qwen/Qwen2.5-7B-Instruct");
  const [trainingJob, setTrainingJob] = useState<FineTuneJobDetail | null>(null);
  const [providerCount, setProviderCount] = useState(0);
  const [skillCount, setSkillCount] = useState(0);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  const speakers = useMemo(() => speakerOptionsForImport(committedImport), [committedImport]);

  useEffect(() => {
    async function bootstrap() {
      const user = await bootstrapUser();
      const [importRows, personaRows, providers] = await Promise.all([
        listImports(),
        listPersonas(),
        listModelProviders()
      ]);
      setUserId(user.user.id);
      setImports(importRows);
      setPersonas(personaRows);
      setCommittedImport(importRows[0] ?? null);
      setPersona(personaRows[0] ?? null);
      setProviderCount(providers.length);
      if (personaRows[0]) setStep("training");
      else if (importRows[0]) setStep("persona");
    }

    bootstrap().catch((reason) => {
      setError(reason instanceof Error ? reason.message : "Onboarding bootstrap failed.");
    });
  }, []);

  useEffect(() => {
    const owner = committedImport?.import_job.normalized_summary?.conversation_owner;
    if (typeof owner === "string" && owner.trim()) {
      setSelectedSpeaker(owner);
    } else {
      setSelectedSpeaker(speakers[0]?.speaker ?? "");
    }
    if (committedImport) {
      setJobName(`${committedImport.import_job.file_name} Fine-Tune`);
    }
  }, [committedImport, speakers]);

  async function handlePreview(file: File) {
    setBusy("preview");
    setError("");
    setStatus("");
    try {
      const result = await previewImport(file);
      setSelectedFile(file);
      setPreview(result);
      setStatus(`${result.total_messages} messages parsed.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "File preview failed.");
    } finally {
      setBusy("");
    }
  }

  async function handleCommitImport() {
    if (!preview || !selectedFile || !userId) return;
    setBusy("commit");
    setError("");
    setStatus("");
    try {
      const committed = await commitImport({
        user_id: userId,
        file_name: selectedFile.name,
        file_size: selectedFile.size,
        source_type: preview.source_type,
        normalized_messages: preview.normalized_messages,
        preview: {
          total_messages: preview.total_messages,
          source_metadata: preview.source_metadata
        }
      });
      setCommittedImport(committed);
      setImports(await listImports());
      setPreview(null);
      setSelectedFile(null);
      setStep("persona");
      setStatus("Import saved.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Import commit failed.");
    } finally {
      setBusy("");
    }
  }

  async function handleExtractPersona() {
    if (!userId || !committedImport) return;
    setBusy("persona");
    setError("");
    setStatus("");
    try {
      const result = await extractPersona({
        user_id: userId,
        import_id: committedImport.import_job.id,
        name: `${committedImport.import_job.file_name} Persona`,
        source_speaker: selectedSpeaker || undefined,
        persist: true,
        set_default: true
      });
      setPersona(result.persona);
      setPersonas(await listPersonas());
      setStep("training");
      setStatus(result.source_speaker ? `Persona extracted from ${result.source_speaker}.` : "Persona extracted.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Persona extraction failed.");
    } finally {
      setBusy("");
    }
  }

  async function handleCreateTrainingJob() {
    if (!committedImport || !selectedSpeaker) {
      setError("Choose a committed import and speaker first.");
      return;
    }
    setBusy("training");
    setError("");
    setStatus("");
    try {
      const job = await createFineTuneJob({
        user_id: committedImport.import_job.user_id,
        import_id: committedImport.import_job.id,
        name: jobName,
        source_speaker: selectedSpeaker,
        backend: "local_qlora",
        base_model: baseModel,
        context_window: 6
      });
      setTrainingJob(job);
      await listFineTuneJobs();
      setStep("runtime");
      setStatus("Training dataset prepared.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Training job creation failed.");
    } finally {
      setBusy("");
    }
  }

  async function handleLaunchTraining() {
    if (!trainingJob) return;
    setBusy("launch");
    setError("");
    setStatus("");
    try {
      const job = await launchFineTuneJob(trainingJob.job.id);
      setStatus(`${job.name} started.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Training launch failed.");
    } finally {
      setBusy("");
    }
  }

  async function handleBootstrapRuntime() {
    setBusy("runtime");
    setError("");
    setStatus("");
    try {
      await bootstrapModelProvider();
      const seeded = await seedSkills();
      const providers = await listModelProviders();
      setProviderCount(providers.length);
      setSkillCount(seeded.length);
      setStatus("Runtime ready.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Runtime bootstrap failed.");
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="P0"
        title="One-Click Onboarding"
        description="Bring a WeChat archive into laiver, create a Persona, prepare local fine-tuning, and make the runtime ready for chat."
        badge="Import -> Persona -> Training -> Chat"
      />

      {error ? <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
      {status ? <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{status}</div> : null}

      <div className="grid gap-4 xl:grid-cols-[340px_minmax(0,1fr)]">
        <Card className="bg-white/88">
          <CardHeader>
            <CardTitle>Run Order</CardTitle>
            <CardDescription>Finish each step once, then keep refining from the dedicated pages.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { key: "import" as const, title: "Import", detail: committedImport?.import_job.file_name ?? "No import selected" },
              { key: "persona" as const, title: "Persona", detail: persona?.name ?? "No Persona yet" },
              { key: "training" as const, title: "Training", detail: trainingJob?.job.name ?? "No job yet" },
              { key: "runtime" as const, title: "Runtime", detail: `${providerCount} providers / ${skillCount} seeded skills` }
            ].map((item) => (
              <button
                key={item.key}
                className="flex w-full items-start gap-3 rounded-md border border-[color:var(--border)] bg-[#fffdf9] p-4 text-left"
                onClick={() => setStep(item.key)}
              >
                <div className="mt-1">
                  <StepBadge done={completedStep(step, item.key)} active={step === item.key} />
                </div>
                <div>
                  <p className="font-medium">{item.title}</p>
                  <p className="mt-1 text-sm text-[var(--muted-foreground)]">{item.detail}</p>
                </div>
              </button>
            ))}
          </CardContent>
        </Card>

        <div className="space-y-4">
          {step === "import" ? (
            <Card className="bg-white/88">
              <CardHeader>
                <CardTitle>Import Chat Archive</CardTitle>
                <CardDescription>Use txt, csv, json, or WeFlow-style WeChat xlsx exports.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <label className="flex min-h-[190px] cursor-pointer flex-col items-center justify-center rounded-md border border-dashed border-[color:var(--border)] bg-[var(--muted)]/40 p-6 text-center">
                  <UploadCloud className="h-8 w-8 text-[var(--muted-foreground)]" />
                  <p className="mt-4 font-medium">Choose a chat history file</p>
                  <p className="mt-2 text-sm text-[var(--muted-foreground)]">Preview first, then save the normalized messages.</p>
                  <input
                    className="hidden"
                    type="file"
                    accept=".txt,.csv,.json,.xlsx"
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      if (file) handlePreview(file).catch(() => undefined);
                    }}
                  />
                </label>

                {preview ? (
                  <div className="space-y-3">
                    <div className="flex flex-wrap gap-2">
                      <Badge>{preview.source_type.toUpperCase()}</Badge>
                      <Badge>{preview.total_messages} messages</Badge>
                      <Badge>{preview.detected_participants.length} speakers</Badge>
                    </div>
                    <div className="overflow-hidden rounded-md border border-[color:var(--border)]">
                      <Table>
                        <thead className="bg-[#faf8f4]">
                          <tr>
                            <TableHead>#</TableHead>
                            <TableHead>Speaker</TableHead>
                            <TableHead>Role</TableHead>
                            <TableHead>Content</TableHead>
                          </tr>
                        </thead>
                        <tbody>
                          {preview.normalized_messages.slice(0, 8).map((message) => (
                            <TableRow key={`${message.sequence_index}-${message.speaker}`}>
                              <TableCell>{message.sequence_index}</TableCell>
                              <TableCell>{message.speaker}</TableCell>
                              <TableCell>{message.role}</TableCell>
                              <TableCell>{message.content}</TableCell>
                            </TableRow>
                          ))}
                        </tbody>
                      </Table>
                    </div>
                  </div>
                ) : imports.length > 0 ? (
                  <div className="rounded-md border border-[color:var(--border)] bg-[#fffdf9] p-4 text-sm">
                    <p className="font-medium">Recent imports</p>
                    <div className="mt-3 space-y-2">
                      {imports.slice(0, 3).map((item) => (
                        <button
                          key={item.import_job.id}
                          className="w-full rounded-md border border-[color:var(--border)] bg-white px-3 py-2 text-left"
                          onClick={() => {
                            setCommittedImport(item);
                            setStep("persona");
                          }}
                        >
                          {item.import_job.file_name}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : null}

                <Button className="w-full" disabled={!preview || busy === "commit"} onClick={handleCommitImport}>
                  {busy === "commit" || busy === "preview" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Save Import
                </Button>
              </CardContent>
            </Card>
          ) : null}

          {step === "persona" ? (
            <Card className="bg-white/88">
              <CardHeader>
                <CardTitle>Create Persona</CardTitle>
                <CardDescription>Choose the speaker whose style laiver should learn.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {!committedImport ? (
                  <p className="text-sm text-[var(--muted-foreground)]">Save an import before extracting Persona.</p>
                ) : (
                  <>
                    <div className="space-y-2">
                      <Label>Import</Label>
                      <select
                        className="h-11 w-full rounded-md border border-[color:var(--border)] bg-white px-3 text-sm"
                        value={committedImport.import_job.id}
                        onChange={(event) => {
                          const next = imports.find((item) => item.import_job.id === event.target.value) ?? null;
                          setCommittedImport(next);
                        }}
                      >
                        {imports.map((item) => (
                          <option key={item.import_job.id} value={item.import_job.id}>
                            {item.import_job.file_name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="space-y-2">
                      <Label>Target Speaker</Label>
                      <select
                        className="h-11 w-full rounded-md border border-[color:var(--border)] bg-white px-3 text-sm"
                        value={selectedSpeaker}
                        onChange={(event) => setSelectedSpeaker(event.target.value)}
                      >
                        {speakers.map((item) => (
                          <option key={item.speaker} value={item.speaker}>
                            {item.speaker} ({item.count}){item.isSelf ? " self" : ""}
                          </option>
                        ))}
                      </select>
                    </div>
                    {persona ? (
                      <div className="rounded-md border border-[color:var(--border)] bg-[#fffdf9] p-4 text-sm">
                        <div className="flex flex-wrap gap-2">
                          <Badge>{persona.tone}</Badge>
                          <Badge>{persona.verbosity}</Badge>
                          {persona.is_default ? <Badge>default</Badge> : null}
                        </div>
                        <p className="mt-3 font-medium">{persona.name}</p>
                        <p className="mt-2 text-[var(--muted-foreground)]">{persona.description || "Persona ready."}</p>
                      </div>
                    ) : personas.length > 0 ? (
                      <div className="rounded-md border border-[color:var(--border)] bg-[#fffdf9] p-4 text-sm">
                        <p className="font-medium">Existing Personas</p>
                        <p className="mt-2 text-[var(--muted-foreground)]">{personas.length} saved Persona records.</p>
                      </div>
                    ) : null}
                    <Button className="w-full" disabled={!selectedSpeaker || busy === "persona"} onClick={handleExtractPersona}>
                      {busy === "persona" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                      Extract Persona
                    </Button>
                  </>
                )}
              </CardContent>
            </Card>
          ) : null}

          {step === "training" ? (
            <Card className="bg-white/88">
              <CardHeader>
                <CardTitle>Prepare Fine-Tuning</CardTitle>
                <CardDescription>Create a local QLoRA dataset from the committed chat archive.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Job Name</Label>
                  <Input value={jobName} onChange={(event) => setJobName(event.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>Base Model</Label>
                  <Input value={baseModel} onChange={(event) => setBaseModel(event.target.value)} />
                </div>
                {trainingJob ? (
                  <div className="rounded-md border border-[color:var(--border)] bg-[#fffdf9] p-4 text-sm">
                    <div className="flex flex-wrap gap-2">
                      <Badge>{trainingJob.job.status}</Badge>
                      <Badge>{trainingJob.job.backend}</Badge>
                      <Badge>{trainingJob.job.source_speaker}</Badge>
                    </div>
                    <p className="mt-3 font-medium">{trainingJob.job.name}</p>
                    <p className="mt-2 text-[var(--muted-foreground)]">
                      train {trainingJob.job.train_examples} / validation {trainingJob.job.validation_examples} / test{" "}
                      {trainingJob.job.test_examples}
                    </p>
                  </div>
                ) : null}
                <div className="flex flex-wrap gap-3">
                  <Button disabled={!committedImport || !selectedSpeaker || busy === "training"} onClick={handleCreateTrainingJob}>
                    {busy === "training" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Create Dataset
                  </Button>
                  <Button variant="secondary" disabled={!trainingJob || busy === "launch"} onClick={handleLaunchTraining}>
                    {busy === "launch" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
                    Launch Training
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : null}

          {step === "runtime" ? (
            <Card className="bg-white/88">
              <CardHeader>
                <CardTitle>Ready Runtime</CardTitle>
                <CardDescription>Seed skills, create a default model provider, then start chatting.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-md border border-[color:var(--border)] bg-[#fffdf9] p-4">
                    <p className="text-sm font-medium">Model Providers</p>
                    <p className="mt-2 text-2xl font-semibold">{providerCount}</p>
                  </div>
                  <div className="rounded-md border border-[color:var(--border)] bg-[#fffdf9] p-4">
                    <p className="text-sm font-medium">Seeded Skills</p>
                    <p className="mt-2 text-2xl font-semibold">{skillCount}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-3">
                  <Button disabled={busy === "runtime"} onClick={handleBootstrapRuntime}>
                    {busy === "runtime" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Initialize Runtime
                  </Button>
                  <Link
                    href="/chat"
                    className="inline-flex items-center justify-center rounded-full border border-[color:var(--border)] bg-white px-4 py-2 text-sm font-semibold text-[var(--foreground)] transition hover:bg-[var(--muted)]"
                  >
                    Start Chat
                  </Link>
                </div>
              </CardContent>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
