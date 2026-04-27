"use client";

import { useEffect, useMemo, useState } from "react";

import type { PersonaCard } from "@agent/shared";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  bootstrapUser,
  extractPersona,
  listImports,
  listPersonas,
  updatePersona,
  type ImportDetail
} from "@/lib/api";

type ExtractionResult = {
  persona: PersonaCard;
  source_message_count: number;
  source_speaker?: string | null;
};

type SpeakerOption = {
  speaker: string;
  messageCount: number;
  roles: string[];
  isSelf: boolean;
};

function renderTagList(values: string[]) {
  if (values.length === 0) {
    return <p className="text-sm text-[var(--muted-foreground)]">No values.</p>;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {values.map((value) => (
        <Badge key={value}>{value}</Badge>
      ))}
    </div>
  );
}

function personaSignature(persona: PersonaCard | null) {
  if (!persona) return "";
  return JSON.stringify({
    name: persona.name,
    description: persona.description ?? "",
    tone: persona.tone,
    verbosity: persona.verbosity,
    common_topics: persona.common_topics ?? [],
    common_phrases: persona.common_phrases ?? [],
    response_style: persona.response_style ?? {},
    relationship_style: persona.relationship_style ?? {},
    is_default: persona.is_default
  });
}

function renderPersonaPreview(persona: PersonaCard | null, prompt: string) {
  if (!persona) {
    return "No Persona selected.";
  }

  const intro =
    persona.verbosity === "detailed"
      ? `I would answer this in a ${persona.tone} and more detailed way.`
      : `I would answer this in a ${persona.tone} and concise way.`;
  const phrase = persona.common_phrases?.[0]
    ? `Signature phrasing: ${persona.common_phrases[0]}`
    : "No signature phrasing configured.";
  const topics =
    persona.common_topics?.length > 0
      ? `Likely emphasis: ${persona.common_topics.slice(0, 3).join(", ")}.`
      : "Likely emphasis: the current request only.";

  return `${intro}\n${topics}\n${phrase}\nSample prompt: ${prompt}`;
}

