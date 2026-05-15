import type { ImportPreviewSummary, NormalizedMessage } from "@agent/shared";

import type { ImportDetail, ImportPreview } from "./client";

import type { ImportMetadataEntryViewModel, ImportPreviewViewModel, ImportSummaryCardViewModel } from "./view-models";

const METADATA_FIELDS = [
  { key: "source_format", label: "Format" },
  { key: "conversation_owner", label: "Owner" },
  { key: "export_tool", label: "Export Tool" },
  { key: "export_version", label: "Export Version" },
  { key: "platform", label: "Platform" },
  { key: "exported_at", label: "Exported At" }
] as const;

export function metadataEntries(metadata?: ImportSourceLike): ImportMetadataEntryViewModel[] {
  const entries: ImportMetadataEntryViewModel[] = [];
  for (const field of METADATA_FIELDS) {
    const value = metadata?.[field.key];
    if (typeof value === "string" && value.trim()) {
      entries.push({ label: field.label, value });
    }
  }
  return entries;
}

export function messageTypeBadges(metadata?: ImportSourceLike) {
  const value = metadata?.message_types;
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
    : [];
}

type ImportSourceLike = ImportPreviewSummary["source_metadata"] | Record<string, unknown> | undefined;

export function toImportPreviewViewModel(preview: ImportPreview): ImportPreviewViewModel {
  return {
    fileName: preview.file_name,
    sourceType: preview.source_type,
    totalMessages: preview.total_messages,
    participants: preview.detected_participants,
    messageTypeBadges: messageTypeBadges(preview.source_metadata),
    metadataEntries: metadataEntries(preview.source_metadata),
    normalizedRows: preview.normalized_messages.map((row: NormalizedMessage) => ({
      sequenceIndex: row.sequence_index,
      speaker: row.speaker,
      role: row.role,
      content: row.content
    }))
  };
}

export function toImportSummaryCardViewModel(item: ImportDetail): ImportSummaryCardViewModel {
  const summary = item.import_job.normalized_summary ?? {};
  const participants = Array.isArray(summary.participants) ? summary.participants.join(" / ") : "unknown";
  const totalMessages =
    typeof summary.total_messages === "number" ? summary.total_messages : item.normalized_messages.length;
  return {
    id: item.import_job.id,
    fileName: item.import_job.file_name,
    sourceType: item.import_job.source_type,
    status: item.import_job.status,
    totalMessages,
    participants,
    metadataEntries: metadataEntries(summary)
  };
}
