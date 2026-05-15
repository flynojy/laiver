import type { MemoryType, UUID } from "@agent/shared";

export type MemoryState = "active" | "pinned" | "archived" | "ignored";

export type MemoryItemViewModel = {
  id?: UUID;
  type: MemoryType;
  label: string;
  source: string;
  state: MemoryState;
  score: number;
  importance: number;
  confidence: number;
  content: string;
  writeStrategy: string;
  reinforcementCount: number;
  currentVersion: boolean;
  factKey: string;
  dedupeKey: string;
  metadataForPatch: Record<string, unknown>;
};

export type MemoryEpisodeViewModel = {
  id: UUID;
  sourceType: string;
  speakerRole?: string | null;
  text: string;
  importance: number;
  occurredAtLabel?: string | null;
};

export type MemoryFactViewModel = {
  id: UUID;
  factType: string;
  status: string;
  subjectKind: string;
  confidence: number;
  importance: number;
  stability: number;
  reinforcementCount: number;
  value: string;
  predicateKey: string;
  normalizedKey: string;
  sensitivity: string;
};

export type MemoryRevisionViewModel = {
  id: UUID;
  factId: UUID;
  op: string;
  revisionNo: number;
  authorType: string;
  conflictGroupId?: string | null;
  value: string;
  confidenceDelta: number;
  retiredAtLabel?: string | null;
};

export type MemoryCandidateViewModel = {
  id: UUID;
  type: string;
  proposedAction: string;
  status: string;
  factLinked: boolean;
  salience: number;
  confidence: number;
  sensitivity: string;
  extractedText: string;
  normalizedKey: string;
  reasonLabel: string;
};

export type MemoryConflictItemViewModel = {
  id: string;
  content: string;
  state: string;
  currentVersion: boolean;
  polarity?: string | null;
};

export type MemoryConflictGroupViewModel = {
  id: string;
  label: string;
  items: MemoryConflictItemViewModel[];
};

export type MemoryDuplicateGroupViewModel = {
  id: string;
  label: string;
  items: MemoryItemViewModel[];
};

export type MemoryProfileBucketViewModel = {
  bucket: string;
  entries: string[];
};

export type MemoryStructuredSnapshotViewModel = {
  json: string;
  profileVersion?: string | null;
  sourceFactCount?: string | null;
  relationshipStage?: string | null;
  preferredTone?: string | null;
  isEmpty: boolean;
};

export type MemoryDashboardViewModel = {
  totalMemories: number;
  totalEpisodes: number;
  totalFacts: number;
  totalRevisions: number;
  pendingCandidateCount: number;
  qdrantAvailable: boolean;
  lifecycleActiveCount: number;
  lifecyclePinnedCount: number;
  lifecycleSupersededCount: number;
  profileSummary: string;
  profileBuckets: MemoryProfileBucketViewModel[];
  userProfile: MemoryStructuredSnapshotViewModel;
  relationshipState: MemoryStructuredSnapshotViewModel;
  conflictGroups: MemoryConflictGroupViewModel[];
};
