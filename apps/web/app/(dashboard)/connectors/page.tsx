"use client";

import { useEffect, useMemo, useState } from "react";

import type {
  ConnectorConversationMappingRecord,
  ConnectorDeliveryRecord,
  ConnectorRecord
} from "@agent/shared";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  bootstrapUser,
  createConnector,
  getFeishuSkeleton,
  listConnectorDeliveries,
  listConnectorMappings,
  listConnectors,
  testConnector,
  updateConnector
} from "@/lib/api";

function JsonPanel({ title, value }: { title: string; value: unknown }) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--muted-foreground)]">
        {title}
      </p>
      <pre className="mt-2 overflow-x-auto rounded-2xl bg-[#faf8f4] p-3 text-xs leading-6">
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}

function MappingList({ mappings }: { mappings: ConnectorConversationMappingRecord[] }) {
  if (mappings.length === 0) {
    return <p className="text-sm text-[var(--muted-foreground)]">No conversation mappings yet.</p>;
  }

  return (
    <div className="space-y-3">
      {mappings.map((item) => (
        <div key={item.mapping_id} className="rounded-[1.25rem] border border-[color:var(--border)] bg-[#fffdf9] p-4">
          <div className="flex flex-wrap gap-2">
            <Badge>{item.memory_scope}</Badge>
            {item.default_persona_id ? <Badge>persona-linked</Badge> : <Badge>persona-open</Badge>}
          </div>
          <p className="mt-2 text-sm font-medium">{item.conversation_key}</p>
          <p className="mt-2 text-xs text-[var(--muted-foreground)]">
            external chat: {item.external_chat_id ?? "n/a"} | external user: {item.external_user_id ?? "n/a"}
          </p>
          <p className="mt-1 text-xs text-[var(--muted-foreground)]">
            internal conversation: {item.internal_conversation_id ?? "pending"}
          </p>
        </div>
      ))}
    </div>
  );
}

function DeliveryList({ deliveries }: { deliveries: ConnectorDeliveryRecord[] }) {
  if (deliveries.length === 0) {
    return <p className="text-sm text-[var(--muted-foreground)]">No delivery records yet.</p>;
  }

  return (
    <div className="space-y-3">
      {deliveries.map((item) => (
        <div key={item.delivery_id} className="rounded-[1.25rem] border border-[color:var(--border)] bg-[#fffdf9] p-4">
          <div className="flex flex-wrap gap-2">
            <Badge>{item.connector_type}</Badge>
            <Badge>{item.delivery_status}</Badge>
            <Badge>{item.mode}</Badge>
            {item.trace?.skills_used?.length ? <Badge>{item.trace.skills_used.join(", ")}</Badge> : null}
          </div>
          <p className="mt-2 text-xs text-[var(--muted-foreground)]">{item.trace?.connector_trace_id ?? item.trace_id}</p>
          <p className="mt-1 text-xs text-[var(--muted-foreground)]">
            mapped conversation: {item.trace?.mapped_conversation_id ?? item.internal_conversation_id ?? "pending"}
          </p>
          <div className="mt-3 grid gap-3 xl:grid-cols-2">
            <JsonPanel title="Trace" value={item.trace ?? {}} />
            <JsonPanel title="Mapping" value={item.mapping ?? {}} />
            <JsonPanel title="Normalized Input" value={item.normalized_input} />
            <JsonPanel title="Outbound Payload" value={item.outbound_response} />
          </div>
          {item.error ? <p className="mt-2 text-xs text-red-600">{item.error}</p> : null}
        </div>
      ))}
    </div>
  );
}

function ConfigField({
  label,
  value,
  onChange,
  type = "text",
  placeholder
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  placeholder?: string;
}) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <Input value={value} type={type} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
    </div>
  );
}

