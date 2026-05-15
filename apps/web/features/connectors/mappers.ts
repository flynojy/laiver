import type {
  ConnectorConversationMappingRecord,
  ConnectorDeliveryRecord,
  ConnectorRecord
} from "@agent/shared";

import type {
  ConnectorCardViewModel,
  ConnectorDeliveryViewModel,
  ConnectorDetailViewModel,
  ConnectorMappingViewModel
} from "./view-models";

export function toJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}

function configValue(config: Record<string, unknown>, key: string, fallback: string) {
  return String(config[key] ?? fallback);
}

export function connectorMode(connector: ConnectorRecord | null, draft?: Record<string, unknown>) {
  return configValue(draft ?? connector?.config ?? {}, "mode", configValue(connector?.config ?? {}, "mode", "mock"));
}

export function connectorDeliveryMode(connector: ConnectorRecord | null, draft?: Record<string, unknown>) {
  return configValue(
    draft ?? connector?.config ?? {},
    "delivery_mode",
    configValue(connector?.config ?? {}, "delivery_mode", "webhook")
  );
}

export function toConnectorCardViewModel(connector: ConnectorRecord): ConnectorCardViewModel {
  return {
    id: connector.connector_id,
    name: connector.name,
    badges: [
      connector.connector_type,
      connector.status,
      connectorMode(connector),
      connectorDeliveryMode(connector)
    ]
  };
}

export function toConnectorDetailViewModel(
  connector: ConnectorRecord,
  draft: Record<string, unknown>
): ConnectorDetailViewModel {
  const mode = connectorMode(connector, draft);
  const deliveryMode = connectorDeliveryMode(connector, draft);
  return {
    id: connector.connector_id,
    mode,
    deliveryMode,
    badges: [connector.connector_type, connector.status, mode, deliveryMode],
    webhookPath: `/api/v1/connectors/feishu/webhook/${connector.connector_id}`
  };
}

export function toConnectorMappingViewModel(
  mapping: ConnectorConversationMappingRecord
): ConnectorMappingViewModel {
  return {
    id: mapping.mapping_id,
    badges: [mapping.memory_scope, mapping.default_persona_id ? "persona-linked" : "persona-open"],
    conversationKey: mapping.conversation_key,
    externalLabel: `external chat: ${mapping.external_chat_id ?? "n/a"} | external user: ${
      mapping.external_user_id ?? "n/a"
    }`,
    internalConversationLabel: `internal conversation: ${mapping.internal_conversation_id ?? "pending"}`
  };
}

export function toConnectorDeliveryViewModel(delivery: ConnectorDeliveryRecord): ConnectorDeliveryViewModel {
  return {
    id: delivery.delivery_id,
    badges: [
      delivery.connector_type,
      delivery.delivery_status,
      delivery.mode,
      delivery.trace?.skills_used?.length ? delivery.trace.skills_used.join(", ") : ""
    ].filter((item): item is string => item.length > 0),
    traceLabel: delivery.trace?.connector_trace_id ?? delivery.trace_id,
    mappedConversationLabel: `mapped conversation: ${
      delivery.trace?.mapped_conversation_id ?? delivery.internal_conversation_id ?? "pending"
    }`,
    panels: [
      { title: "Trace", json: toJson(delivery.trace ?? {}) },
      { title: "Mapping", json: toJson(delivery.mapping ?? {}) },
      { title: "Normalized Input", json: toJson(delivery.normalized_input) },
      { title: "Outbound Payload", json: toJson(delivery.outbound_response) }
    ],
    error: delivery.error
  };
}
