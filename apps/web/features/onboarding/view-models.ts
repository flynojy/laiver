import type { UUID } from "@agent/shared";

export type OnboardingStep = "import" | "persona" | "training" | "runtime";

export type OnboardingStepCardViewModel = {
  key: OnboardingStep;
  title: string;
  detail: string;
  done: boolean;
  active: boolean;
};

export type OnboardingSpeakerOptionViewModel = {
  speaker: string;
  count: number;
  isSelf: boolean;
  label: string;
};

export type OnboardingImportPreviewViewModel = {
  sourceTypeLabel: string;
  totalMessages: number;
  participantCount: number;
  badges: string[];
  rows: Array<{
    sequenceIndex: number;
    speaker: string;
    role: string;
    content: string;
  }>;
};

export type OnboardingImportOptionViewModel = {
  id: UUID;
  fileName: string;
};

export type OnboardingPersonaSummaryViewModel = {
  name: string;
  tone: string;
  verbosity: string;
  isDefault: boolean;
  description: string;
  badges: string[];
};

export type OnboardingTrainingJobViewModel = {
  name: string;
  status: string;
  backend: string;
  sourceSpeaker: string;
  trainExamples: number;
  validationExamples: number;
  testExamples: number;
};

export type OnboardingRuntimeStatusViewModel = {
  providerCount: number;
  skillCount: number;
  summary: string;
};
