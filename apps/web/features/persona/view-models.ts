import type { UUID } from "@agent/shared";

export type PersonaSpeakerOptionViewModel = {
  speaker: string;
  messageCount: number;
  roles: string[];
  isSelf: boolean;
};

export type PersonaListItemViewModel = {
  id?: UUID;
  name: string;
  tone: string;
  verbosity: string;
  isDefault: boolean;
};

export type PersonaPreviewViewModel = {
  savedPreview: string;
  draftPreview: string;
};