export default function ConnectorsPage() {
  const [userId, setUserId] = useState("");
  const [connectors, setConnectors] = useState<ConnectorRecord[]>([]);
  const [mappings, setMappings] = useState<ConnectorConversationMappingRecord[]>([]);
  const [deliveries, setDeliveries] = useState<ConnectorDeliveryRecord[]>([]);
  const [activeConnectorId, setActiveConnectorId] = useState("");
  const [configDraft, setConfigDraft] = useState<Record<string, unknown>>({});
  const [skeleton, setSkeleton] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  async function refresh(activeId?: string) {
    const connectorRows = await listConnectors();
    setConnectors(connectorRows);
    const nextId = activeId ?? connectorRows[0]?.connector_id ?? "";
    setActiveConnectorId(nextId);
    if (nextId) {
      const [deliveryRows, mappingRows] = await Promise.all([
        listConnectorDeliveries(nextId),
        listConnectorMappings(nextId)
      ]);
      setDeliveries(deliveryRows);
      setMappings(mappingRows);
    } else {
      setDeliveries([]);
      setMappings([]);
    }
  }

  useEffect(() => {
    async function bootstrap() {
      const user = await bootstrapUser();
      setUserId(user.user.id);
      const connectorSkeleton = await getFeishuSkeleton();
      setSkeleton(connectorSkeleton);
      await refresh();
    }

    bootstrap().catch((reason) => {
      setError(reason instanceof Error ? reason.message : "Connector page bootstrap failed.");
    });
  }, []);

  const activeConnector = connectors.find((item) => item.connector_id === activeConnectorId) ?? connectors[0] ?? null;

  useEffect(() => {
    if (activeConnector) {
      setConfigDraft(activeConnector.config ?? {});
    } else {
      setConfigDraft({});
    }
  }, [activeConnector]);

  const failedDeliveries = useMemo(
    () => deliveries.filter((item) => item.delivery_status === "failed"),
    [deliveries]
  );
  const latestTrace = deliveries[0]?.trace ?? null;

  const mode = String(configDraft.mode ?? activeConnector?.config.mode ?? "mock");
  const deliveryMode = String(configDraft.delivery_mode ?? activeConnector?.config.delivery_mode ?? "webhook");

  function setConfigValue(key: string, value: string | boolean) {
    setConfigDraft((current) => ({
      ...current,
      [key]: value
    }));
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Connector Layer"
        title="Feishu Connector"
        description="Configure mock or live Feishu delivery, inspect webhook traces, and keep conversation mapping visible from the same screen."
        badge="Receive + Reply"
      />

      {error ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
      {status ? <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{status}</div> : null}

      <div className="grid gap-4 xl:grid-cols-[380px_minmax(0,1fr)]">
        <Card className="bg-white/88">
          <CardHeader>
            <CardTitle>Create Connector</CardTitle>
            <CardDescription>
              Start with mock mode locally. When you are ready for live Feishu replies, switch the delivery mode to webhook or OpenAPI and save the connector config below.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <pre className="overflow-x-auto rounded-[1.25rem] bg-[#faf8f4] p-4 text-xs leading-6">
              {JSON.stringify(skeleton ?? {}, null, 2)}
            </pre>
            <Button
              className="w-full"
              disabled={!userId || loading}
              onClick={async () => {
                setLoading(true);
                setError("");
                try {
                  await createConnector({
                    user_id: userId,
                    connector_type: "feishu",
                    name: "Feishu Primary Connector",
                    status: "active",
                    config: {
                      mode: "mock",
                      delivery_mode: "webhook",
                      verification_token: "local-test-token",
                      reply_webhook_url: "",
                      app_id: "",
                      app_secret: "",
                      receive_id_type: "chat_id",
                      openapi_base_url: "https://open.feishu.cn",
                      force_delivery_failure: false
                    },
                    metadata: {
                      note: "Local baseline connector"
                    }
                  });
                  await refresh();
                  setStatus("Feishu connector created.");
                } catch (reason) {
                  setError(reason instanceof Error ? reason.message : "Connector create failed.");
                } finally {
                  setLoading(false);
                }
              }}
            >
              Create Feishu Connector
            </Button>

            <div className="space-y-3">
              {connectors.map((connector) => (
                <button
                  key={connector.connector_id}
                  className="w-full rounded-[1.25rem] border border-[color:var(--border)] bg-[#faf8f4] px-4 py-4 text-left"
                  onClick={async () => {
                    setActiveConnectorId(connector.connector_id);
                    await refresh(connector.connector_id);
                  }}
                >
                  <div className="flex flex-wrap gap-2">
                    <p className="font-medium">{connector.name}</p>
                    <Badge>{connector.connector_type}</Badge>
                    <Badge>{connector.status}</Badge>
                    <Badge>{String(connector.config.mode ?? "mock")}</Badge>
                    <Badge>{String(connector.config.delivery_mode ?? "webhook")}</Badge>
                  </div>
                  <p className="mt-2 text-xs text-[var(--muted-foreground)]">{connector.connector_id}</p>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="bg-white/88">
            <CardHeader>
              <CardTitle>Connector Details</CardTitle>
              <CardDescription>
                The same webhook path is used for both mock and live inbound traffic. Save the config first, then use Test Connector to verify the current delivery mode.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {activeConnector ? (
                <>
                  <div className="flex flex-wrap gap-2">
                    <Badge>{activeConnector.connector_type}</Badge>
                    <Badge>{activeConnector.status}</Badge>
                    <Badge>{mode}</Badge>
                    <Badge>{deliveryMode}</Badge>
                  </div>
                  <p className="text-xs text-[var(--muted-foreground)]">
                    Webhook path: <code>/api/v1/connectors/feishu/webhook/{activeConnector.connector_id}</code>
                  </p>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label>Mode</Label>
                      <select
                        className="w-full rounded-2xl border border-[color:var(--border)] bg-white px-4 py-3 text-sm"
                        value={mode}
                        onChange={(event) => setConfigValue("mode", event.target.value)}
                      >
                        <option value="mock">mock</option>
                        <option value="live">live</option>
                      </select>
                    </div>
                    <div className="space-y-2">
                      <Label>Delivery Mode</Label>
                      <select
                        className="w-full rounded-2xl border border-[color:var(--border)] bg-white px-4 py-3 text-sm"
                        value={deliveryMode}
                        onChange={(event) => setConfigValue("delivery_mode", event.target.value)}
                      >
                        <option value="webhook">webhook</option>
                        <option value="openapi">openapi</option>
                      </select>
                    </div>
                    <ConfigField
                      label="Verification Token"
                      value={String(configDraft.verification_token ?? "")}
                      onChange={(value) => setConfigValue("verification_token", value)}
                      placeholder="Match the Feishu event subscription token"
                    />
                    <ConfigField
                      label="Reply Webhook URL"
                      value={String(configDraft.reply_webhook_url ?? "")}
                      onChange={(value) => setConfigValue("reply_webhook_url", value)}
                      placeholder="Used in live webhook delivery mode"
                    />
                    <ConfigField
                      label="App ID"
                      value={String(configDraft.app_id ?? "")}
                      onChange={(value) => setConfigValue("app_id", value)}
                      placeholder="Required for live OpenAPI delivery"
                    />
                    <ConfigField
                      label="App Secret"
                      type="password"
                      value={String(configDraft.app_secret ?? "")}
                      onChange={(value) => setConfigValue("app_secret", value)}
                      placeholder="Required for live OpenAPI delivery"
                    />
                    <div className="space-y-2">
                      <Label>Receive ID Type</Label>
                      <select
                        className="w-full rounded-2xl border border-[color:var(--border)] bg-white px-4 py-3 text-sm"
                        value={String(configDraft.receive_id_type ?? "chat_id")}
                        onChange={(event) => setConfigValue("receive_id_type", event.target.value)}
                      >
                        <option value="chat_id">chat_id</option>
                        <option value="open_id">open_id</option>
                        <option value="user_id">user_id</option>
                        <option value="union_id">union_id</option>
                      </select>
                    </div>
                    <ConfigField
                      label="OpenAPI Base URL"
                      value={String(configDraft.openapi_base_url ?? "https://open.feishu.cn")}
                      onChange={(value) => setConfigValue("openapi_base_url", value)}
                      placeholder="https://open.feishu.cn"
                    />
                  </div>

                  <label className="flex items-center gap-3 rounded-2xl border border-[color:var(--border)] bg-[#faf8f4] px-4 py-3 text-sm">
                    <input
                      type="checkbox"
                      checked={configDraft.force_delivery_failure === true}
                      onChange={(event) => setConfigValue("force_delivery_failure", event.target.checked)}
                    />
                    Force delivery failure for testing
                  </label>

                  <pre className="overflow-x-auto rounded-[1.25rem] bg-[#faf8f4] p-4 text-xs leading-6">
                    {JSON.stringify(configDraft, null, 2)}
                  </pre>

                  <div className="flex flex-wrap gap-3">
                    <Button
                      disabled={loading}
                      onClick={async () => {
                        setLoading(true);
                        setError("");
                        try {
                          await updateConnector(activeConnector.connector_id, {
                            config: configDraft
                          });
                          await refresh(activeConnector.connector_id);
                          setStatus("Connector config saved.");
                        } catch (reason) {
                          setError(reason instanceof Error ? reason.message : "Connector save failed.");
                        } finally {
                          setLoading(false);
                        }
                      }}
                    >
                      Save Config
                    </Button>
                    <Button
                      disabled={loading}
                      variant="secondary"
                      onClick={async () => {
                        setLoading(true);
                        setError("");
                        try {
                          const result = await testConnector(activeConnector.connector_id, {
                            message_text: "What response style do I prefer? Please answer briefly.",
                            mode: mode
                          });
                          await refresh(activeConnector.connector_id);
                          setStatus(
                            `Test completed: ${result.delivery_status} | conversation ${result.trace?.mapped_conversation_id ?? "pending"}`
                          );
                        } catch (reason) {
                          setError(reason instanceof Error ? reason.message : "Connector test failed.");
                        } finally {
                          setLoading(false);
                        }
                      }}
                    >
                      Test Connector
                    </Button>
                  </div>
                </>
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">Create a connector first.</p>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="bg-white/88">
              <CardHeader>
                <CardTitle>Conversation Mapping</CardTitle>
                <CardDescription>Same Feishu chat should keep reusing the same internal conversation once a mapping exists.</CardDescription>
              </CardHeader>
              <CardContent>
                <MappingList mappings={mappings} />
              </CardContent>
            </Card>

            <Card className="bg-white/88">
              <CardHeader>
                <CardTitle>Trace Snapshot</CardTitle>
                <CardDescription>Latest connector trace with normalized input, persona choice, skills used, fallback status, and outbound summary.</CardDescription>
              </CardHeader>
              <CardContent>
                {latestTrace ? (
                  <JsonPanel title="Latest Trace" value={latestTrace} />
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">No trace recorded yet.</p>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="bg-white/88">
              <CardHeader>
                <CardTitle>Recent Deliveries</CardTitle>
                <CardDescription>Inbound summary, normalized input, mapped conversation, and outbound payload are all stored here.</CardDescription>
              </CardHeader>
              <CardContent>
                <DeliveryList deliveries={deliveries} />
              </CardContent>
            </Card>

            <Card className="bg-white/88">
              <CardHeader>
                <CardTitle>Delivery Failures</CardTitle>
                <CardDescription>Failures stay visible here, but mapping and internal agent execution should still remain intact.</CardDescription>
              </CardHeader>
              <CardContent>
                <DeliveryList deliveries={failedDeliveries} />
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
