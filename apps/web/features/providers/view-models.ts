import type { UUID } from "@agent/shared";

export type ProviderFormType = "deepseek" | "openai_compatible" | "ollama";

export type ProviderPreset = {
  name: string;
  baseUrl: string;
  modelName: string;
  apiKeyRef: string;
  helper: string;
};

export type ProviderFormState = {
  name: string;
  providerType: ProviderFormType;
  baseUrl: string;
  modelName: string;
  apiKeyRef: string;
  isDefault: boolean;
  isEnabled: boolean;
};

export type ProviderCardViewModel = {
  id?: UUID;
  name: string;
  providerType: string;
  modelName: string;
  baseUrl: string;
  apiKeyRef?: string | null;
  isDefault: boolean;
  isEnabled: boolean;
  statusLabel: string;
  runtime?: LocalAdapterRuntimeViewModel | null;
};

export type LocalAdapterRuntimeViewModel = {
  status: string;
  resident: boolean;
  device?: string | null;
  adapterPath: string;
  baseModel: string;
  loadCount: number;
  requestCount: number;
  activeRequestCount: number;
  idleSeconds: number;
  idleTimeoutSeconds: number;
  generateTimeoutSeconds: number;
  memoryAllocatedMb?: number | null;
  memoryReservedMb?: number | null;
  lastEvictionReason?: string | null;
  error?: string | null;
};

export type ProviderValidationViewModel = {
  providerId?: UUID | null;
  providerName: string;
  modelName: string;
  providerType: string;
  mode: string;
  healthStatus: string;
  routePolicy: string;
  fallbackPolicy: string;
  fallbackAvailable: boolean;
  apiKeyConfigured: boolean;
  completionOk: boolean;
  streamOk: boolean;
  toolCallOk: boolean;
  completionPreview: string;
  streamPreview: string;
  toolCallsJson: string;
  errorLabel?: string | null;
  recommendation?: string | null;
};

export const PROVIDER_PRESETS: Record<ProviderFormType, ProviderPreset> = {
  deepseek: {
    name: "DeepSeek",
    baseUrl: "https://api.deepseek.com",
    modelName: "deepseek-chat",
    apiKeyRef: "env:DEEPSEEK_API_KEY",
    helper: "适合直接�?DeepSeek 官方 API�?
  },
  openai_compatible: {
    name: "OpenAI Compatible",
    baseUrl: "https://api.openai.com/v1",
    modelName: "gpt-4o-mini",
    apiKeyRef: "env:OPENAI_API_KEY",
    helper: "适合 OpenAI、Groq、Together、Moonshot 等兼�?Chat Completions 的服务�?
  },
  ollama: {
    name: "Ollama",
    baseUrl: "http://localhost:11434",
    modelName: "qwen3:14b",
    apiKeyRef: "",
    helper: "适合本机 Ollama，建议先用小上下文验证�?
  }
};
