import type { UUID } from "@agent/shared";

export type TrainingSpeakerOptionViewModel = {
  speaker: string;
  count: number;
};

export type TrainingWorkflowStageViewModel = {
  title: string;
  detail: string;
  done: boolean;
};

export type TrainingJobCardViewModel = {
  id: UUID;
  name: string;
  status: string;
  backend: string;
  baseModel: string;
  trainExamples: number;
  validationExamples: number;
  testExamples: number;
};

export type TrainingDatasetSampleViewModel = {
  id: string;
  label: string;
  messages: Array<{
    role: string;
    content: string;
  }>;
};

export type TrainingJobDetailViewModel = {
  id: UUID;
  name: string;
  status: string;
  backend: string;
  sourceSpeaker: string;
  datasetPath: string;
  configPath: string;
  outputDir: string;
  trainExamples: number;
  validationExamples: number;
  testExamples: number;
  artifactPath?: string | null;
  errorMessage?: string | null;
  launcherCommand: string;
  registeredProvider?: {
    id?: UUID;
    name: string;
    providerType: string;
    baseUrl: string;
    isDefault: boolean;
    isEnabled: boolean;
  } | null;
  datasetSamples: TrainingDatasetSampleViewModel[];
};