function splitCsv(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function speakerOptionsForImport(item: ImportDetail | undefined): SpeakerOption[] {
  if (!item) return [];

  const summaryStats = item.import_job.normalized_summary?.speaker_stats;
  if (summaryStats && typeof summaryStats === "object" && !Array.isArray(summaryStats)) {
    return Object.entries(summaryStats)
      .map(([speaker, value]) => {
        if (!value || typeof value !== "object") return null;
        const candidate = value as Record<string, unknown>;
        return {
          speaker,
          messageCount:
            typeof candidate.message_count === "number"
              ? candidate.message_count
              : Number(candidate.message_count) || 0,
          roles: Array.isArray(candidate.roles)
            ? candidate.roles.filter((item): item is string => typeof item === "string")
            : [],
          isSelf: candidate.is_self === true
        };
      })
      .filter((item): item is SpeakerOption => item !== null)
      .sort((left, right) => right.messageCount - left.messageCount);
  }

  const fallback = new Map<string, SpeakerOption>();
  for (const message of item.normalized_messages) {
    const current = fallback.get(message.speaker) ?? {
      speaker: message.speaker,
      messageCount: 0,
      roles: [],
      isSelf: message.metadata?.is_self === true
    };
    current.messageCount += 1;
    if (!current.roles.includes(message.role)) {
      current.roles.push(message.role);
    }
    fallback.set(message.speaker, current);
  }
  return [...fallback.values()].sort((left, right) => right.messageCount - left.messageCount);
}

function defaultSpeakerForImport(item: ImportDetail | undefined) {
  if (!item) return "";
  const owner = item.import_job.normalized_summary?.conversation_owner;
  if (typeof owner === "string" && owner.trim()) {
    return owner;
  }
  return "";
}

export default function PersonaPage() {
  const [userId, setUserId] = useState("");
  const [imports, setImports] = useState<ImportDetail[]>([]);
  const [personas, setPersonas] = useState<PersonaCard[]>([]);
  const [savedPersona, setSavedPersona] = useState<PersonaCard | null>(null);
  const [draftPersona, setDraftPersona] = useState<PersonaCard | null>(null);
  const [selectedImportId, setSelectedImportId] = useState("");
  const [selectedSourceSpeaker, setSelectedSourceSpeaker] = useState("");
  const [previewPrompt, setPreviewPrompt] = useState("How would you summarize the next step for this project?");
  const [lastExtraction, setLastExtraction] = useState<ExtractionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  const selectedImport = useMemo(
    () => imports.find((item) => item.import_job.id === selectedImportId),
    [imports, selectedImportId]
  );
  const speakerOptions = useMemo(
    () => speakerOptionsForImport(selectedImport),
    [selectedImport]
  );

  useEffect(() => {
    async function bootstrap() {
      const user = await bootstrapUser();
      setUserId(user.user.id);
      const [importRows, personaRows] = await Promise.all([listImports(), listPersonas()]);
      setImports(importRows);
      setPersonas(personaRows);
      setSavedPersona(personaRows[0] ?? null);
      setDraftPersona(personaRows[0] ?? null);
      setSelectedImportId(importRows[0]?.import_job.id ?? "");
    }

    bootstrap().catch((reason) => {
      setError(reason instanceof Error ? reason.message : "Persona page bootstrap failed.");
    });
  }, []);

  useEffect(() => {
    setSelectedSourceSpeaker(defaultSpeakerForImport(selectedImport));
  }, [selectedImportId, selectedImport]);

  async function refreshPersonas(nextPersonaId?: string) {
    const rows = await listPersonas();
    setPersonas(rows);
    const selected = rows.find((item) => item.id === nextPersonaId) ?? rows[0] ?? null;
    setSavedPersona(selected);
    setDraftPersona(selected);
  }

  async function handleExtract() {
    if (!userId || !selectedImportId) return;
    setLoading(true);
    setError("");
    setStatus("");
    try {
      const result = await extractPersona({
        user_id: userId,
        import_id: selectedImportId,
        name: `${selectedImport?.import_job.file_name ?? "Imported"} Persona`,
        source_speaker: selectedSourceSpeaker || undefined,
        persist: true,
        set_default: true
      });
      setLastExtraction(result);
      setSavedPersona(result.persona);
      setDraftPersona(result.persona);
      await refreshPersonas(result.persona.id);
      setStatus(
        result.source_speaker
          ? `Persona extracted from ${result.source_speaker}.`
          : "Persona extracted successfully."
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Persona extraction failed.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!savedPersona?.id || !draftPersona?.id) return;
    if (savedPersona.id !== draftPersona.id) return;
    if (personaSignature(savedPersona) === personaSignature(draftPersona)) return;

    const timeout = window.setTimeout(async () => {
      try {
        const updated = await updatePersona(draftPersona.id!, draftPersona);
        setSavedPersona(updated);
        setDraftPersona(updated);
        setPersonas((current) => current.map((item) => (item.id === updated.id ? updated : item)));
        setStatus("Persona auto-saved.");
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Persona auto-save failed.");
      }
    }, 700);

    return () => window.clearTimeout(timeout);
  }, [draftPersona, savedPersona]);

  const savedPreview = useMemo(
    () => renderPersonaPreview(savedPersona, previewPrompt),
    [savedPersona, previewPrompt]
  );
  const draftPreview = useMemo(
    () => renderPersonaPreview(draftPersona, previewPrompt),
    [draftPersona, previewPrompt]
  );

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Quality"
        title="Persona Validation"
        description="Extract a Persona from a chosen speaker, inspect field-level evidence and confidence, then edit key fields with auto-save and compare the answer preview before and after changes."
        badge="Evidence + Preview"
      />

      {error ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
      {status ? <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{status}</div> : null}

      <div className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
        <Card className="bg-white/88">
          <CardHeader>
            <CardTitle>Extract Persona</CardTitle>
            <CardDescription>Choose an import and optionally pick the speaker whose style you want to model.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Import Source</Label>
              <select
                className="w-full rounded-2xl border border-[color:var(--border)] bg-white px-4 py-3 text-sm"
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
              <Label>Target Speaker</Label>
              <select
                className="w-full rounded-2xl border border-[color:var(--border)] bg-white px-4 py-3 text-sm"
                value={selectedSourceSpeaker}
                onChange={(event) => setSelectedSourceSpeaker(event.target.value)}
              >
                <option value="">Auto</option>
                {speakerOptions.map((option) => (
                  <option key={option.speaker} value={option.speaker}>
                    {option.speaker}
                  </option>
                ))}
              </select>
            </div>

            {speakerOptions.length > 0 ? (
              <div className="rounded-[1.25rem] border border-[color:var(--border)] bg-[#faf8f4] p-4 text-sm">
                <p className="font-medium">Speaker Summary</p>
                <div className="mt-3 space-y-2">
                  {speakerOptions.map((option) => (
                    <div key={option.speaker} className="flex flex-wrap items-center gap-2">
                      <Badge>{option.speaker}</Badge>
                      <Badge>{option.messageCount} messages</Badge>
                      {option.isSelf ? <Badge>self</Badge> : null}
                      {option.roles.map((role) => (
                        <Badge key={`${option.speaker}-${role}`}>{role}</Badge>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            <Button className="w-full" disabled={!selectedImportId || !userId || loading} onClick={handleExtract}>
              Extract Persona
            </Button>

            <div className="space-y-2">
              {personas.length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">No Persona records yet.</p>
              ) : (
                personas.map((persona) => (
                  <button
                    key={persona.id}
                    className="w-full rounded-2xl border border-[color:var(--border)] bg-[#faf8f4] px-4 py-3 text-left"
                    onClick={() => {
                      setSavedPersona(persona);
                      setDraftPersona(persona);
                    }}
                  >
                    <div className="flex items-center gap-2">
                      <p className="font-medium">{persona.name}</p>
                      {persona.is_default ? <Badge>default</Badge> : null}
                    </div>
                    <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                      {persona.tone} / {persona.verbosity}
                    </p>
                  </button>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Extraction Details</CardTitle>
              <CardDescription>Field-level evidence and confidence for the currently selected Persona.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {draftPersona ? (
                <>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge>{draftPersona.tone}</Badge>
                    <Badge>{draftPersona.verbosity}</Badge>
                    {draftPersona.is_default ? <Badge>default persona</Badge> : null}
                    {lastExtraction ? <Badge>{lastExtraction.source_message_count} source messages</Badge> : null}
                    {lastExtraction?.source_speaker ? <Badge>speaker: {lastExtraction.source_speaker}</Badge> : null}
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label>Common Topics</Label>
                      {renderTagList(draftPersona.common_topics ?? [])}
                    </div>
                    <div className="space-y-2">
                      <Label>Common Phrases</Label>
                      {renderTagList(draftPersona.common_phrases ?? [])}
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label>Confidence Scores</Label>
                      <pre className="overflow-x-auto rounded-2xl bg-[#faf8f4] p-4 text-xs leading-6">
                        {JSON.stringify(draftPersona.confidence_scores ?? {}, null, 2)}
                      </pre>
                    </div>
                    <div className="space-y-2">
                      <Label>Field Evidence</Label>
                      <pre className="overflow-x-auto rounded-2xl bg-[#faf8f4] p-4 text-xs leading-6">
                        {JSON.stringify(draftPersona.evidence_samples ?? {}, null, 2)}
                      </pre>
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label>Response Style</Label>
                      <pre className="overflow-x-auto rounded-2xl bg-[#faf8f4] p-4 text-xs leading-6">
                        {JSON.stringify(draftPersona.response_style ?? {}, null, 2)}
                      </pre>
                    </div>
                    <div className="space-y-2">
                      <Label>Relationship Style</Label>
                      <pre className="overflow-x-auto rounded-2xl bg-[#faf8f4] p-4 text-xs leading-6">
                        {JSON.stringify(draftPersona.relationship_style ?? {}, null, 2)}
                      </pre>
                    </div>
                  </div>
                </>
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">Extract a Persona first.</p>
              )}
            </CardContent>
          </Card>

          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Edit Persona</CardTitle>
              <CardDescription>Key fields auto-save shortly after changes so you can tune the Persona and compare the preview immediately.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {draftPersona ? (
                <>
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="space-y-2">
                      <Label>Name</Label>
                      <Input
                        value={draftPersona.name}
                        onChange={(event) =>
                          setDraftPersona((current) => current && { ...current, name: event.target.value })
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Tone</Label>
                      <Input
                        value={draftPersona.tone}
                        onChange={(event) =>
                          setDraftPersona((current) => current && { ...current, tone: event.target.value })
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Verbosity</Label>
                      <Input
                        value={draftPersona.verbosity}
                        onChange={(event) =>
                          setDraftPersona((current) => current && { ...current, verbosity: event.target.value })
                        }
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Description</Label>
                    <Textarea
                      value={draftPersona.description ?? ""}
                      onChange={(event) =>
                        setDraftPersona((current) => current && { ...current, description: event.target.value })
                      }
                    />
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label>Common Topics (comma separated)</Label>
                      <Textarea
                        value={(draftPersona.common_topics ?? []).join(", ")}
                        onChange={(event) =>
                          setDraftPersona((current) =>
                            current && { ...current, common_topics: splitCsv(event.target.value) }
                          )
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Common Phrases (comma separated)</Label>
                      <Textarea
                        value={(draftPersona.common_phrases ?? []).join(", ")}
                        onChange={(event) =>
                          setDraftPersona((current) =>
                            current && { ...current, common_phrases: splitCsv(event.target.value) }
                          )
                        }
                      />
                    </div>
                  </div>
                </>
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">No editable Persona selected.</p>
              )}
            </CardContent>
          </Card>

          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Answer Preview / Compare</CardTitle>
              <CardDescription>Compare the saved Persona against the current edited draft before the next conversation turn.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Preview Prompt</Label>
                <Textarea value={previewPrompt} onChange={(event) => setPreviewPrompt(event.target.value)} />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Saved Persona Preview</Label>
                  <pre className="overflow-x-auto rounded-2xl bg-[#faf8f4] p-4 text-xs leading-6">{savedPreview}</pre>
                </div>
                <div className="space-y-2">
                  <Label>Edited Draft Preview</Label>
                  <pre className="overflow-x-auto rounded-2xl bg-[#faf8f4] p-4 text-xs leading-6">{draftPreview}</pre>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
