from __future__ import annotations

import json
import os
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import SkillStatus
from app.models.runtime import Skill, SkillInvocation
from app.schemas.runtime import (
    SkillCreate,
    SkillInstallRequest,
    SkillInvocationRead,
    SkillManifestPayload,
    ToolDefinition,
)
from app.services import memory_service

SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"
COMMUNITY_SKILLS_DIR = Path(os.getenv("COMMUNITY_SKILLS_DIR", (SKILLS_DIR.parent / "community_skills").as_posix()))
MEMORY_RECALL_HINTS = (
    "remember",
    "memory",
    "recall",
    "earlier",
    "before",
    "preference",
    "prefer",
    "what do i",
    "response style",
)
TASK_HINTS = (
    "todo",
    "to do",
    "task",
    "action item",
    "follow up",
    "follow-up",
    "next step",
    "need to",
    "must",
    "should",
)
FORCED_FAILURE_TOKEN = "[force-skill-error]"
SKILL_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")


@dataclass
class PlannedSkillCall:
    skill: Skill
    tool_name: str
    arguments: dict[str, Any]
    trigger_source: str


@dataclass
class SkillExecutionResult:
    skill: Skill
    tool_name: str
    output: dict[str, Any]
    invocation: SkillInvocation
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None and self.invocation.status == "success"

    def as_read(self) -> SkillInvocationRead:
        return SkillInvocationRead.model_validate(self.invocation)


