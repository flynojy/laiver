"use client";

import { useEffect, useMemo, useState } from "react";

import type { MemoryType } from "@agent/shared";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableCell, TableHead, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import {
  availableMemorySources,
  buildDuplicateGroups,
  buildMemoryStatePatch,
  filterMemoryItems,
  toCandidateViewModel,
  toEpisodeViewModel,
  toFactViewModel,
  toMemoryDashboard,
  toMemoryItems,
  toRevisionViewModel
} from "@/features/memories/mappers";
import type {
  MemoryCandidateViewModel,
  MemoryDashboardViewModel,
  MemoryEpisodeViewModel,
  MemoryFactViewModel,
  MemoryItemViewModel,
  MemoryRevisionViewModel,
  MemoryState
} from "@/features/memories/view-models";
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
} from "@/features/memories/client";

export default function MemoriesPage() {
  const [userId, setUserId] = useState("");
  const [memories, setMemories] = useState<MemoryItemViewModel[]>([]);
  const [recentMemories, setRecentMemories] = useState<MemoryItemViewModel[]>([]);
  const [recentEpisodes, setRecentEpisodes] = useState<MemoryEpisodeViewModel[]>([]);
  const [recentFacts, setRecentFacts] = useState<MemoryFactViewModel[]>([]);
  const [recentRevisions, setRecentRevisions] = useState<MemoryRevisionViewModel[]>([]);
  const [recentCandidates, setRecentCandidates] = useState<MemoryCandidateViewModel[]>([]);
  const [dashboard, setDashboard] = useState<MemoryDashboardViewModel>({
    totalMemories: 0,
    totalEpisodes: 0,
    totalFacts: 0,
    totalRevisions: 0,
    pendingCandidateCount: 0,
    qdrantAvailable: false,
    lifecycleActiveCount: 0,
    lifecyclePinnedCount: 0,
    lifecycleSupersededCount: 0,
    profileSummary: "",
    profileBuckets: [],
    userProfile: { json: "{}", isEmpty: true },
    relationshipState: { json: "{}", isEmpty: true },
    conflictGroups: []
  });
  const [query, setQuery] = useState("");
  const [content, setContent] = useState("");
  const [memoryType, setMemoryType] = useState<MemoryType>("semantic");
  const [filterType, setFilterType] = useState("all");
  const [filterSource, setFilterSource] = useState("all");
  const [filterState, setFilterState] = useState("all");
  const [minScore, setMinScore] = useState("0");
  const [showDedupeOnly, setShowDedupeOnly] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  async function loadMemoryState() {
    const [memoryRows, debug, pendingCandidates] = await Promise.all([
      listMemories(),
      getMemoryDebug(),
      listMemoryCandidates({ status: "pending", limit: 20 })
    ]);
    const nextDashboard = toMemoryDashboard(debug);
    setMemories(toMemoryItems(memoryRows));
    setRecentMemories(toMemoryItems(debug.recent_memories));
    setRecentEpisodes(debug.recent_episodes.map(toEpisodeViewModel));
    setRecentFacts(debug.recent_facts.map(toFactViewModel));
    setRecentRevisions(debug.recent_revisions.map(toRevisionViewModel));
    setRecentCandidates((pendingCandidates.length > 0 ? pendingCandidates : debug.recent_candidates).map(toCandidateViewModel));
    setDashboard(nextDashboard);
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
      const results = await searchMemories({
          user_id: userId,
          query,
          limit: 20
        });
      setMemories(toMemoryItems(results));
      setStatus("Memory search complete.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Memory search failed.");
    }
  }

  async function handleMemoryState(memory: MemoryItemViewModel, nextState: MemoryState) {
    try {
      await updateMemory(memory.id!, {
        metadata: buildMemoryStatePatch(memory, nextState)
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

  async function handleCandidateReview(candidate: MemoryCandidateViewModel, nextStatus: "approved" | "rejected") {
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
    return filterMemoryItems(memories, {
      type: filterType,
      source: filterSource,
      state: filterState,
      minScore,
      dedupeOnly: showDedupeOnly
    });
  }, [filterSource, filterState, filterType, memories, minScore, showDedupeOnly]);

  const duplicateGroups = useMemo(() => buildDuplicateGroups(filteredMemories), [filteredMemories]);
  const availableSources = useMemo(() => availableMemorySources(memories), [memories]);
  const memoryPipeline = [
    {
      title: "Capture",
      detail: "Conversation turn becomes a memory row.",
      value: `${dashboard.totalMemories} rows`
    },
    {
      title: "Episode",
      detail: "Raw source event is preserved first.",
      value: `${dashboard.totalEpisodes} episodes`
    },
    {
      title: "Review",
      detail: "Candidate review gate before commit.",
      value: `${dashboard.pendingCandidateCount} pending`
    },
    {
      title: "Fact",
      detail: "Stable facts and revisions are tracked.",
      value: `${dashboard.totalFacts} facts / ${dashboard.totalRevisions} revisions`
    },
    {
      title: "Profile",
      detail: "Long-term summary rebuilt from active facts.",
      value: dashboard.profileSummary ? "ready" : "empty"
    },
    {
      title: "Recall",
      detail: "Vector search accelerates retrieval.",
      value: dashboard.qdrantAvailable ? "Qdrant ready" : "SQL fallback"
    }
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Quality"
        title="Memory Validation"
        description="Curate memory quality with reinforcement, conflict resolution, and a live long-term profile summary instead of treating every write as an isolated note."
        badge="Profile + Conflict"
      />

      {error ? <div className="rounded-2xl border border-[var(--danger)] bg-[color:var(--danger)]/10 px-4 py-3 text-sm text-[var(--danger)]">{error}</div> : null}
      {status ? <div className="rounded-2xl border border-[var(--success)] bg-[color:var(--success)]/10 px-4 py-3 text-sm text-[var(--success)]">{status}</div> : null}

      <Card className="bg-white/88">
        <CardHeader>
          <CardTitle>Memory Flow</CardTitle>
          <CardDescription>Writes are captured as episodes first, promoted to candidates and facts, then recalled through the profile and vector index.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
          {memoryPipeline.map((step) => (
            <div key={step.title} className="rounded-[1rem] border border-[color:var(--border)] bg-[#faf8f4] p-4">
              <p className="text-sm font-medium">{step.title}</p>
              <p className="mt-2 text-lg font-semibold">{step.value}</p>
              <p className="mt-2 text-xs leading-5 text-[var(--muted-foreground)]">{step.detail}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
          <Card className="bg-[var(--surface)]">
            <CardHeader>
              <CardTitle>Write and Search</CardTitle>
              <CardDescription>Manual write is useful when you want to inspect reinforcement, conflict replacement, and recall behavior quickly.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <Badge>{dashboard.totalMemories} total</Badge>
                <Badge>{dashboard.totalEpisodes} episodes</Badge>
                <Badge>{dashboard.totalFacts} facts</Badge>
                <Badge>{dashboard.totalRevisions} revisions</Badge>
                <Badge>{dashboard.pendingCandidateCount} pending review</Badge>
                <Badge>{dashboard.qdrantAvailable ? "Qdrant ready" : "Qdrant fallback"}</Badge>
                <Badge>{dashboard.lifecycleActiveCount} active</Badge>
                <Badge>{dashboard.lifecyclePinnedCount} pinned</Badge>
                <Badge>{dashboard.lifecycleSupersededCount} superseded</Badge>
              </div>

            <div className="space-y-2">
              <Label>Memory Type</Label>
              <select
                className="w-full rounded-2xl border border-[color:var(--border)] bg-[var(--surface)] px-4 py-3 text-sm"
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
          <Card className="bg-[var(--surface)]">
            <CardHeader>
              <CardTitle>Filters and States</CardTitle>
              <CardDescription>Filter by type, source, state, and score before you pin, archive, or ignore memories.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-5">
              <div className="space-y-2">
                <Label>Type</Label>
                <select
                  className="w-full rounded-2xl border border-[color:var(--border)] bg-[var(--surface)] px-4 py-3 text-sm"
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
                  className="w-full rounded-2xl border border-[color:var(--border)] bg-[var(--surface)] px-4 py-3 text-sm"
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
                  className="w-full rounded-2xl border border-[color:var(--border)] bg-[var(--surface)] px-4 py-3 text-sm"
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

          <Card className="bg-[var(--surface)]">
            <CardHeader>
              <CardTitle>Long-Term Profile</CardTitle>
              <CardDescription>Stable instructions and preferences are merged into a lightweight profile that can steer later replies.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {dashboard.profileSummary ? (
                <div className="rounded-[1.25rem] border border-[color:var(--border)] bg-[#fffdf9] p-4 text-sm leading-6">
                  <p className="whitespace-pre-wrap">{dashboard.profileSummary}</p>
                </div>
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">No long-term profile yet.</p>
              )}

              {dashboard.profileBuckets.length > 0 ? (
                <div className="grid gap-3 md:grid-cols-3">
                  {dashboard.profileBuckets.map((bucket) => (
                    <div key={bucket.bucket} className="rounded-[1rem] border border-[color:var(--border)] bg-[#faf8f4] p-4">
                      <p className="text-sm font-medium capitalize">{bucket.bucket}</p>
                      <div className="mt-3 space-y-2 text-sm text-[var(--muted-foreground)]">
                        {bucket.entries.length > 0 ? (
                          bucket.entries.map((item, index) => <p key={index}>{item}</p>)
                        ) : (
                          <p>No entries.</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card className="bg-[var(--surface)]">
            <CardHeader>
              <CardTitle>Structured Snapshots</CardTitle>
              <CardDescription>User profile and relationship state are rebuilt from active facts so the companion has something more stable than freeform notes.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 lg:grid-cols-2">
              <div className="space-y-3 rounded-[1.25rem] border border-[color:var(--border)] bg-[var(--surface)] p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium">User Profile</p>
                  {dashboard.userProfile.profileVersion ? <Badge>v{dashboard.userProfile.profileVersion}</Badge> : null}
                  {dashboard.userProfile.sourceFactCount ? <Badge>{dashboard.userProfile.sourceFactCount} facts</Badge> : null}
                </div>
                {!dashboard.userProfile.isEmpty ? (
                  <pre className="overflow-x-auto rounded-[1rem] bg-[#faf8f4] p-3 text-xs leading-6">
                    {dashboard.userProfile.json}
                  </pre>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">No structured profile yet.</p>
                )}
              </div>

              <div className="space-y-3 rounded-[1.25rem] border border-[color:var(--border)] bg-[var(--surface)] p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium">Relationship State</p>
                  {dashboard.relationshipState.relationshipStage ? (
                    <Badge>{dashboard.relationshipState.relationshipStage}</Badge>
                  ) : null}
                  {dashboard.relationshipState.preferredTone ? (
                    <Badge>{dashboard.relationshipState.preferredTone}</Badge>
                  ) : null}
                </div>
                {!dashboard.relationshipState.isEmpty ? (
                  <pre className="overflow-x-auto rounded-[1rem] bg-[#faf8f4] p-3 text-xs leading-6">
                    {dashboard.relationshipState.json}
                  </pre>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">No relationship snapshot yet.</p>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-[var(--surface)]">
            <CardHeader>
              <CardTitle>Recent Writes</CardTitle>
              <CardDescription>Inspect how preference, instruction, and episodic memories are labeled, reinforced, and stored.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {recentMemories.length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">No memories yet.</p>
              ) : (
                recentMemories.slice(0, 6).map((memory) => (
                  <div key={memory.id} className="rounded-[1.25rem] border border-[color:var(--border)] bg-[var(--surface)] p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge>{memory.type}</Badge>
                      <Badge>{memory.label}</Badge>
                      <Badge>{memory.writeStrategy}</Badge>
                      <Badge>{memory.state}</Badge>
                      <Badge>importance {memory.importance}</Badge>
                      <Badge>confidence {memory.confidence}</Badge>
                      <Badge>reinforce {memory.reinforcementCount}</Badge>
                      <Badge>{memory.currentVersion ? "current" : "older"}</Badge>
                    </div>
                    <p className="mt-3 text-sm leading-6">{memory.content}</p>
                    <p className="mt-2 text-xs text-[var(--muted-foreground)]">
                      source: {memory.source} | fact key: {memory.factKey} | dedupe key: {memory.dedupeKey || "n/a"}
                    </p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="bg-[var(--surface)]">
            <CardHeader>
              <CardTitle>Episode Ledger</CardTitle>
              <CardDescription>Every memory write appends a source episode first, so facts and revisions can point back to a concrete event trail.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {recentEpisodes.length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">No episodes yet.</p>
              ) : (
                recentEpisodes.slice(0, 6).map((episode) => (
                  <div key={episode.id} className="rounded-[1.25rem] border border-[color:var(--border)] bg-[var(--surface)] p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge>{episode.sourceType}</Badge>
                      {episode.speakerRole ? <Badge>{episode.speakerRole}</Badge> : null}
                      <Badge>importance {episode.importance}</Badge>
                    </div>
                    <p className="mt-3 text-sm leading-6">{episode.text}</p>
                    {episode.occurredAtLabel ? (
                      <p className="mt-2 text-xs text-[var(--muted-foreground)]">
                        occurred: {episode.occurredAtLabel}
                      </p>
                    ) : null}
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="bg-[var(--surface)]">
            <CardHeader>
              <CardTitle>Fact Ledger</CardTitle>
              <CardDescription>Canonical facts carry the stable state the companion should recall, while old revisions stop steering active behavior.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {recentFacts.length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">No facts yet.</p>
              ) : (
                recentFacts.slice(0, 6).map((fact) => (
                  <div key={fact.id} className="rounded-[1.25rem] border border-[color:var(--border)] bg-[var(--surface)] p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge>{fact.factType}</Badge>
                      <Badge>{fact.status}</Badge>
                      <Badge>{fact.subjectKind}</Badge>
                      <Badge>confidence {fact.confidence}</Badge>
                      <Badge>importance {fact.importance}</Badge>
                      <Badge>stable {fact.stability}</Badge>
                      <Badge>reinforce {fact.reinforcementCount}</Badge>
                    </div>
                    <p className="mt-3 text-sm leading-6">{fact.value}</p>
                    <p className="mt-2 text-xs text-[var(--muted-foreground)]">
                      predicate: {fact.predicateKey} | key: {fact.normalizedKey} | sensitivity: {fact.sensitivity}
                    </p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="bg-[var(--surface)]">
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
                    className="rounded-[1.25rem] border border-[color:var(--border)] bg-[var(--surface)] p-4"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge>{revision.op}</Badge>
                      <Badge>revision {revision.revisionNo}</Badge>
                      <Badge>{revision.authorType}</Badge>
                      {revision.conflictGroupId ? <Badge>{revision.conflictGroupId}</Badge> : null}
                    </div>
                    <p className="mt-3 text-sm leading-6">{revision.value}</p>
                    <p className="mt-2 text-xs text-[var(--muted-foreground)]">
                      fact: {revision.factId} | delta: {revision.confidenceDelta}
                      {revision.retiredAtLabel ? ` | retired: ${revision.retiredAtLabel}` : ""}
                    </p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="bg-[var(--surface)]">
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
                    className="rounded-[1.25rem] border border-[color:var(--border)] bg-[var(--surface)] p-4"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge>{candidate.type}</Badge>
                      <Badge>{candidate.proposedAction}</Badge>
                      <Badge>{candidate.status}</Badge>
                      {candidate.factLinked ? <Badge>fact linked</Badge> : <Badge>gated</Badge>}
                      <Badge>salience {candidate.salience}</Badge>
                      <Badge>confidence {candidate.confidence}</Badge>
                      <Badge>{candidate.sensitivity}</Badge>
                    </div>
                    <p className="mt-3 text-sm leading-6">{candidate.extractedText}</p>
                    <p className="mt-2 text-xs text-[var(--muted-foreground)]">
                      key: {candidate.normalizedKey} | reasons: {candidate.reasonLabel}
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

          <Card className="bg-[var(--surface)]">
            <CardHeader>
              <CardTitle>Conflict Groups</CardTitle>
              <CardDescription>When newer instructions or preferences contradict older ones, the older version is marked and removed from active recall.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {dashboard.conflictGroups.length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">No conflict groups yet.</p>
              ) : (
                dashboard.conflictGroups.map((group) => (
                  <div key={group.id} className="rounded-[1.25rem] border border-[color:var(--border)] bg-[#fffdf9] p-4">
                    <p className="text-sm font-medium">{group.label}</p>
                    <div className="mt-3 space-y-2">
                      {group.items.map((item) => (
                        <div key={item.id} className="rounded-2xl bg-[var(--surface-2)] p-3 text-sm leading-6">
                          <div className="flex flex-wrap gap-2">
                            <Badge>{item.state}</Badge>
                            <Badge>{item.currentVersion ? "current" : "superseded"}</Badge>
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

          <Card className="bg-[var(--surface)]">
            <CardHeader>
              <CardTitle>Potential Duplicates</CardTitle>
              <CardDescription>Simple dedupe view based on the stored `dedupe_key` metadata.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {duplicateGroups.length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">No duplicate groups in the current filtered set.</p>
              ) : (
                duplicateGroups.map((group) => (
                  <div key={group.id} className="rounded-[1.25rem] border border-[color:var(--border)] bg-[#fffdf9] p-4">
                    <p className="text-sm font-medium">{group.label}</p>
                    <div className="mt-3 space-y-2">
                      {group.items.map((memory) => (
                        <div key={memory.id} className="rounded-2xl bg-[#faf8f4] p-3 text-sm leading-6">
                          <div className="flex flex-wrap gap-2">
                            <Badge>{memory.label}</Badge>
                            <Badge>{memory.state}</Badge>
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

          <Card className="bg-[var(--surface)]">
            <CardHeader>
              <CardTitle>Memory Table</CardTitle>
              <CardDescription>Filtered list with quick curator actions.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-hidden rounded-[1.25rem] border border-[color:var(--border)]">
                <Table>
                  <thead className="bg-[var(--surface-2)]">
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
                        <TableCell>{memory.type}</TableCell>
                        <TableCell>{memory.label}</TableCell>
                        <TableCell>{memory.content}</TableCell>
                        <TableCell>{`${memory.importance} / ${memory.confidence}`}</TableCell>
                        <TableCell>{memory.source}</TableCell>
                        <TableCell>{memory.state}</TableCell>
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
