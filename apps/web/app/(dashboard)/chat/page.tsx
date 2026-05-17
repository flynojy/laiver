"use client";

import { useEffect, useState } from "react";
import { Loader2, SendHorizontal } from "lucide-react";

import type {
  ConversationControls,
  ModelProviderConfig,
  PersonaCard,
  UUID
} from "@agent/shared";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { defaultConversationControls, normalizeConversationControls, toChatRunViewModel } from "@/features/chat/mappers";
import type { ChatMemoryItemViewModel, ChatRunViewModel } from "@/features/chat/view-models";
import {
  bootstrapModelProvider,
  bootstrapUser,
  getConversation,
  listConversations,
  listModelProviders,
  listPersonas,
  respondAgent,
  seedSkills,
  updateConversation,
  type ConversationDetail,
  type ConversationSummary
} from "@/features/chat/client";

function MemoryList({ memories }: { memories: ChatMemoryItemViewModel[] }) {
  if (memories.length === 0) {
    return <p className="text-sm text-[var(--muted-foreground)]">No items.</p>;
  }

  return (
    <div className="space-y-3">
      {memories.map((memory) => (
        <div key={memory.id} className="rounded-2xl border border-[color:var(--border)] bg-[var(--surface)] p-3">
          <div className="flex flex-wrap gap-2">
            <Badge>{memory.type}</Badge>
            <Badge>{memory.label}</Badge>
            <Badge>{memory.state}</Badge>
            <Badge>importance {memory.importance}</Badge>
            <Badge>confidence {memory.confidence}</Badge>
          </div>
          <p className="mt-2 text-sm leading-6">{memory.content}</p>
        </div>
      ))}
    </div>
  );
}

