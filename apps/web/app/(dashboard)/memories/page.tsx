"use client";

import { useEffect, useMemo, useState } from "react";

import type { MemoryCandidateRecord, MemoryFactRecord, MemoryRecord, MemoryRevisionRecord } from "@agent/shared";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableCell, TableHead, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import {
  bootstrapUser,
  createMemory,
  getMemoryDebug,
  listMemoryCandidates,
  listMemories,
  runMemoryMaintenance,
  searchMemories,
  updateMemory,
  updateMemoryCandidate
} from "@/lib/api";

type MemoryType = "session" | "episodic" | "semantic" | "instruction";
type MemoryState = "active" | "pinned" | "archived" | "ignored";

function memoryLabel(memory: MemoryRecord) {
  return String(memory.metadata?.memory_label ?? "unknown");
}

function memorySource(memory: MemoryRecord) {
  return String(memory.metadata?.source ?? "unknown");
}

function memoryState(memory: MemoryRecord) {
  return String(memory.metadata?.state ?? "active") as MemoryState;
}

function memoryScore(memory: MemoryRecord) {
  return (memory.importance_score + memory.confidence_score) / 2;
}

function dedupeGroups(memories: MemoryRecord[]) {
  const groups = new Map<string, MemoryRecord[]>();
  memories.forEach((memory) => {
    const key = String(memory.metadata?.dedupe_key ?? "");
    if (!key) return;
    groups.set(key, [...(groups.get(key) ?? []), memory]);
  });
  return [...groups.values()].filter((group) => group.length > 1);
}

