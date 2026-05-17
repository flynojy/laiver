import type { UUID } from "@agent/shared";

export type ConnectorCardViewModel = {
  id: UUID;
  name: string;
  badges: string[];
};

export type ConnectorDetailViewModel = {
  id: UUID;
  badges: string[];
  mode: string;
  deliveryMode: string;
  webhookPath: string;
};

export type ConnectorMappingViewModel = {
  id: UUID;
  badges: string[];
  conversationKey: string;
  externalLabel: string;
  internalConversationLabel: string;
};

export type ConnectorDeliveryViewModel = {
  id: UUID;
  badges: string[];
  traceLabel: string;
  mappedConversationLabel: string;
  panels: Array<{
    title: string;
    json: string;
  }>;
  error?: string | null;
};
