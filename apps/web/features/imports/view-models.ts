import type { UUID } from "@agent/shared";

export type ImportMetadataEntryViewModel = {
  label: string;
  value: string;
};

export type ImportPreviewViewModel = {
  fileName: string;
  sourceType: string;
  totalMessages: number;
  participants: string[];
  messageTypeBadges: string[];
  metadataEntries: ImportMetadataEntryViewModel[];
  normalizedRows: Array<{
    sequenceIndex: number;
    speaker: string;
    role: string;
    content: string;
  }>;
};

export type ImportSummaryCardViewModel = {
  id: UUID;
  fileName: string;
  sourceType: string;
  status: string;
  totalMessages: number;
  participants: string;
  metadataEntries: ImportMetadataEntryViewModel[];
};
