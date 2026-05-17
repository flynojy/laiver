"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, UploadCloud } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableCell, TableHead, TableRow } from "@/components/ui/table";
import { toImportPreviewViewModel, toImportSummaryCardViewModel } from "@/features/imports/mappers";
import {
  bootstrapUser,
  commitImport,
  listImports,
  previewImport,
  type ImportDetail,
  type ImportPreview
} from "@/features/imports/client";

export default function ImportsPage() {
  const [userId, setUserId] = useState("");
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [imports, setImports] = useState<ImportDetail[]>([]);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const previewView = useMemo(() => (preview ? toImportPreviewViewModel(preview) : null), [preview]);
  const importCards = useMemo(() => imports.map(toImportSummaryCardViewModel), [imports]);

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

      {error ? <div className="rounded-2xl border border-[var(--danger)] bg-[color:var(--danger)]/10 px-4 py-3 text-sm text-[var(--danger)]">{error}</div> : null}
      {status ? <div className="rounded-2xl border border-[var(--success)] bg-[color:var(--success)]/10 px-4 py-3 text-sm text-[var(--success)]">{status}</div> : null}

      <div className="grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
        <Card className="bg-[var(--surface)]">
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

            {previewView ? (
              <div className="rounded-[1.5rem] border border-[color:var(--border)] bg-[#faf8f4] p-4 text-sm">
                <p className="font-medium">{previewView.fileName}</p>
                <p className="mt-2 text-[var(--muted-foreground)]">
                  {previewView.totalMessages} messages, participants: {previewView.participants.join(" / ") || "unknown"}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Badge>{previewView.sourceType.toUpperCase()}</Badge>
                  <Badge>{previewView.totalMessages} messages</Badge>
                  <Badge>{previewView.participants.length} speakers</Badge>
                </div>
                {previewView.messageTypeBadges.length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {previewView.messageTypeBadges.map((item) => (
                      <Badge key={item}>{item}</Badge>
                    ))}
                  </div>
                ) : null}
                {previewView.metadataEntries.length > 0 ? (
                  <div className="mt-4 grid gap-2 sm:grid-cols-2">
                    {previewView.metadataEntries.map((entry) => (
                      <div
                        key={entry.label}
                        className="rounded-xl border border-[color:var(--border)] bg-[var(--surface)] px-3 py-2"
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
          <Card className="bg-[var(--surface)]">
            <CardHeader>
              <CardTitle>Normalized Message Preview</CardTitle>
              <CardDescription>Confirm speaker, role, and content before the data enters the shared import registry.</CardDescription>
            </CardHeader>
            <CardContent>
              {previewView ? (
                <div className="overflow-hidden rounded-[1.25rem] border border-[color:var(--border)]">
                  <Table>
                    <thead className="bg-[var(--surface-2)]">
                      <tr>
                        <TableHead>#</TableHead>
                        <TableHead>Speaker</TableHead>
                        <TableHead>Role</TableHead>
                        <TableHead>Content</TableHead>
                      </tr>
                    </thead>
                    <tbody>
                      {previewView.normalizedRows.slice(0, 20).map((row) => (
                        <TableRow key={`${row.sequenceIndex}-${row.speaker}`}>
                          <TableCell>{row.sequenceIndex}</TableCell>
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

          <Card className="bg-[var(--surface)]">
            <CardHeader>
              <CardTitle>Committed Imports</CardTitle>
              <CardDescription>Saved imports stay available here for Persona extraction and later inspection.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {importCards.length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">No imports committed yet.</p>
              ) : (
                importCards.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-[1.25rem] border border-[color:var(--border)] bg-[#fffdf9] p-4"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium">{item.fileName}</p>
                      <Badge>{item.status}</Badge>
                      <Badge>{item.sourceType}</Badge>
                    </div>
                    <p className="mt-2 text-sm text-[var(--muted-foreground)]">{item.totalMessages} messages</p>
                    <p className="mt-1 text-sm text-[var(--muted-foreground)]">Participants: {item.participants}</p>
                    {item.metadataEntries.length > 0 ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {item.metadataEntries.map((entry) => (
                          <Badge key={`${item.id}-${entry.label}`}>{`${entry.label}: ${entry.value}`}</Badge>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
