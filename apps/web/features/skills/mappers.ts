import type { SkillInvocationRecord, SkillRecord } from "@agent/shared";

import type { SkillCardViewModel, SkillInvocationViewModel } from "./view-models";

function skillTypeLabel(skill: SkillRecord) {
  return skill.is_builtin ? "builtin" : "community";
}

function executableHandler(skill: SkillRecord) {
  return typeof skill.runtime_config?.handler_slug === "string"
    ? String(skill.runtime_config.handler_slug)
    : skill.is_builtin
      ? skill.slug
      : "";
}

export function toSkillCardViewModel(skill: SkillRecord): SkillCardViewModel {
  const handler = executableHandler(skill);
  return {
    id: skill.id,
    title: skill.title,
    description: skill.description,
    status: skill.status,
    typeLabel: skillTypeLabel(skill),
    slug: skill.slug,
    versionLabel: `v${skill.version}`,
    proxyLabel:
      !skill.is_builtin && skill.runtime_config?.handler_slug
        ? `proxy:${String(skill.runtime_config.handler_slug)}`
        : undefined,
    handlerLabel: handler ? `handler:${handler}` : "manifest-only",
    isCommunity: !skill.is_builtin,
    toggleLabel: skill.status === "active" ? "Disable Skill" : "Enable Skill",
    manifestJson: JSON.stringify(skill.manifest, null, 2),
    runtimeConfigJson: JSON.stringify(skill.runtime_config, null, 2)
  };
}

export function toSkillInvocationViewModel(invocation: SkillInvocationRecord): SkillInvocationViewModel {
  return {
    id: invocation.invocation_id,
    badges: [invocation.skill_slug, invocation.tool_name, invocation.trigger_source, invocation.status],
    traceId: invocation.trace_id,
    timingLabel: `started: ${invocation.started_at ?? "n/a"} | finished: ${invocation.finished_at ?? "n/a"}`,
    outputJson: JSON.stringify(invocation.output, null, 2),
    error: invocation.error
  };
}