class BaseSkillHandler(ABC):
    slug: str

    @abstractmethod
    def should_trigger(self, message: str, context: dict[str, Any]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def planned_arguments(self, message: str, context: dict[str, Any]) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    async def invoke(self, arguments: dict[str, Any], context: dict[str, Any], db: Session) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def summarize_output(self, output: dict[str, Any]) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def fallback_arguments(self, message: str, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class MemorySearchSkill(BaseSkillHandler):
    slug = "memory-search"

    def should_trigger(self, message: str, context: dict[str, Any]) -> bool:
        lowered = message.lower()
        return any(keyword in lowered for keyword in MEMORY_RECALL_HINTS)

    def planned_arguments(self, message: str, context: dict[str, Any]) -> dict[str, Any] | None:
        if not self.should_trigger(message, context):
            return None
        return {"query": message, "limit": 4}

    async def invoke(self, arguments: dict[str, Any], context: dict[str, Any], db: Session) -> dict[str, Any]:
        rows = memory_service.search_memories(
            db,
            user_id=str(context["user_id"]),
            persona_id=str(context["persona_id"]) if context.get("persona_id") else None,
            query=str(arguments.get("query", "")),
            limit=int(arguments.get("limit", 4)),
        )
        return {
            "matches": [
                {
                    "id": str(item.id),
                    "memory_type": item.memory_type.value,
                    "content": item.content,
                    "importance_score": item.importance_score,
                    "confidence_score": item.confidence_score,
                    "source": item.details.get("source"),
                    "memory_label": item.details.get("memory_label"),
                }
                for item in rows
            ]
        }

    def summarize_output(self, output: dict[str, Any]) -> list[str]:
        matches = output.get("matches", [])
        if not matches:
            return ["memory-search: no matching memories found"]
        return [
            f"memory-search: recalled {item['content']}"
            for item in matches[:3]
            if isinstance(item, dict) and item.get("content")
        ]

    def fallback_arguments(self, message: str, context: dict[str, Any]) -> dict[str, Any]:
        return {"query": message, "limit": 4}


class TaskExtractorSkill(BaseSkillHandler):
    slug = "task-extractor"

    def should_trigger(self, message: str, context: dict[str, Any]) -> bool:
        lowered = message.lower()
        return any(keyword in lowered for keyword in TASK_HINTS)

    def planned_arguments(self, message: str, context: dict[str, Any]) -> dict[str, Any] | None:
        if not self.should_trigger(message, context):
            return None
        return {"text": message}

    def _priority_for(self, text: str) -> str:
        lowered = text.lower()
        if any(keyword in lowered for keyword in ("asap", "urgent", "today", "now", "immediately")):
            return "high"
        if any(keyword in lowered for keyword in ("tomorrow", "this week", "soon")):
            return "medium"
        return "low"

    async def invoke(self, arguments: dict[str, Any], context: dict[str, Any], db: Session) -> dict[str, Any]:
        text = str(arguments.get("text", ""))
        if FORCED_FAILURE_TOKEN in text.lower():
            raise RuntimeError("Forced task-extractor failure for local testing.")

        chunks = [
            chunk.strip(" -*\t")
            for chunk in re.split(r"[\n;]|(?:\band\b)", text, flags=re.IGNORECASE)
            if chunk.strip()
        ]
        tasks = []
        for chunk in chunks:
            if len(chunk) < 8:
                continue
            summary = chunk[:200]
            title = summary.rstrip(".")
            if len(title) > 72:
                title = f"{title[:69].rstrip()}..."
            tasks.append(
                {
                    "title": title,
                    "summary": summary,
                    "priority": self._priority_for(summary),
                }
            )
        return {"tasks": tasks, "count": len(tasks)}

    def summarize_output(self, output: dict[str, Any]) -> list[str]:
        tasks = output.get("tasks", [])
        if not tasks:
            return ["task-extractor: no structured tasks found"]
        return [
            f"task-extractor: {item['title']} [{item['priority']}]"
            for item in tasks[:5]
            if isinstance(item, dict) and item.get("title")
        ]

    def fallback_arguments(self, message: str, context: dict[str, Any]) -> dict[str, Any]:
        return {"text": message}


class SkillRuntime:
    def __init__(self) -> None:
        self.handlers: dict[str, BaseSkillHandler] = {
            "memory-search": MemorySearchSkill(),
            "task-extractor": TaskExtractorSkill(),
        }

    def _load_manifest(self, path: Path) -> SkillManifestPayload:
        return SkillManifestPayload.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def _validate_skill_slug(self, slug: str) -> str:
        normalized = slug.strip().lower()
        if not SKILL_SLUG_PATTERN.fullmatch(normalized):
            raise ValueError("Skill slug must use lowercase letters, numbers, or hyphens.")
        return normalized

    def _community_skill_dir(self, slug: str) -> Path:
        return COMMUNITY_SKILLS_DIR / slug

    def _write_community_skill_files(
        self,
        *,
        slug: str,
        manifest: SkillManifestPayload,
        runtime_config: dict[str, Any],
    ) -> dict[str, str]:
        skill_dir = self._community_skill_dir(slug)
        skill_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = skill_dir / "skill.json"
        runtime_path = skill_dir / "runtime.json"

        manifest_path.write_text(
            json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        runtime_path.write_text(
            json.dumps(runtime_config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        return {
            "manifest_path": manifest_path.as_posix(),
            "runtime_path": runtime_path.as_posix(),
        }

    def _runtime_config_for_install(
        self,
        *,
        slug: str,
        runtime_config: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        config = dict(runtime_config)
        config.setdefault("type", "community_manifest")
        config["source"] = source
        config["installed_at"] = datetime.now(timezone.utc).isoformat()

        handler_slug = config.get("handler_slug")
        if handler_slug is not None:
            handler_slug = str(handler_slug).strip()
            if handler_slug not in self.handlers:
                raise ValueError(f"Unsupported handler slug: {handler_slug}")
            config["handler_slug"] = handler_slug

        file_paths = self._write_community_skill_files(
            slug=slug,
            manifest=SkillManifestPayload.model_validate(config.pop("__manifest__")),
            runtime_config=config,
        )
        config.update(file_paths)
        return config

    def _install_payload_from_json(self, payload: dict[str, Any], *, source: str) -> SkillInstallRequest:
        manifest_payload = payload.get("manifest", payload)
        runtime_config = payload.get("runtime_config", {})
        activate = bool(payload.get("activate", True))
        install_source = str(payload.get("source", source))
        return SkillInstallRequest(
            manifest=SkillManifestPayload.model_validate(manifest_payload),
            runtime_config=dict(runtime_config),
            source=install_source,
            activate=activate,
        )

    def parse_skill_package(self, *, filename: str, content: bytes) -> SkillInstallRequest:
        suffix = Path(filename).suffix.lower()
        if suffix == ".json":
            payload = json.loads(content.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Skill package JSON must be an object.")
            return self._install_payload_from_json(payload, source=f"upload:{filename}")

        if suffix == ".zip":
            try:
                with ZipFile(BytesIO(content)) as archive:
                    names = [item.filename for item in archive.infolist() if not item.is_dir()]
                    manifest_candidates = sorted(
                        [name for name in names if Path(name).name.lower() == "skill.json"],
                        key=lambda item: (item.count("/"), len(item)),
                    )
                    if not manifest_candidates:
                        raise ValueError("Skill archive must include a skill.json manifest.")

                    manifest_payload = json.loads(archive.read(manifest_candidates[0]).decode("utf-8"))
                    runtime_candidates = sorted(
                        [name for name in names if Path(name).name.lower() == "runtime.json"],
                        key=lambda item: (item.count("/"), len(item)),
                    )
                    payload: dict[str, Any] = {"manifest": manifest_payload}
                    if runtime_candidates:
                        payload["runtime_config"] = json.loads(
                            archive.read(runtime_candidates[0]).decode("utf-8")
                        )
                    return self._install_payload_from_json(payload, source=f"upload:{filename}")
            except BadZipFile as exc:
                raise ValueError("Skill archive is not a valid zip file.") from exc

        raise ValueError("Unsupported skill package format. Use .json or .zip.")

    def local_manifests(self) -> list[SkillManifestPayload]:
        manifests: list[SkillManifestPayload] = []
        if not SKILLS_DIR.exists():
            return manifests
        for path in sorted(SKILLS_DIR.glob("*/skill.json")):
            manifests.append(self._load_manifest(path))
        return manifests

    def _active_skill_rows(self, db: Session) -> list[Skill]:
        return db.scalars(
            select(Skill).where(Skill.status == SkillStatus.ACTIVE).order_by(Skill.created_at.asc())
        ).all()

    def _tool_map(self, skills: list[Skill]) -> dict[str, Skill]:
        mapping: dict[str, Skill] = {}
        for skill in skills:
            if not self.handler_for_skill(skill):
                continue
            manifest = SkillManifestPayload.model_validate(skill.manifest)
            for tool in manifest.tools:
                mapping[tool.name] = skill
        return mapping

    def handler_for_slug(self, slug: str) -> BaseSkillHandler | None:
        return self.handlers.get(slug)

    def handler_slug_for_skill(self, skill: Skill) -> str | None:
        if skill.slug in self.handlers:
            return skill.slug
        handler_slug = skill.runtime_config.get("handler_slug")
        if isinstance(handler_slug, str) and handler_slug in self.handlers:
            return handler_slug
        return None

    def handler_for_skill(self, skill: Skill) -> BaseSkillHandler | None:
        handler_slug = self.handler_slug_for_skill(skill)
        if not handler_slug:
            return None
        return self.handlers.get(handler_slug)

    def skill_can_execute(self, skill: Skill) -> bool:
        return self.handler_for_skill(skill) is not None

    def _skill_triggers_match(self, skill: Skill, message: str) -> bool:
        manifest = SkillManifestPayload.model_validate(skill.manifest)
        if not manifest.triggers:
            return False
        lowered = message.lower()
        return any(trigger.strip().lower() in lowered for trigger in manifest.triggers if trigger.strip())

    def summarize_execution(self, execution: SkillExecutionResult) -> list[str]:
        if execution.error:
            return [f"{execution.skill.slug}: failed - {execution.error}"]
        handler = self.handler_for_skill(execution.skill)
        if not handler:
            return [f"{execution.skill.slug}: completed"]
        return handler.summarize_output(execution.output)

    def invocation_summary(self, execution: SkillExecutionResult) -> str:
        suffix = execution.error or execution.invocation.status
        return f"{execution.skill.slug}/{execution.tool_name}: {suffix}"

    def tool_definitions(self, db: Session) -> list[ToolDefinition]:
        definitions: list[ToolDefinition] = []
        for skill in self._active_skill_rows(db):
            if not self.skill_can_execute(skill):
                continue
            manifest = SkillManifestPayload.model_validate(skill.manifest)
            for tool in manifest.tools:
                definitions.append(
                    ToolDefinition(
                        function={
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.parameters,
                        }
                    )
                )
        return definitions

    def builtin_manifests(self) -> list[SkillCreate]:
        return [
            SkillCreate(
                slug=manifest.slug,
                name=manifest.name,
                version=manifest.version,
                title=manifest.title,
                description=manifest.description,
                manifest=manifest,
                runtime_config={"type": "builtin", "manifest_path": f"skills/{manifest.slug}/skill.json"},
                is_builtin=True,
            )
            for manifest in self.local_manifests()
            if manifest.slug in self.handlers
        ]

    def sync_builtin_skills(self, db: Session) -> list[Skill]:
        rows: list[Skill] = []
        for manifest in self.builtin_manifests():
            row = db.scalar(select(Skill).where(Skill.slug == manifest.slug))
            if row:
                row.name = manifest.name
                row.version = manifest.version
                row.title = manifest.title
                row.description = manifest.description
                row.manifest = manifest.manifest.model_dump()
                row.runtime_config = manifest.runtime_config
                row.is_builtin = True
                rows.append(row)
            else:
                row = Skill(
                    **{
                        **manifest.model_dump(),
                        "manifest": manifest.manifest.model_dump(),
                    }
                )
                db.add(row)
                rows.append(row)
        db.commit()
        for row in rows:
            db.refresh(row)
        return rows

    def install_skill(self, db: Session, payload: SkillInstallRequest) -> Skill:
        manifest = payload.manifest.model_copy(update={"slug": self._validate_skill_slug(payload.manifest.slug)})
        existing = db.scalar(select(Skill).where(Skill.slug == manifest.slug))
        if existing and existing.is_builtin:
            raise ValueError("Builtin skills cannot be overwritten by community packages.")

        tool_name_conflicts: dict[str, str] = {}
        registered_skills = db.scalars(select(Skill)).all()
        for row in registered_skills:
            if row.slug == manifest.slug:
                continue
            row_manifest = SkillManifestPayload.model_validate(row.manifest)
            for tool in row_manifest.tools:
                tool_name_conflicts[tool.name] = row.slug

        conflicting_tool = next((tool.name for tool in manifest.tools if tool.name in tool_name_conflicts), None)
        if conflicting_tool:
            raise ValueError(
                f"Tool name '{conflicting_tool}' is already provided by skill '{tool_name_conflicts[conflicting_tool]}'."
            )

        runtime_config_seed = dict(payload.runtime_config)
        runtime_config_seed["__manifest__"] = manifest.model_dump()
        runtime_config = self._runtime_config_for_install(
            slug=manifest.slug,
            runtime_config=runtime_config_seed,
            source=payload.source,
        )

        status = SkillStatus.ACTIVE if payload.activate else SkillStatus.DISABLED
        if existing:
            existing.name = manifest.name
            existing.version = manifest.version
            existing.title = manifest.title
            existing.description = manifest.description
            existing.manifest = manifest.model_dump()
            existing.runtime_config = runtime_config
            existing.status = status
            existing.is_builtin = False
            row = existing
        else:
            row = Skill(
                user_id=None,
                slug=manifest.slug,
                name=manifest.name,
                version=manifest.version,
                title=manifest.title,
                description=manifest.description,
                manifest=manifest.model_dump(),
                runtime_config=runtime_config,
                status=status,
                is_builtin=False,
            )
            db.add(row)

        db.commit()
        db.refresh(row)
        return row

    def enable_skill(self, db: Session, skill_id: str) -> Skill | None:
        row = db.scalar(select(Skill).where(Skill.id == uuid.UUID(skill_id)))
        if not row:
            return None
        row.status = SkillStatus.ACTIVE
        db.commit()
        db.refresh(row)
        return row

    def disable_skill(self, db: Session, skill_id: str) -> Skill | None:
        row = db.scalar(select(Skill).where(Skill.id == uuid.UUID(skill_id)))
        if not row:
            return None
        row.status = SkillStatus.DISABLED
        db.commit()
        db.refresh(row)
        return row

    def uninstall_skill(self, db: Session, skill_id: str) -> bool:
        row = db.scalar(select(Skill).where(Skill.id == uuid.UUID(skill_id)))
        if not row:
            return False
        if not row.is_builtin:
            skill_dir = self._community_skill_dir(row.slug)
            if skill_dir.exists():
                for child in skill_dir.iterdir():
                    if child.is_file():
                        child.unlink()
                skill_dir.rmdir()
        db.delete(row)
        db.commit()
        return True

    def plan_invocations(self, db: Session, message: str, context: dict[str, Any]) -> list[PlannedSkillCall]:
        planned: list[PlannedSkillCall] = []
        for skill in self._active_skill_rows(db):
            handler = self.handler_for_skill(skill)
            if not handler:
                continue
            arguments = handler.planned_arguments(message, context)
            if not arguments and self._skill_triggers_match(skill, message):
                arguments = handler.fallback_arguments(message, context)
            if not arguments:
                continue
            manifest = SkillManifestPayload.model_validate(skill.manifest)
            tool_name = manifest.tools[0].name if manifest.tools else skill.slug
            planned.append(
                PlannedSkillCall(
                    skill=skill,
                    tool_name=tool_name,
                    arguments=arguments,
                    trigger_source="planner",
                )
            )
        return planned

    async def execute(
        self,
        *,
        name: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
        db: Session,
        trace_id: str,
        conversation_id: Any = None,
        message_id: Any = None,
        trigger_source: str = "model",
        skill: Skill | None = None,
    ) -> SkillExecutionResult:
        active_skills = self._active_skill_rows(db)
        skill = skill or self._tool_map(active_skills).get(name)
        if not skill:
            raise ValueError(f"Unknown or disabled skill: {name}")

        handler = self.handler_for_skill(skill)
        if not handler:
            raise ValueError(f"No handler registered for skill: {skill.slug}")

        started_at = datetime.now(timezone.utc)
        try:
            output = await handler.invoke(arguments, context, db)
            invocation = SkillInvocation(
                skill_id=skill.id,
                skill_slug=skill.slug,
                tool_name=name,
                trace_id=trace_id,
                trigger_source=trigger_source,
                conversation_id=conversation_id,
                message_id=message_id,
                input_payload=arguments,
                output_payload=output,
                status="success",
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
            )
            db.add(invocation)
            db.flush()
            return SkillExecutionResult(skill=skill, tool_name=name, output=output, invocation=invocation)
        except Exception as exc:
            invocation = SkillInvocation(
                skill_id=skill.id,
                skill_slug=skill.slug,
                tool_name=name,
                trace_id=trace_id,
                trigger_source=trigger_source,
                conversation_id=conversation_id,
                message_id=message_id,
                input_payload=arguments,
                output_payload={},
                status="error",
                error_message=str(exc),
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
            )
            db.add(invocation)
            db.flush()
            return SkillExecutionResult(
                skill=skill,
                tool_name=name,
                output={},
                invocation=invocation,
                error=str(exc),
            )

    def recent_invocations(self, db: Session, limit: int = 20) -> list[SkillInvocation]:
        return db.scalars(
            select(SkillInvocation).order_by(SkillInvocation.created_at.desc()).limit(limit)
        ).all()


skill_runtime = SkillRuntime()
