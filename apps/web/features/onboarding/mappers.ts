import type { FineTuneJobDetail, ImportPreviewSummary, PersonaCard } from "@agent/shared";

import type { ImportDetail, ImportPreview } from "./client";

import type {
  OnboardingImportPreviewViewModel,
  OnboardingImportOptionViewModel,
  OnboardingPersonaSummaryViewModel,
  OnboardingRuntimeStatusViewModel,
  OnboardingSpeakerOptionViewModel,
  OnboardingStep,
  OnboardingStepCardViewModel,
  OnboardingTrainingJobViewModel
} from "./view-models";

function speakerStatsForImport(importRow: ImportDetail | null) {
  if (!importRow) return [];
  const speakerStats = importRow.import_job.normalized_summary?.speaker_stats;
  if (speakerStats && typeof speakerStats === "object" && !Array.isArray(speakerStats)) {
    return Object.entries(speakerStats)
      .map(([speaker, value]) => {
        const payload = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
        const count = Number(payload.message_count ?? 0);
        const isSelf = payload.is_self === true;
        return {
          speaker,
          count,
          isSelf,
          label: `${speaker} (${count})${isSelf ? " self" : ""}`
        };
      })
      .sort((left, right) => right.count - left.count);
  }

  const counts = new Map<string, OnboardingSpeakerOptionViewModel>();
  for (const message of importRow.normalized_messages) {
    const current = counts.get(message.speaker) ?? {
      speaker: message.speaker,
      count: 0,
      isSelf: message.metadata?.is_self === true,
      label: ""
    };
    current.count += 1;
    current.label = `${current.speaker} (${current.count})${current.isSelf ? " self" : ""}`;
    counts.set(message.speaker, current);
  }
  return [...counts.values()].sort((left, right) => right.count - left.count);
}

function sourceMetadataBadges(metadata?: ImportPreviewSummary["source_metadata"] | Record<string, unknown>) {
  const value = metadata?.message_types;
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
    : [];
}

export function toOnboardingImportPreviewViewModel(preview: ImportPreview): OnboardingImportPreviewViewModel {
  return {
    sourceTypeLabel: preview.source_type.toUpperCase(),
    totalMessages: preview.total_messages,
    participantCount: preview.detected_participants.length,
    badges: sourceMetadataBadges(preview.source_metadata),
    rows: preview.normalized_messages.slice(0, 8).map((row) => ({
      sequenceIndex: row.sequence_index,
      speaker: row.speaker,
      role: row.role,
      content: row.content
    }))
  };
}

export function toOnboardingImportOptionViewModel(item: ImportDetail): OnboardingImportOptionViewModel {
  return {
    id: item.import_job.id,
    fileName: item.import_job.file_name
  };
}

export function toOnboardingSpeakerOptions(importRow: ImportDetail | null): OnboardingSpeakerOptionViewModel[] {
  return speakerStatsForImport(importRow);
}

export function defaultSpeakerForImport(
  importRow: ImportDetail | null,
  speakers: OnboardingSpeakerOptionViewModel[]
) {
  const owner = importRow?.import_job.normalized_summary?.conversation_owner;
  if (typeof owner === "string" && owner.trim()) {
    return owner;
  }
  return speakers[0]?.speaker ?? "";
}

export function defaultTrainingJobName(importRow: ImportDetail | null) {
  return importRow ? `${importRow.import_job.file_name} Fine-Tune` : null;
}

export function toOnboardingPersonaSummaryViewModel(persona: PersonaCard | null): OnboardingPersonaSummaryViewModel | null {
  if (!persona) return null;
  return {
    name: persona.name,
    tone: persona.tone,
    verbosity: persona.verbosity,
    isDefault: persona.is_default,
    description: persona.description || "Persona ready.",
    badges: [persona.tone, persona.verbosity, persona.is_default ? "default" : ""].filter(Boolean)
  };
}

export function toOnboardingTrainingJobViewModel(
  detail: FineTuneJobDetail | null
): OnboardingTrainingJobViewModel | null {
  if (!detail) return null;
  return {
    name: detail.job.name,
    status: detail.job.status,
    backend: detail.job.backend,
    sourceSpeaker: detail.job.source_speaker,
    trainExamples: detail.job.train_examples,
    validationExamples: detail.job.validation_examples,
    testExamples: detail.job.test_examples
  };
}

export function toOnboardingRuntimeStatusViewModel(
  providerCount: number,
  skillCount: number
): OnboardingRuntimeStatusViewModel {
  return {
    providerCount,
    skillCount,
    summary: `${providerCount} providers / ${skillCount} seeded skills`
  };
}

export function buildOnboardingStepCards(args: {
  currentStep: OnboardingStep;
  committedImport: ImportDetail | null;
  persona: PersonaCard | null;
  trainingJob: FineTuneJobDetail | null;
  runtime: OnboardingRuntimeStatusViewModel;
}): OnboardingStepCardViewModel[] {
  const order: OnboardingStep[] = ["import", "persona", "training", "runtime"];
  const completed = (target: OnboardingStep) => order.indexOf(args.currentStep) > order.indexOf(target);
  return [
    {
      key: "import",
      title: "Import",
      detail: args.committedImport?.import_job.file_name ?? "No import selected",
      done: completed("import"),
      active: args.currentStep === "import"
    },
    {
      key: "persona",
      title: "Persona",
      detail: args.persona?.name ?? "No Persona yet",
      done: completed("persona"),
      active: args.currentStep === "persona"
    },
    {
      key: "training",
      title: "Training",
      detail: args.trainingJob?.job.name ?? "No job yet",
      done: completed("training"),
      active: args.currentStep === "training"
    },
    {
      key: "runtime",
      title: "Runtime",
      detail: args.runtime.summary,
      done: completed("runtime"),
      active: args.currentStep === "runtime"
    }
  ];
}

export type { OnboardingStep } from "./view-models";
