import type {
  MemoryCandidateRecord,
  MemoryEpisodeRecord,
  MemoryFactRecord,
  MemoryRecord,
  MemoryRevisionRecord
} from "@agent/shared";

import type {
  MemoryConflictGroupViewModel,
  MemoryDashboardViewModel,
  MemoryDuplicateGroupViewModel,
  MemoryEpisodeViewModel,
  MemoryFactViewModel,
  MemoryItemViewModel,
  MemoryRevisionViewModel,
  MemoryCandidateViewModel,
  MemoryState,
  MemoryStructuredSnapshotViewModel
} from "./view-models";

export type MemoryDebugDto = {
  qdrant_available: boolean;
  total_memories: number;
  total_episodes: number;
  total_facts: number;
  total_revisions: number;
  candidate_counts: Record<string, number>;
  recent_memories: MemoryRecord[];
  recent_episodes: MemoryEpisodeRecord[];
  recent_facts: MemoryFactRecord[];
  recent_revisions: MemoryRevisionRecord[];
  recent_candidates: MemoryCandidateRecord[];
  profile_summary: string;
  profile_snapshot: Record<string, unknown>;
  user_profile_snapshot: Record<string, unknown>;
  relationship_state_snapshot: Record<string, unknown>;
  conflict_groups: Array<{
    group_id: string;
    fact_key: string;
    items: Array<{
      id: string;
      content: string;
      state: string;
      current_version: boolean;
      polarity?: string | null;
    }>;
  }>;
  lifecycle_counts: Record<string, number>;
};

function toNumber(value: number | undefined, fallback = 0) {
  return typeof value === "number" ? value : fallback;
}

function toJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}

function toDateLabel(value?: string | null) {
  return value ? new Date(value).toLocaleString() : null;
}

export function toMemoryItem(memory: MemoryRecord): MemoryItemViewModel {
  const metadata = memory.metadata ?? {};
  return {
    id: memory.id,
    type: memory.memory_type,
    label: String(metadata.memory_label ?? "unknown"),
    source: String(metadata.source ?? "unknown"),
    state: String(metadata.state ?? "active") as MemoryState,
    score: (memory.importance_score + memory.confidence_score) / 2,
    importance: memory.importance_score,
    confidence: memory.confidence_score,
    content: memory.content,
    writeStrategy: String(metadata.write_strategy ?? "strategy:unknown"),
    reinforcementCount: Number(metadata.reinforcement_count ?? 1),
    currentVersion: Boolean(metadata.current_version ?? true),
    factKey: String(metadata.fact_key ?? "n/a"),
    dedupeKey: String(metadata.dedupe_key ?? ""),
    metadataForPatch: metadata
  };
}

export function toMemoryItems(memories: MemoryRecord[]) {
  return memories.map(toMemoryItem);
}

export function filterMemoryItems(
  memories: MemoryItemViewModel[],
  filters: {
    type: string;
    source: string;
    state: string;
    minScore: string;
    dedupeOnly: boolean;
  }
) {
  const threshold = Number(filters.minScore) || 0;
  const rows = memories.filter((memory) => {
    if (filters.type !== "all" && memory.type !== filters.type) return false;
    if (filters.source !== "all" && memory.source !== filters.source) return false;
    if (filters.state !== "all" && memory.state !== filters.state) return false;
    if (memory.score < threshold) return false;
    return true;
  });

  if (!filters.dedupeOnly) return rows;
  const duplicateKeys = new Set(buildDuplicateGroups(rows).map((group) => group.id));
  return rows.filter((memory) => duplicateKeys.has(memory.dedupeKey));
}

export function buildDuplicateGroups(memories: MemoryItemViewModel[]): MemoryDuplicateGroupViewModel[] {
  const groups = new Map<string, MemoryItemViewModel[]>();
  memories.forEach((memory) => {
    if (!memory.dedupeKey) return;
    groups.set(memory.dedupeKey, [...(groups.get(memory.dedupeKey) ?? []), memory]);
  });
  return [...groups.entries()]
    .filter(([, items]) => items.length > 1)
    .map(([key, items]) => ({ id: key, label: key || "unknown", items }));
}

export function availableMemorySources(memories: MemoryItemViewModel[]) {
  return [...new Set(memories.map((memory) => memory.source))].sort();
}

