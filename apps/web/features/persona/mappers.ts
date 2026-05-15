import type { PersonaCard } from "@agent/shared";

import type { ImportDetail } from "./client";

import type {
  PersonaListItemViewModel,
  PersonaPreviewViewModel,
  PersonaSpeakerOptionViewModel
} from "./view-models";

export function toPersonaListItemViewModel(persona: PersonaCard): PersonaListItemViewModel {
  return {
    id: persona.id,
    name: persona.name,
    tone: persona.tone,
    verbosity: persona.verbosity,
    isDefault: persona.is_default
  };
}

export function speakerOptionsForImport(item: ImportDetail | undefined): PersonaSpeakerOptionViewModel[] {
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
            ? candidate.roles.filter((role): role is string => typeof role === "string")
            : [],
          isSelf: candidate.is_self === true
        };
      })
      .filter((item): item is PersonaSpeakerOptionViewModel => item !== null)
      .sort((left, right) => right.messageCount - left.messageCount);
  }

  const fallback = new Map<string, PersonaSpeakerOptionViewModel>();
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

export function defaultSpeakerForImport(item: ImportDetail | undefined) {
  if (!item) return "";
  const owner = item.import_job.normalized_summary?.conversation_owner;
  if (typeof owner === "string" && owner.trim()) {
    return owner;
  }
  return "";
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

export function toPersonaPreviewViewModel(savedPersona: PersonaCard | null, draftPersona: PersonaCard | null, prompt: string): PersonaPreviewViewModel {
  return {
    savedPreview: renderPersonaPreview(savedPersona, prompt),
    draftPreview: renderPersonaPreview(draftPersona, prompt)
  };
}

export function hasPersonaChanged(savedPersona: PersonaCard | null, draftPersona: PersonaCard | null) {
  return personaSignature(savedPersona) !== personaSignature(draftPersona);
}
