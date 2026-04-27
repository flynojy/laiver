"use client";

import { useEffect, useState } from "react";
import { Loader2, UploadCloud } from "lucide-react";

import type { ImportSourceMetadata } from "@agent/shared";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableCell, TableHead, TableRow } from "@/components/ui/table";
import {
  bootstrapUser,
  commitImport,
  listImports,
  previewImport,
  type ImportDetail,
  type ImportPreview
} from "@/lib/api";

function metadataEntries(metadata?: ImportSourceMetadata | Record<string, unknown>) {
  const mapping = [
    { key: "source_format", label: "Format" },
    { key: "conversation_owner", label: "Owner" },
    { key: "export_tool", label: "Export Tool" },
    { key: "export_version", label: "Export Version" },
    { key: "platform", label: "Platform" },
    { key: "exported_at", label: "Exported At" }
  ] as const;

  const entries: Array<{ label: string; value: string }> = [];
  for (const item of mapping) {
    const value = metadata?.[item.key];
    if (typeof value === "string" && value.trim()) {
      entries.push({ label: item.label, value });
    }
  }
  return entries;
}

function messageTypeBadges(metadata?: ImportSourceMetadata | Record<string, unknown>) {
  const value = metadata?.message_types;
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
    : [];
}

export default function ImportsPage() {
  const [userId, setUserId] = useState("");
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [imports, setImports] = useState<ImportDetail[]>([]);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    async function bootstrap() {
      const user = await bootstrapUser();
      setUserId(user.user.id);
      setImports(await listImports());
    }

    bootstrap().catch((reason) => {
      setError(reason instanceof Error ? reason.message : "Import page bootstrap failed.");
    });
  }, []);

  async function handlePreview(file: File) {
    setLoading(true);
    setError("");
    setStatus("");
    try {
      const result = await previewImport(file);
      setSelectedFile(file);
      setPreview(result);
      setStatus(`Parsed ${result.total_messages} messages from ${file.name}.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "File preview failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCommit() {
    if (!preview || !selectedFile || !userId) return;
    setLoading(true);
    setError("");
    setStatus("");
    try {
      await commitImport({
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
      setImports(await listImports());
      setStatus("Import committed successfully. You can continue to Persona extraction.");
      setPreview(null);
      setSelectedFile(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Import commit failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Step 1-3"
        title="Import, Preview, and Commit"
        description="Upload chat history, verify normalized messages, inspect source metadata, and then save the import for downstream Persona work."
        badge="Import -> Preview -> Commit"
      />

      {error ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
      {status ? <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{status}</div> : null}

      <div className="grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
        <Card className="bg-white/88">
          <CardHeader>
            <CardTitle>Upload Source File</CardTitle>
            <CardDescription>Supports plain text, CSV, JSON, and WeFlow-style WeChat XLSX exports.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="flex min-h-[220px] cursor-pointer flex-col items-center justify-center rounded-[1.75rem] border border-dashed border-[color:var(--border)] bg-[var(--muted)]/40 p-6 text-center">
              <UploadCloud className="h-8 w-8 text-[var(--muted-foreground)]" />
              <p className="mt-4 font-medium">Choose a txt / csv / json / xlsx file</p>
              <p className="mt-2 text-sm text-[var(--muted-foreground)]">
                Parse first, inspect the result, then commit it into the import registry.
              </p>
              <input
                className="hidden"
                type="file"
                accept=".txt,.csv,.json,.xlsx"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) {
                    handlePreview(file).catch(() => undefined);
                  }
                }}
              />
            </label>

            {preview ? (
              <div className="rounded-[1.5rem] border border-[color:var(--border)] bg-[#faf8f4] p-4 text-sm">
                <p className="font-medium">{preview.file_name}</p>
                <p className="mt-2 text-[var(--muted-foreground)]">
                  {preview.total_messages} messages, participants: {preview.detected_participants.join(" / ") || "unknown"}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Badge>{preview.source_type.toUpperCase()}</Badge>
                  <Badge>{preview.total_messages} messages</Badge>
                  <Badge>{preview.detected_participants.length} speakers</Badge>
                </div>
                {messageTypeBadges(preview.source_metadata).length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {messageTypeBadges(preview.source_metadata).map((item) => (
                      <Badge key={item}>{item}</Badge>
                    ))}
                  </div>
                ) : null}
                {metadataEntries(preview.source_metadata).length > 0 ? (
                  <div className="mt-4 grid gap-2 sm:grid-cols-2">
                    {metadataEntries(preview.source_metadata).map((entry) => (
                      <div
                        key={entry.label}
                        className="rounded-xl border border-[color:var(--border)] bg-white px-3 py-2"
                      >
                        <p className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted-foreground)]">
                          {entry.label}
                        </p>
                        <p className="mt-1 text-sm">{entry.value}</p>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}

            <Button onClick={handleCommit} disabled={!preview || loading} className="w-full">
              {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Commit Import
            </Button>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Normalized Message Preview</CardTitle>
              <CardDescription>Confirm speaker, role, and content before the data enters the shared import registry.</CardDescription>
            </CardHeader>
            <CardContent>
              {preview ? (
                <div className="overflow-hidden rounded-[1.25rem] border border-[color:var(--border)]">
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
                      {preview.normalized_messages.slice(0, 20).map((row) => (
                        <TableRow key={`${row.sequence_index}-${row.speaker}`}>
                          <TableCell>{row.sequence_index}</TableCell>
                          <TableCell>{row.speaker}</TableCell>
                          <TableCell>{row.role}</TableCell>
                          <TableCell>{row.content}</TableCell>
                        </TableRow>
                      ))}
                    </tbody>
                  </Table>
                </div>
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">
                  After you upload a file, the normalized rows will appear here.
                </p>
              )}
            </CardContent>
          </Card>

          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Committed Imports</CardTitle>
              <CardDescription>Saved imports stay available here for Persona extraction and later inspection.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {imports.length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">No imports committed yet.</p>
              ) : (
                imports.map((item) => {
                  const summary = item.import_job.normalized_summary ?? {};
                  const participants = Array.isArray(summary.participants) ? summary.participants.join(" / ") : "unknown";
                  const totalMessages =
                    typeof summary.total_messages === "number" ? summary.total_messages : item.normalized_messages.length;

                  return (
                    <div
                      key={item.import_job.id}
                      className="rounded-[1.25rem] border border-[color:var(--border)] bg-[#fffdf9] p-4"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium">{item.import_job.file_name}</p>
                        <Badge>{item.import_job.status}</Badge>
                        <Badge>{item.import_job.source_type}</Badge>
                      </div>
                      <p className="mt-2 text-sm text-[var(--muted-foreground)]">
                        {totalMessages} messages
                      </p>
                      <p className="mt-1 text-sm text-[var(--muted-foreground)]">Participants: {participants}</p>
                      {metadataEntries(summary).length > 0 ? (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {metadataEntries(summary).map((entry) => (
                            <Badge key={`${item.import_job.id}-${entry.label}`}>{`${entry.label}: ${entry.value}`}</Badge>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  );
                })
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
