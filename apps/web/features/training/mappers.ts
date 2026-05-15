import type { FineTuneJobDetail, FineTuneJobRecord } from "@agent/shared";

import type { ImportDetail } from "./client";

import type {
  TrainingJobCardViewModel,
  TrainingJobDetailViewModel,
  TrainingSpeakerOptionViewModel,
  TrainingWorkflowStageViewModel
} from "./view-models";

export function speakerOptionsForImport(importRow: ImportDetail | null): TrainingSpeakerOptionViewModel[] {
  if (!importRow) {
    return [];
  }
  const summary = importRow.import_job.normalized_summary ?? {};
  const speakerStats = summary.speaker_stats;
  if (speakerStats && typeof speakerStats === "object") {
    return Object.entries(speakerStats)
      .map(([speaker, value]) => ({
        speaker,
        count:
          value && typeof value === "object" && "message_count" in value
            ? Number((value as { message_count?: number }).message_count ?? 0)
            : 0
      }))
      .sort((left, right) => right.count - left.count);
  }

  const counts = new Map<string, number>();
  for (const message of importRow.normalized_messages) {
    counts.set(message.speaker, (counts.get(message.speaker) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([speaker, count]) => ({ speaker, count }))
    .sort((left, right) => right.count - left.count);
}

export function toTrainingJobCard(job: FineTuneJobRecord): TrainingJobCardViewModel {
  return {
    id: job.id,
    name: job.name,
    status: job.status,
    backend: job.backend,
    baseModel: job.base_model,
    trainExamples: job.train_examples,
    validationExamples: job.validation_examples,
    testExamples: job.test_examples
  };
}

export function toTrainingJobDetail(detail: FineTuneJobDetail | null): TrainingJobDetailViewModel | null {
  if (!detail) {
    return null;
  }
  return {
    id: detail.job.id,
    name: detail.job.name,
    status: detail.job.status,
    backend: detail.job.backend,
    sourceSpeaker: detail.job.source_speaker,
    datasetPath: detail.job.dataset_path,
    configPath: detail.job.config_path,
    outputDir: detail.job.output_dir,
    trainExamples: detail.job.train_examples,
    validationExamples: detail.job.validation_examples,
    testExamples: detail.job.test_examples,
    artifactPath: detail.job.artifact_path,
    errorMessage: detail.job.error_message,
    launcherCommand: detail.job.launcher_command,
    registeredProvider: detail.registered_provider
      ? {
          id: detail.registered_provider.id,
          name: detail.registered_provider.name,
          providerType: detail.registered_provider.provider_type,
          baseUrl: detail.registered_provider.base_url,
          isDefault: detail.registered_provider.is_default,
          isEnabled: detail.registered_provider.is_enabled ?? true
        }
      : null,
    datasetSamples: detail.dataset_preview.map((sample, index) => ({
      id: `${detail.job.id}-${index}`,
      label: `Sample ${index + 1}`,
      messages: sample.messages.map((message) => ({
        role: message.role,
        content: message.content
      }))
    }))
  };
}

export function buildWorkflowStages(
  selectedImport: ImportDetail | null,
  selectedSpeaker: string,
  detail: TrainingJobDetailViewModel | null
): TrainingWorkflowStageViewModel[] {
  return [
    {
      title: "Dataset",
      detail: selectedImport ? selectedImport.import_job.file_name : "Pick an import first",
      done: Boolean(selectedImport && selectedSpeaker)
    },
    {
      title: "Launch",
      detail: detail ? detail.status : "Create a job and start the runner",
      done: Boolean(detail && ["running", "completed", "failed", "cancelled"].includes(detail.status))
    },
    {
      title: "Register",
      detail: detail?.registeredProvider ? detail.registeredProvider.name : "Register the finished adapter",
      done: Boolean(detail?.registeredProvider)
    },
    {
      title: "Default",
      detail: detail?.registeredProvider?.isDefault ? "Registered provider is default" : "Switch the active default model",
      done: Boolean(detail?.registeredProvider?.isDefault)
    }
  ];
}