export default function ChatPage() {
  const [userId, setUserId] = useState("");
  const [personas, setPersonas] = useState<PersonaCard[]>([]);
  const [selectedPersonaId, setSelectedPersonaId] = useState("");
  const [providers, setProviders] = useState<ModelProviderConfig[]>([]);
  const [selectedProviderId, setSelectedProviderId] = useState<UUID | "">("");
  const [controls, setControls] = useState<ConversationControls>(defaultConversationControls());
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversation, setActiveConversation] = useState<ConversationDetail | null>(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [lastRun, setLastRun] = useState<ChatRunViewModel | null>(null);

  async function loadConversation(conversationId: string, preferredPersonaId?: string | null) {
    const detail = await getConversation(conversationId);
    setActiveConversation(detail);
    if (preferredPersonaId) {
      setSelectedPersonaId(preferredPersonaId);
    } else if (detail.conversation.persona_id) {
      setSelectedPersonaId(detail.conversation.persona_id);
    }
    setControls(normalizeConversationControls(detail.conversation.metadata?.controls));
  }

  async function refreshConversations(nextConversationId?: string, preferredPersonaId?: string | null) {
    const rows = await listConversations();
    setConversations(rows);
    const targetId = nextConversationId ?? activeConversation?.conversation.id ?? rows[0]?.id;
    if (targetId) {
      await loadConversation(targetId, preferredPersonaId);
    }
  }

  useEffect(() => {
    async function bootstrap() {
      const user = await bootstrapUser();
      setUserId(user.user.id);

      await bootstrapModelProvider();
      const [personaRows, providerRows] = await Promise.all([listPersonas(), listModelProviders(), seedSkills()]);

      setPersonas(personaRows);
      setSelectedPersonaId(personaRows.find((item) => item.is_default)?.id ?? personaRows[0]?.id ?? "");
      setProviders(providerRows);
      setSelectedProviderId(providerRows.find((item) => item.is_default)?.id ?? providerRows[0]?.id ?? "");
      await refreshConversations();
    }

    bootstrap().catch((reason) => {
      setError(reason instanceof Error ? reason.message : "Chat page bootstrap failed.");
    });
  }, []);

  const currentPersona =
    lastRun?.persona ??
    personas.find((persona) => persona.id === (selectedPersonaId || activeConversation?.conversation.persona_id)) ??
    null;
  const currentProvider =
    providers.find((provider) => provider.id === (selectedProviderId || undefined)) ??
    providers.find((provider) => provider.is_default) ??
    providers[0] ??
    null;

  async function persistConversationState(nextPersonaId: string, nextControls: ConversationControls) {
    if (!activeConversation?.conversation.id) return;
    await updateConversation(activeConversation.conversation.id, {
      persona_id: nextPersonaId || null,
      metadata: {
        ...activeConversation.conversation.metadata,
        controls: nextControls
      }
    });
    await loadConversation(activeConversation.conversation.id, nextPersonaId || undefined);
  }

  async function sendMessage() {
    if (!draft.trim() || !userId) return;
    setSending(true);
    setError("");
    setStatus("");
    try {
      const result = await respondAgent({
        user_id: userId,
        conversation_id: activeConversation?.conversation.id,
        persona_id: selectedPersonaId || undefined,
        provider_id: selectedProviderId || undefined,
        message: draft,
        controls
      });
      const runView = toChatRunViewModel(result);
      setLastRun(runView);
      setDraft("");
      await refreshConversations(runView.conversationId, runView.personaId ?? selectedPersonaId);
      setStatus("Agent responded. Use the debug panel to inspect controls, explanation, memory writes, and skill grounding.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Message send failed.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Conversation Quality"
        title="Chat Flow Validation"
        description="Tune persona, skills, and memory write controls at the conversation level, then inspect exactly which memories, persona fields, and skill outputs shaped the answer."
        badge="Controls + Explanation"
      />

      {error ? (
        <div className="rounded-[4px] border border-[var(--danger)] bg-[color:var(--danger)]/10 px-4 py-3 font-mono text-xs uppercase tracking-[0.12em] text-[var(--danger)]">
          ▶ ALERT — {error}
        </div>
      ) : null}
      {status ? (
        <div className="rounded-[4px] border border-[var(--success)] bg-[color:var(--success)]/10 px-4 py-3 font-mono text-xs uppercase tracking-[0.12em] text-[var(--success)]">
          ● {status}
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)_380px]">
        <Card>
          <CardHeader>
            <CardTitle>Conversation Controls</CardTitle>
            <CardDescription>Set persona, provider, and runtime switches before sending the next turn.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Current Persona</label>
              <select
                className="w-full rounded-[4px] border border-[color:var(--border-strong)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--foreground)]"
                value={selectedPersonaId}
                onChange={async (event) => {
                  const nextPersonaId = event.target.value;
                  setSelectedPersonaId(nextPersonaId);
                  if (activeConversation?.conversation.id) {
                    await persistConversationState(nextPersonaId, controls);
                    setStatus("Conversation persona updated.");
                  }
                }}
              >
                <option value="">No Persona</option>
                {personas.map((persona) => (
                  <option key={persona.id} value={persona.id}>
                    {persona.name}
                  </option>
                ))}
                </select>
              </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Model Provider</label>
              <select
                className="w-full rounded-2xl border border-[color:var(--border)] bg-white px-4 py-3 text-sm"
                value={selectedProviderId}
                onChange={(event) => setSelectedProviderId(event.target.value as UUID | "")}
              >
                <option value="">Default provider</option>
                {providers.map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {provider.name} ({provider.provider_type})
                  </option>
                ))}
              </select>
              <p className="text-xs text-[var(--muted-foreground)]">
                Current default: {currentProvider ? `${currentProvider.name} (${currentProvider.provider_type})` : "none"}
              </p>
            </div>

            <div className="space-y-3 rounded-[1.25rem] border border-[color:var(--border)] bg-[var(--surface-2)] p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">Skills</p>
                  <p className="text-xs text-[var(--muted-foreground)]">Planner + tool execution for the next turns.</p>
                </div>
                <Button
                  variant={controls.skills_enabled ? "default" : "secondary"}
                  onClick={async () => {
                    const nextControls = { ...controls, skills_enabled: !controls.skills_enabled };
                    setControls(nextControls);
                    if (activeConversation?.conversation.id) {
                      await persistConversationState(selectedPersonaId, nextControls);
                    }
                  }}
                >
                  {controls.skills_enabled ? "On" : "Off"}
                </Button>
              </div>

              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">Memory Write</p>
                  <p className="text-xs text-[var(--muted-foreground)]">Store new memories after this turn.</p>
                </div>
                <Button
                  variant={controls.memory_write_enabled ? "default" : "secondary"}
                  onClick={async () => {
                    const nextControls = { ...controls, memory_write_enabled: !controls.memory_write_enabled };
                    setControls(nextControls);
                    if (activeConversation?.conversation.id) {
                      await persistConversationState(selectedPersonaId, nextControls);
                    }
                  }}
                >
                  {controls.memory_write_enabled ? "On" : "Off"}
                </Button>
              </div>
            </div>

            <Button
              variant="secondary"
              className="w-full"
              onClick={() => {
                setActiveConversation(null);
                setLastRun(null);
                setControls(defaultConversationControls());
                setStatus("Switched to new conversation mode.");
              }}
            >
              Start New Conversation
            </Button>

            <div className="space-y-3">
              {conversations.length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">No conversations yet.</p>
              ) : (
                conversations.map((conversation) => (
                  <button
                    key={conversation.id}
                    className="w-full rounded-[6px] border border-[color:var(--border)] bg-[var(--surface-2)] px-4 py-3 text-left transition hover:border-[color:var(--border-strong)]"
                    onClick={() => {
                      loadConversation(conversation.id, conversation.persona_id ?? undefined).catch(() => undefined);
                      setLastRun(null);
                    }}
                  >
                    <p className="font-medium">{conversation.title}</p>
                    <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                      {new Date(conversation.updated_at).toLocaleString()}
                    </p>
                  </button>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{activeConversation?.conversation.title ?? "New Conversation"}</CardTitle>
            <CardDescription>
              Try toggling skills or memory write, or switch persona, then send the same prompt again to compare the result.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {activeConversation?.conversation.summary ? (
              <div className="rounded-[1.25rem] border border-[color:var(--border)] bg-[var(--surface)] p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--muted-foreground)]">
                  Long-Horizon Summary
                </p>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6">{activeConversation.conversation.summary}</p>
              </div>
            ) : null}
            <div className="max-h-[560px] space-y-3 overflow-y-auto rounded-[1.5rem] border border-[color:var(--border)] bg-[var(--surface-2)] p-4">
              {activeConversation?.messages.length ? (
                activeConversation.messages.map((message) => (
                  <div
                    key={message.id}
                    className={`rounded-[8px] border px-4 py-3 text-sm leading-6 ${
                      message.role === "user"
                        ? "ml-auto max-w-[75%] border-[var(--accent)] bg-[var(--accent)] text-[var(--accent-foreground)]"
                        : "max-w-[82%] border-[color:var(--border)] bg-[var(--surface)] text-[var(--foreground)]"
                    }`}
                  >
                    <p className={`mb-1 font-mono text-[9px] uppercase tracking-[0.18em] ${message.role === "user" ? "text-[var(--accent-foreground)]/60" : "text-[var(--foreground-muted)]"}`}>
                      {message.role === "user" ? "PILOT" : "MAGI // 02"}
                    </p>
                    {message.content}
                  </div>
                ))
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">
                  Send the first message to create a new conversation.
                </p>
              )}
            </div>

            <div className="space-y-3 rounded-[1.5rem] border border-[color:var(--border)] bg-[var(--surface)] p-4">
              <div className="flex flex-wrap gap-2">
                <Badge>{selectedPersonaId ? "persona selected" : "no persona"}</Badge>
                <Badge>{controls.skills_enabled ? "skills on" : "skills off"}</Badge>
                <Badge>{controls.memory_write_enabled ? "memory write on" : "memory write off"}</Badge>
              </div>
              <Textarea
                placeholder="Type a message for conversation quality testing..."
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                className="min-h-[140px] border-0 bg-transparent p-0 focus:border-0"
              />
              <div className="flex justify-end">
                <Button onClick={sendMessage} disabled={sending || !draft.trim()}>
                  {sending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <SendHorizontal className="mr-2 h-4 w-4" />}
                  Send Message
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Debug Panel</CardTitle>
            <CardDescription>This panel is rendered from the Chat feature view model, not raw backend debug fields.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <label className="text-sm font-medium">Current Persona</label>
              {currentPersona ? (
                <div className="rounded-2xl bg-[var(--surface-2)] p-4">
                  <div className="flex flex-wrap gap-2">
                    <Badge>{currentPersona.name}</Badge>
                    <Badge>{currentPersona.tone}</Badge>
                    <Badge>{currentPersona.verbosity}</Badge>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-[var(--muted-foreground)]">
                    {currentPersona.description || "No description"}
                  </p>
                </div>
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">No Persona selected.</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Runtime Controls</label>
              {lastRun ? (
                <div className="flex flex-wrap gap-2">
                  <Badge>{lastRun.runtime.skillsEnabled ? "skills enabled" : "skills disabled"}</Badge>
                  <Badge>{lastRun.runtime.memoryWriteEnabled ? "memory write enabled" : "memory write disabled"}</Badge>
                  <Badge>{lastRun.runtime.memoryWritten ? "memory written" : "no memory write"}</Badge>
                  <Badge>{lastRun.runtime.personaName}</Badge>
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  <Badge>{controls.skills_enabled ? "skills enabled" : "skills disabled"}</Badge>
                  <Badge>{controls.memory_write_enabled ? "memory write enabled" : "memory write disabled"}</Badge>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Provider + Model</label>
              {lastRun ? (
                <div className="flex flex-wrap gap-2">
                  <Badge>{lastRun.provider.providerName}</Badge>
                  <Badge>{lastRun.provider.modelName}</Badge>
                  <Badge>{lastRun.provider.modelMode}</Badge>
                  {lastRun.provider.modelThinkLabel ? <Badge>{lastRun.provider.modelThinkLabel}</Badge> : null}
                  {lastRun.provider.modelThinkGate ? <Badge>{lastRun.provider.modelThinkGate}</Badge> : null}
                  <Badge>route {lastRun.provider.memoryRoute}</Badge>
                  <Badge>{lastRun.provider.fallbackStatus}</Badge>
                  <Badge>{lastRun.provider.traceId}</Badge>
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {currentProvider ? <Badge>{currentProvider.provider_type}</Badge> : <Badge>no provider</Badge>}
                  {currentProvider ? <Badge>{currentProvider.name}</Badge> : null}
                  <Badge>{selectedProviderId ? "explicit" : "default route"}</Badge>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Compression Status</label>
              {lastRun ? (
                <>
                  <div className="flex flex-wrap gap-2">
                    <Badge>{lastRun.compression.active ? "compression active" : "full short history"}</Badge>
                    <Badge>{lastRun.compression.summarizedMessageCount} summarized</Badge>
                    <Badge>{lastRun.compression.recentMessageCount} recent kept</Badge>
                  </div>
                  {lastRun.compression.summary ? (
                    <pre className="overflow-x-auto rounded-2xl bg-[#faf8f4] p-3 text-xs leading-6">
                      {lastRun.compression.summary}
                    </pre>
                  ) : (
                    <p className="text-sm text-[var(--muted-foreground)]">No summary injected for the last run.</p>
                  )}
                </>
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">No run yet.</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Skills Used</label>
              {lastRun ? (
                lastRun.skillsUsed.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {lastRun.skillsUsed.map((skill) => (
                      <Badge key={skill}>{skill}</Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">No skills used in the last run.</p>
                )
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">No run yet.</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Memories Used In Answer</label>
              {lastRun ? <MemoryList memories={lastRun.explanation.memoriesUsed} /> : <p className="text-sm text-[var(--muted-foreground)]">No run yet.</p>}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Persona Fields Used</label>
              {lastRun ? (
                lastRun.explanation.personaFieldsUsed.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {lastRun.explanation.personaFieldsUsed.map((field) => (
                      <Badge key={field}>{field}</Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">No persona fields were applied.</p>
                )
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">No run yet.</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Skill Outputs Referenced</label>
              {lastRun ? (
                lastRun.explanation.skillOutputsUsed.length > 0 ? (
                  <div className="space-y-2">
                    {lastRun.explanation.skillOutputsUsed.map((item) => (
                      <div key={item} className="rounded-2xl bg-[#faf8f4] p-3 text-sm leading-6">
                        {item}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">No grounded skill output was referenced.</p>
                )
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">No run yet.</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Skill Invocation Details</label>
              {lastRun ? (
                lastRun.skillInvocations.length > 0 ? (
                  <div className="space-y-3">
                    {lastRun.skillInvocations.map((invocation) => (
                      <div key={invocation.id} className="rounded-2xl border border-[color:var(--border)] bg-[#fffdf9] p-3">
                        <div className="flex flex-wrap gap-2">
                          <Badge>{invocation.skillSlug}</Badge>
                          <Badge>{invocation.toolName}</Badge>
                          <Badge>{invocation.status}</Badge>
                        </div>
                        <pre className="mt-3 overflow-x-auto rounded-2xl bg-[#faf8f4] p-3 text-xs leading-6">
                          {invocation.outputJson}
                        </pre>
                        {invocation.error ? (
                          <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--danger)]">
                            ▶ {invocation.error}
                          </p>
                        ) : null}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">No invocation details for the last run.</p>
                )
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">No run yet.</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Memory Hits</label>
              {lastRun ? <MemoryList memories={lastRun.memoryHits} /> : <p className="text-sm text-[var(--muted-foreground)]">No run yet.</p>}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Memory Writes</label>
              {lastRun ? (
                <>
                  <div className="flex flex-wrap gap-2">
                    <Badge>{lastRun.runtime.memoryWritten ? "YES" : "NO"}</Badge>
                    <Badge>{lastRun.runtime.memoryWriteCount} writes</Badge>
                  </div>
                  <MemoryList memories={lastRun.memoryWrites} />
                </>
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">No run yet.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