export default function MemoriesPage() {
  const [userId, setUserId] = useState("");
  const [memories, setMemories] = useState<MemoryRecord[]>([]);
  const [recentMemories, setRecentMemories] = useState<MemoryRecord[]>([]);
  const [recentEpisodes, setRecentEpisodes] = useState<
    Array<{
      id: string;
      source_type: string;
      speaker_role?: string | null;
      raw_text: string;
      summary_short?: string | null;
      importance: number;
      occurred_at?: string | null;
    }>
  >([]);
  const [recentFacts, setRecentFacts] = useState<MemoryFactRecord[]>([]);
  const [recentRevisions, setRecentRevisions] = useState<MemoryRevisionRecord[]>([]);
  const [recentCandidates, setRecentCandidates] = useState<MemoryCandidateRecord[]>([]);
  const [profileSummary, setProfileSummary] = useState("");
  const [profileSnapshot, setProfileSnapshot] = useState<Record<string, unknown>>({});
  const [userProfileSnapshot, setUserProfileSnapshot] = useState<Record<string, unknown>>({});
  const [relationshipStateSnapshot, setRelationshipStateSnapshot] = useState<Record<string, unknown>>({});
  const [conflictGroups, setConflictGroups] = useState<
    Array<{
      group_id: string;
      fact_key: string;
      items: Array<{
        id: string;
        content: string;
        state: string;
        current_version: boolean;
        polarity?: string | null;
      }>;
    }>
  >([]);
  const [lifecycleCounts, setLifecycleCounts] = useState<Record<string, number>>({});
  const [query, setQuery] = useState("");
  const [content, setContent] = useState("");
  const [memoryType, setMemoryType] = useState<MemoryType>("semantic");
  const [filterType, setFilterType] = useState("all");
  const [filterSource, setFilterSource] = useState("all");
  const [filterState, setFilterState] = useState("all");
  const [minScore, setMinScore] = useState("0");
  const [showDedupeOnly, setShowDedupeOnly] = useState(false);
  const [totalMemories, setTotalMemories] = useState(0);
  const [totalEpisodes, setTotalEpisodes] = useState(0);
  const [totalFacts, setTotalFacts] = useState(0);
  const [totalRevisions, setTotalRevisions] = useState(0);
  const [candidateCounts, setCandidateCounts] = useState<Record<string, number>>({});
  const [qdrantAvailable, setQdrantAvailable] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  async function loadMemoryState() {
    const [memoryRows, debug, pendingCandidates] = await Promise.all([
      listMemories(),
      getMemoryDebug(),
      listMemoryCandidates({ status: "pending", limit: 20 })
    ]);
    setMemories(memoryRows);
    setRecentMemories(debug.recent_memories);
    setRecentEpisodes(debug.recent_episodes);
    setRecentFacts(debug.recent_facts);
    setRecentRevisions(debug.recent_revisions);
    setRecentCandidates(pendingCandidates.length > 0 ? pendingCandidates : debug.recent_candidates);
    setTotalMemories(debug.total_memories);
    setTotalEpisodes(debug.total_episodes);
    setTotalFacts(debug.total_facts);
    setTotalRevisions(debug.total_revisions);
    setCandidateCounts(debug.candidate_counts);
    setQdrantAvailable(debug.qdrant_available);
    setProfileSummary(debug.profile_summary);
    setProfileSnapshot(debug.profile_snapshot);
    setUserProfileSnapshot(debug.user_profile_snapshot);
    setRelationshipStateSnapshot(debug.relationship_state_snapshot);
    setConflictGroups(debug.conflict_groups);
    setLifecycleCounts(debug.lifecycle_counts);
  }

  useEffect(() => {
    async function bootstrap() {
      const user = await bootstrapUser();
      setUserId(user.user.id);
      await loadMemoryState();
    }

    bootstrap().catch((reason) => {
      setError(reason instanceof Error ? reason.message : "Memory page bootstrap failed.");
    });
  }, []);

  async function handleCreateMemory() {
    if (!content.trim() || !userId) return;
    setError("");
    setStatus("");
    try {
      await createMemory({
        user_id: userId,
        memory_type: memoryType,
        content
      });
      setContent("");
      await loadMemoryState();
      setStatus("Memory created.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Memory create failed.");
    }
  }

  async function handleSearch() {
    if (!query.trim() || !userId) return;
    setError("");
    setStatus("");
    try {
      setMemories(
        await searchMemories({
          user_id: userId,
          query,
          limit: 20
        })
      );
      setStatus("Memory search complete.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Memory search failed.");
    }
  }

  async function handleMemoryState(memory: MemoryRecord, nextState: MemoryState) {
    try {
      await updateMemory(memory.id!, {
        metadata: {
          ...memory.metadata,
          state: nextState,
          pinned: nextState === "pinned"
        }
      });
      await loadMemoryState();
      setStatus(`Memory marked as ${nextState}.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Memory update failed.");
    }
  }

  async function handleMaintenanceRun() {
    try {
      setError("");
      setStatus("");
      const report = await runMemoryMaintenance();
      await loadMemoryState();
      setStatus(
        `Maintenance complete: ${report.facts_decayed} decayed, ${report.facts_archived} archived, ${report.candidates_ignored} candidates ignored.`
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Memory maintenance failed.");
    }
  }

  async function handleCandidateReview(candidate: MemoryCandidateRecord, nextStatus: "approved" | "rejected") {
    try {
      setError("");
      setStatus("");
      await updateMemoryCandidate(candidate.id, {
        status: nextStatus,
        reviewer_type: "human"
      });
      await loadMemoryState();
      setStatus(`Candidate ${nextStatus}.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Candidate review failed.");
    }
  }

  const filteredMemories = useMemo(() => {
    const threshold = Number(minScore) || 0;
    const rows = memories.filter((memory) => {
      if (filterType !== "all" && memory.memory_type !== filterType) return false;
      if (filterSource !== "all" && memorySource(memory) !== filterSource) return false;
      if (filterState !== "all" && memoryState(memory) !== filterState) return false;
      if (memoryScore(memory) < threshold) return false;
      return true;
    });

    if (!showDedupeOnly) return rows;
    const duplicateKeys = new Set(
      dedupeGroups(rows).map((group) => String(group[0]?.metadata?.dedupe_key ?? ""))
    );
    return rows.filter((memory) => duplicateKeys.has(String(memory.metadata?.dedupe_key ?? "")));
  }, [filterSource, filterState, filterType, memories, minScore, showDedupeOnly]);

  const duplicateGroups = useMemo(() => dedupeGroups(filteredMemories), [filteredMemories]);
  const availableSources = useMemo(
    () => [...new Set(memories.map((memory) => memorySource(memory)))].sort(),
    [memories]
  );

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Quality"
        title="Memory Validation"
        description="Curate memory quality with reinforcement, conflict resolution, and a live long-term profile summary instead of treating every write as an isolated note."
        badge="Profile + Conflict"
      />

      {error ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
      {status ? <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{status}</div> : null}

      <div className="grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Write and Search</CardTitle>
              <CardDescription>Manual write is useful when you want to inspect reinforcement, conflict replacement, and recall behavior quickly.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <Badge>{totalMemories} total</Badge>
                <Badge>{totalEpisodes} episodes</Badge>
                <Badge>{totalFacts} facts</Badge>
                <Badge>{totalRevisions} revisions</Badge>
                <Badge>{candidateCounts.pending ?? 0} pending review</Badge>
                <Badge>{qdrantAvailable ? "Qdrant ready" : "Qdrant fallback"}</Badge>
                <Badge>{lifecycleCounts.active ?? 0} active</Badge>
                <Badge>{lifecycleCounts.pinned ?? 0} pinned</Badge>
                <Badge>{lifecycleCounts.superseded ?? 0} superseded</Badge>
              </div>

            <div className="space-y-2">
              <Label>Memory Type</Label>
              <select
                className="w-full rounded-2xl border border-[color:var(--border)] bg-white px-4 py-3 text-sm"
                value={memoryType}
                onChange={(event) => setMemoryType(event.target.value as MemoryType)}
              >
                <option value="session">session</option>
                <option value="episodic">episodic</option>
                <option value="semantic">semantic</option>
                <option value="instruction">instruction</option>
              </select>
            </div>

            <div className="space-y-2">
              <Label>New Memory</Label>
              <Textarea value={content} onChange={(event) => setContent(event.target.value)} />
            </div>
            <Button className="w-full" disabled={!content.trim() || !userId} onClick={handleCreateMemory}>
              Create Memory
            </Button>

            <div className="space-y-2">
              <Label>Recall Query</Label>
              <Input value={query} onChange={(event) => setQuery(event.target.value)} />
            </div>
            <div className="flex gap-3">
              <Button variant="secondary" className="flex-1" disabled={!query.trim() || !userId} onClick={handleSearch}>
                Search
              </Button>
              <Button variant="ghost" className="flex-1" onClick={() => loadMemoryState().catch(() => undefined)}>
                Refresh
              </Button>
            </div>
            <Button variant="secondary" className="w-full" onClick={() => handleMaintenanceRun().catch(() => undefined)}>
              Run Maintenance
            </Button>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Filters and States</CardTitle>
              <CardDescription>Filter by type, source, state, and score before you pin, archive, or ignore memories.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-5">
              <div className="space-y-2">
                <Label>Type</Label>
                <select
                  className="w-full rounded-2xl border border-[color:var(--border)] bg-white px-4 py-3 text-sm"
                  value={filterType}
                  onChange={(event) => setFilterType(event.target.value)}
                >
                  <option value="all">all</option>
                  <option value="session">session</option>
                  <option value="episodic">episodic</option>
                  <option value="semantic">semantic</option>
                  <option value="instruction">instruction</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label>Source</Label>
                <select
                  className="w-full rounded-2xl border border-[color:var(--border)] bg-white px-4 py-3 text-sm"
                  value={filterSource}
                  onChange={(event) => setFilterSource(event.target.value)}
                >
                  <option value="all">all</option>
                  {availableSources.map((source) => (
                    <option key={source} value={source}>
                      {source}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label>State</Label>
                <select
                  className="w-full rounded-2xl border border-[color:var(--border)] bg-white px-4 py-3 text-sm"
                  value={filterState}
                  onChange={(event) => setFilterState(event.target.value)}
                >
                  <option value="all">all</option>
                  <option value="active">active</option>
                  <option value="pinned">pinned</option>
                  <option value="archived">archived</option>
                  <option value="ignored">ignored</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label>Min Score</Label>
                <Input value={minScore} onChange={(event) => setMinScore(event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Dedupe View</Label>
                <Button variant="secondary" className="w-full" onClick={() => setShowDedupeOnly((current) => !current)}>
                  {showDedupeOnly ? "Show All" : "Duplicates Only"}
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Long-Term Profile</CardTitle>
              <CardDescription>Stable instructions and preferences are merged into a lightweight profile that can steer later replies.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {profileSummary ? (
                <div className="rounded-[1.25rem] border border-[color:var(--border)] bg-[#fffdf9] p-4 text-sm leading-6">
                  <p className="whitespace-pre-wrap">{profileSummary}</p>
                </div>
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">No long-term profile yet.</p>
              )}

              {Array.isArray(profileSnapshot.by_bucket) ? null : (
                <div className="grid gap-3 md:grid-cols-3">
                  {Object.entries((profileSnapshot.by_bucket as Record<string, unknown>) ?? {}).map(([bucket, value]) => (
                    <div key={bucket} className="rounded-[1rem] border border-[color:var(--border)] bg-[#faf8f4] p-4">
                      <p className="text-sm font-medium capitalize">{bucket}</p>
                      <div className="mt-3 space-y-2 text-sm text-[var(--muted-foreground)]">
                        {Array.isArray(value) && value.length > 0 ? (
                          value.map((item, index) => <p key={index}>{String(item)}</p>)
                        ) : (
                          <p>No entries.</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Structured Snapshots</CardTitle>
              <CardDescription>User profile and relationship state are rebuilt from active facts so the companion has something more stable than freeform notes.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 lg:grid-cols-2">
              <div className="space-y-3 rounded-[1.25rem] border border-[color:var(--border)] bg-[#fffdf9] p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium">User Profile</p>
                  {userProfileSnapshot.profile_version ? <Badge>v{String(userProfileSnapshot.profile_version)}</Badge> : null}
                  {userProfileSnapshot.source_fact_count ? <Badge>{String(userProfileSnapshot.source_fact_count)} facts</Badge> : null}
                </div>
                {Object.keys(userProfileSnapshot).length > 0 ? (
                  <pre className="overflow-x-auto rounded-[1rem] bg-[#faf8f4] p-3 text-xs leading-6">
                    {JSON.stringify(userProfileSnapshot, null, 2)}
                  </pre>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">No structured profile yet.</p>
                )}
              </div>

              <div className="space-y-3 rounded-[1.25rem] border border-[color:var(--border)] bg-[#fffdf9] p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium">Relationship State</p>
                  {relationshipStateSnapshot.relationship_stage ? (
                    <Badge>{String(relationshipStateSnapshot.relationship_stage)}</Badge>
                  ) : null}
                  {relationshipStateSnapshot.preferred_tone ? (
                    <Badge>{String(relationshipStateSnapshot.preferred_tone)}</Badge>
                  ) : null}
                </div>
                {Object.keys(relationshipStateSnapshot).length > 0 ? (
                  <pre className="overflow-x-auto rounded-[1rem] bg-[#faf8f4] p-3 text-xs leading-6">
                    {JSON.stringify(relationshipStateSnapshot, null, 2)}
                  </pre>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">No relationship snapshot yet.</p>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Recent Writes</CardTitle>
              <CardDescription>Inspect how preference, instruction, and episodic memories are labeled, reinforced, and stored.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {recentMemories.length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">No memories yet.</p>
              ) : (
                recentMemories.slice(0, 6).map((memory) => (
                  <div key={memory.id} className="rounded-[1.25rem] border border-[color:var(--border)] bg-[#fffdf9] p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge>{memory.memory_type}</Badge>
                      <Badge>{memoryLabel(memory)}</Badge>
                      <Badge>{String(memory.metadata?.write_strategy ?? "strategy:unknown")}</Badge>
                      <Badge>{memoryState(memory)}</Badge>
                      <Badge>importance {memory.importance_score}</Badge>
                      <Badge>confidence {memory.confidence_score}</Badge>
                      <Badge>reinforce {String(memory.metadata?.reinforcement_count ?? 1)}</Badge>
                      <Badge>{String(memory.metadata?.current_version ?? true) ? "current" : "older"}</Badge>
                    </div>
                    <p className="mt-3 text-sm leading-6">{memory.content}</p>
                    <p className="mt-2 text-xs text-[var(--muted-foreground)]">
                      source: {memorySource(memory)} | fact key: {String(memory.metadata?.fact_key ?? "n/a")} | dedupe key: {String(memory.metadata?.dedupe_key ?? "n/a")}
                    </p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Episode Ledger</CardTitle>
              <CardDescription>Every memory write appends a source episode first, so facts and revisions can point back to a concrete event trail.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {recentEpisodes.length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">No episodes yet.</p>
              ) : (
                recentEpisodes.slice(0, 6).map((episode) => (
                  <div key={episode.id} className="rounded-[1.25rem] border border-[color:var(--border)] bg-[#fffdf9] p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge>{episode.source_type}</Badge>
                      {episode.speaker_role ? <Badge>{episode.speaker_role}</Badge> : null}
                      <Badge>importance {episode.importance}</Badge>
                    </div>
                    <p className="mt-3 text-sm leading-6">{episode.summary_short || episode.raw_text}</p>
                    {episode.occurred_at ? (
                      <p className="mt-2 text-xs text-[var(--muted-foreground)]">
                        occurred: {new Date(episode.occurred_at).toLocaleString()}
                      </p>
                    ) : null}
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Fact Ledger</CardTitle>
              <CardDescription>Canonical facts carry the stable state the companion should recall, while old revisions stop steering active behavior.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {recentFacts.length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">No facts yet.</p>
              ) : (
                recentFacts.slice(0, 6).map((fact) => (
                  <div key={fact.id} className="rounded-[1.25rem] border border-[color:var(--border)] bg-[#fffdf9] p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge>{fact.fact_type}</Badge>
                      <Badge>{fact.status}</Badge>
                      <Badge>{fact.subject_kind}</Badge>
                      <Badge>confidence {fact.confidence}</Badge>
                      <Badge>importance {fact.importance}</Badge>
                      <Badge>stable {fact.stability_score}</Badge>
                      <Badge>reinforce {fact.reinforcement_count}</Badge>
                    </div>
                    <p className="mt-3 text-sm leading-6">{fact.value_text || JSON.stringify(fact.value_json)}</p>
                    <p className="mt-2 text-xs text-[var(--muted-foreground)]">
                      predicate: {fact.predicate_key} | key: {fact.normalized_key} | sensitivity: {fact.sensitivity}
                    </p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Revision History</CardTitle>
              <CardDescription>Each create, reinforce, and supersede operation stays visible, so we can audit how a memory changed over time.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {recentRevisions.length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">No revisions yet.</p>
              ) : (
                recentRevisions.slice(0, 6).map((revision) => (
                  <div
                    key={revision.id}
                    className="rounded-[1.25rem] border border-[color:var(--border)] bg-[#fffdf9] p-4"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge>{revision.op}</Badge>
                      <Badge>revision {revision.revision_no}</Badge>
                      <Badge>{revision.author_type}</Badge>
                      {revision.conflict_group_id ? <Badge>{revision.conflict_group_id}</Badge> : null}
                    </div>
                    <p className="mt-3 text-sm leading-6">
                      {revision.content_text || JSON.stringify(revision.value_json)}
                    </p>
                    <p className="mt-2 text-xs text-[var(--muted-foreground)]">
                      fact: {revision.fact_id} | delta: {revision.confidence_delta}
                      {revision.valid_to ? ` | retired: ${new Date(revision.valid_to).toLocaleString()}` : ""}
                    </p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Review Queue</CardTitle>
              <CardDescription>Candidate memories surface extraction quality before we make this layer the gatekeeper for long-term writes.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {recentCandidates.length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">No pending candidates right now.</p>
              ) : (
                recentCandidates.slice(0, 8).map((candidate) => (
                  <div
                    key={candidate.id}
                    className="rounded-[1.25rem] border border-[color:var(--border)] bg-[#fffdf9] p-4"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge>{candidate.candidate_type}</Badge>
                      <Badge>{candidate.proposed_action}</Badge>
                      <Badge>{candidate.status}</Badge>
                      {candidate.proposed_value?.fact_id ? <Badge>fact linked</Badge> : <Badge>gated</Badge>}
                      <Badge>salience {candidate.salience_score}</Badge>
                      <Badge>confidence {candidate.confidence_score}</Badge>
                      <Badge>{candidate.sensitivity}</Badge>
                    </div>
                    <p className="mt-3 text-sm leading-6">{candidate.extracted_text}</p>
                    <p className="mt-2 text-xs text-[var(--muted-foreground)]">
                      key: {candidate.normalized_key} | reasons:{" "}
                      {candidate.reason_codes.length > 0
                        ? candidate.reason_codes.map((item) => String(item)).join(", ")
                        : "none"}
                    </p>
                    <div className="mt-3 flex gap-3">
                      <Button
                        className="h-9 px-4"
                        onClick={() => handleCandidateReview(candidate, "approved").catch(() => undefined)}
                      >
                        Approve
                      </Button>
                      <Button
                        className="h-9 px-4"
                        variant="secondary"
                        onClick={() => handleCandidateReview(candidate, "rejected").catch(() => undefined)}
                      >
                        Reject
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Conflict Groups</CardTitle>
              <CardDescription>When newer instructions or preferences contradict older ones, the older version is marked and removed from active recall.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {conflictGroups.length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">No conflict groups yet.</p>
              ) : (
                conflictGroups.map((group) => (
                  <div key={group.group_id} className="rounded-[1.25rem] border border-[color:var(--border)] bg-[#fffdf9] p-4">
                    <p className="text-sm font-medium">{group.fact_key || group.group_id}</p>
                    <div className="mt-3 space-y-2">
                      {group.items.map((item) => (
                        <div key={item.id} className="rounded-2xl bg-[#faf8f4] p-3 text-sm leading-6">
                          <div className="flex flex-wrap gap-2">
                            <Badge>{item.state}</Badge>
                            <Badge>{item.current_version ? "current" : "superseded"}</Badge>
                            {item.polarity ? <Badge>{item.polarity}</Badge> : null}
                          </div>
                          <p className="mt-2">{item.content}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Potential Duplicates</CardTitle>
              <CardDescription>Simple dedupe view based on the stored `dedupe_key` metadata.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {duplicateGroups.length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">No duplicate groups in the current filtered set.</p>
              ) : (
                duplicateGroups.map((group) => (
                  <div key={String(group[0]?.metadata?.dedupe_key ?? group[0]?.id)} className="rounded-[1.25rem] border border-[color:var(--border)] bg-[#fffdf9] p-4">
                    <p className="text-sm font-medium">{String(group[0]?.metadata?.dedupe_key ?? "unknown")}</p>
                    <div className="mt-3 space-y-2">
                      {group.map((memory) => (
                        <div key={memory.id} className="rounded-2xl bg-[#faf8f4] p-3 text-sm leading-6">
                          <div className="flex flex-wrap gap-2">
                            <Badge>{memoryLabel(memory)}</Badge>
                            <Badge>{memoryState(memory)}</Badge>
                          </div>
                          <p className="mt-2">{memory.content}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Memory Table</CardTitle>
              <CardDescription>Filtered list with quick curator actions.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-hidden rounded-[1.25rem] border border-[color:var(--border)]">
                <Table>
                  <thead className="bg-[#faf8f4]">
                    <tr>
                      <TableHead>Type</TableHead>
                      <TableHead>Label</TableHead>
                      <TableHead>Content</TableHead>
                      <TableHead>Score</TableHead>
                      <TableHead>Source</TableHead>
                      <TableHead>State</TableHead>
                      <TableHead>Actions</TableHead>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredMemories.map((memory) => (
                      <TableRow key={memory.id}>
                        <TableCell>{memory.memory_type}</TableCell>
                        <TableCell>{memoryLabel(memory)}</TableCell>
                        <TableCell>{memory.content}</TableCell>
                        <TableCell>{`${memory.importance_score} / ${memory.confidence_score}`}</TableCell>
                        <TableCell>{memorySource(memory)}</TableCell>
                        <TableCell>{memoryState(memory)}</TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-2">
                            <Button variant="secondary" onClick={() => handleMemoryState(memory, "pinned")}>
                              Pin
                            </Button>
                            <Button variant="secondary" onClick={() => handleMemoryState(memory, "archived")}>
                              Archive
                            </Button>
                            <Button variant="secondary" onClick={() => handleMemoryState(memory, "ignored")}>
                              Ignore
                            </Button>
                            <Button variant="ghost" onClick={() => handleMemoryState(memory, "active")}>
                              Reset
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </tbody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