export function buildMemoryStatePatch(memory: MemoryItemViewModel, nextState: MemoryState) {
  return {
    ...memory.metadataForPatch,
    state: nextState,
    pinned: nextState === "pinned"
  };
}

export function toEpisodeViewModel(episode: MemoryEpisodeRecord): MemoryEpisodeViewModel {
  return {
    id: episode.id,
    sourceType: episode.source_type,
    speakerRole: episode.speaker_role,
    text: episode.summary_short || episode.raw_text,
    importance: episode.importance,
    occurredAtLabel: toDateLabel(episode.occurred_at)
  };
}

export function toFactViewModel(fact: MemoryFactRecord): MemoryFactViewModel {
  return {
    id: fact.id,
    factType: fact.fact_type,
    status: fact.status,
    subjectKind: fact.subject_kind,
    confidence: fact.confidence,
    importance: fact.importance,
    stability: fact.stability_score,
    reinforcementCount: fact.reinforcement_count,
    value: fact.value_text || toJson(fact.value_json),
    predicateKey: fact.predicate_key,
    normalizedKey: fact.normalized_key,
    sensitivity: fact.sensitivity
  };
}

export function toRevisionViewModel(revision: MemoryRevisionRecord): MemoryRevisionViewModel {
  return {
    id: revision.id,
    factId: revision.fact_id,
    op: revision.op,
    revisionNo: revision.revision_no,
    authorType: revision.author_type,
    conflictGroupId: revision.conflict_group_id,
    value: revision.content_text || toJson(revision.value_json),
    confidenceDelta: revision.confidence_delta,
    retiredAtLabel: toDateLabel(revision.valid_to)
  };
}

export function toCandidateViewModel(candidate: MemoryCandidateRecord): MemoryCandidateViewModel {
  return {
    id: candidate.id,
    type: candidate.candidate_type,
    proposedAction: candidate.proposed_action,
    status: candidate.status,
    factLinked: Boolean(candidate.proposed_value?.fact_id),
    salience: candidate.salience_score,
    confidence: candidate.confidence_score,
    sensitivity: candidate.sensitivity,
    extractedText: candidate.extracted_text,
    normalizedKey: candidate.normalized_key,
    reasonLabel: candidate.reason_codes.length > 0 ? candidate.reason_codes.map((item) => String(item)).join(", ") : "none"
  };
}

function toStructuredSnapshot(snapshot: Record<string, unknown>): MemoryStructuredSnapshotViewModel {
  return {
    json: toJson(snapshot),
    profileVersion: snapshot.profile_version ? String(snapshot.profile_version) : null,
    sourceFactCount: snapshot.source_fact_count ? String(snapshot.source_fact_count) : null,
    relationshipStage: snapshot.relationship_stage ? String(snapshot.relationship_stage) : null,
    preferredTone: snapshot.preferred_tone ? String(snapshot.preferred_tone) : null,
    isEmpty: Object.keys(snapshot).length === 0
  };
}

export function toMemoryDashboard(debug: MemoryDebugDto): MemoryDashboardViewModel {
  const byBucket = debug.profile_snapshot.by_bucket as Record<string, unknown> | undefined;
  return {
    totalMemories: debug.total_memories,
    totalEpisodes: debug.total_episodes,
    totalFacts: debug.total_facts,
    totalRevisions: debug.total_revisions,
    pendingCandidateCount: toNumber(debug.candidate_counts.pending),
    qdrantAvailable: debug.qdrant_available,
    lifecycleActiveCount: toNumber(debug.lifecycle_counts.active),
    lifecyclePinnedCount: toNumber(debug.lifecycle_counts.pinned),
    lifecycleSupersededCount: toNumber(debug.lifecycle_counts.superseded),
    profileSummary: debug.profile_summary,
    profileBuckets: Object.entries(byBucket ?? {}).map(([bucket, value]) => ({
      bucket,
      entries: Array.isArray(value) ? value.map((item) => String(item)) : []
    })),
    userProfile: toStructuredSnapshot(debug.user_profile_snapshot),
    relationshipState: toStructuredSnapshot(debug.relationship_state_snapshot),
    conflictGroups: debug.conflict_groups.map((group): MemoryConflictGroupViewModel => ({
      id: group.group_id,
      label: group.fact_key || group.group_id,
      items: group.items.map((item) => ({
        id: item.id,
        content: item.content,
        state: item.state,
        currentVersion: item.current_version,
        polarity: item.polarity
      }))
    }))
  };
}
