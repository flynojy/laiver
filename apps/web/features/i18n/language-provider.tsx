"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode
} from "react";

import { translations, type Language } from "@/features/i18n/dictionary";

const STORAGE_KEY = "laiver.ui.language";

type LanguageContextValue = {
  language: Language;
  setLanguage: (language: Language) => void;
  toggleLanguage: () => void;
  t: (value: string) => string;
  tNode: (node: ReactNode) => ReactNode;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

function exactTranslation(value: string, language: Language) {
  for (const [key, translation] of Object.entries(translations)) {
    if (value === key || value === translation.en || value === translation.zh) {
      return translation[language];
    }
  }
  return null;
}

function applyDynamicTranslation(value: string, language: Language) {
  if (language === "en") {
    return value;
  }

  const dynamicRules: Array<[RegExp, (match: RegExpMatchArray) => string]> = [
    [/^importance (.+)$/i, (match) => `重要度 ${match[1]}`],
    [/^confidence (.+)$/i, (match) => `置信度 ${match[1]}`],
    [/^route (.+)$/i, (match) => `路由 ${match[1]}`],
    [/^fallback (.+) (available|unavailable)$/i, (match) => `备用策略 ${match[1]} ${match[2] === "available" ? "可用" : "不可用"}`],
    [/^(\d+) messages?$/i, (match) => `${match[1]} 条消息`],
    [/^(\d+) speakers?$/i, (match) => `${match[1]} 位发言人`],
    [/^(\d+) writes?$/i, (match) => `${match[1]} 条写入`],
    [/^(\d+) summarized$/i, (match) => `${match[1]} 条已摘要`],
    [/^(\d+) recent kept$/i, (match) => `${match[1]} 条近期保留`],
    [/^(.+) messages, participants: (.+)$/i, (match) => `${match[1]} 条消息，参与者：${match[2]}`],
    [/^Participants: (.+)$/i, (match) => `参与者：${match[1]}`],
    [/^Selected package: (.+)$/i, (match) => `已选择包：${match[1] === "none" ? "无" : match[1]}`],
    [/^Current default: (.+)$/i, (match) => `当前默认：${match[1]}`],
    [/^API key configured: (yes|no)$/i, (match) => `API Key 已配置：${match[1] === "yes" ? "是" : "否"}`],
    [/^(.+) created\. Dataset export is ready for local training\.$/i, (match) => `${match[1]} 已创建，数据集已可用于本地训练。`],
    [/^(.+) has started\. Laiver will keep refreshing the local training status\.$/i, (match) => `${match[1]} 已启动，Laiver 会持续刷新本地训练状态。`],
    [/^(.+) is now available in the provider registry\.$/i, (match) => `${match[1]} 已加入模型供应商列表。`],
    [/^(.+) is now the default model provider\.$/i, (match) => `${match[1]} 已设为默认模型供应商。`],
    [/^(.+) installed\.$/i, (match) => `${match[1]} 已安装。`],
    [/^(.+) disabled\.$/i, (match) => `${match[1]} 已停用。`],
    [/^(.+) enabled\.$/i, (match) => `${match[1]} 已启用。`],
    [/^(.+) removed\.$/i, (match) => `${match[1]} 已移除。`]
  ];

  for (const [pattern, translate] of dynamicRules) {
    const match = value.match(pattern);
    if (match) {
      return translate(match);
    }
  }

  return value;
}

function preserveWhitespace(original: string, translated: string) {
  const leading = original.match(/^\s*/)?.[0] ?? "";
  const trailing = original.match(/\s*$/)?.[0] ?? "";
  return `${leading}${translated}${trailing}`;
}

function translateText(value: string, language: Language) {
  const trimmed = value.trim();
  if (!trimmed) {
    return value;
  }

  const exact = exactTranslation(trimmed, language);
  if (exact) {
    return preserveWhitespace(value, exact);
  }

  return preserveWhitespace(value, applyDynamicTranslation(trimmed, language));
}

// Shallow translation: only translate string / number / array-of-primitives that are
// passed *directly* as children to a translated primitive (Badge, CardTitle, etc.).
// Nested React elements are returned as-is — their own translated primitives (or
// explicit t() calls in page code) handle their own subtree. This avoids the
// O(N) cloneElement walk over deep JSX trees on every render while preserving
// the "<Badge>literal</Badge>" auto-translation that call sites rely on.
function translateReactNode(node: ReactNode, language: Language): ReactNode {
  if (typeof node === "string") {
    return translateText(node, language);
  }

  if (typeof node === "number" || typeof node === "boolean" || node == null) {
    return node;
  }

  if (Array.isArray(node)) {
    const primitiveOnly = node.every((child) => typeof child === "string" || typeof child === "number");
    if (primitiveOnly) {
      return translateText(node.map(String).join(""), language);
    }
    // Mixed content (string + element): translate only the string slots, leave elements alone.
    return node.map((child) =>
      typeof child === "string" || typeof child === "number" ? translateReactNode(child, language) : child
    );
  }

  // React element or anything else: pass through. Recursion into element subtrees
  // is intentionally skipped — it caused per-frame cloneElement over the whole
  // tree and can break key stability in keyed lists.
  return node;
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>("en");

  useEffect(() => {
    const storedLanguage = window.localStorage.getItem(STORAGE_KEY);
    if (storedLanguage === "en" || storedLanguage === "zh") {
      setLanguageState(storedLanguage);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, language);
    document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  }, [language]);

  const value = useMemo<LanguageContextValue>(() => {
    return {
      language,
      setLanguage: setLanguageState,
      toggleLanguage: () => setLanguageState((current) => (current === "en" ? "zh" : "en")),
      t: (text) => translateText(text, language),
      tNode: (node) => translateReactNode(node, language)
    };
  }, [language]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useI18n() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useI18n must be used inside LanguageProvider.");
  }
  return context;
}
