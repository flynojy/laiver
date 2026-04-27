from __future__ import annotations

import json
import os
import shutil
import sys
import unittest
import uuid
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient
from openpyxl import Workbook

API_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = API_ROOT.parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

FIXTURE_PATH = WORKSPACE_ROOT / "docs" / "fixtures" / "mvp-e2e-chat.txt"
ALT_FIXTURE_PATH = WORKSPACE_ROOT / "docs" / "fixtures" / "mvp-e2e-detailed-chat.txt"
TEST_RUN_ROOT = WORKSPACE_ROOT / ".tmp" / "test-runs"


def _clear_app_modules() -> None:
    db_session = sys.modules.get("app.db.session")
    if db_session is not None and hasattr(db_session, "engine"):
        db_session.engine.dispose()
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


def build_client(db_path: Path, extra_env: dict[str, str] | None = None) -> TestClient:
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ["AUTO_INIT_DB"] = "true"
    os.environ["COMMUNITY_SKILLS_DIR"] = (db_path.parent / "community-skills").as_posix()
    os.environ["FINE_TUNE_ARTIFACTS_DIR"] = (db_path.parent / "fine-tuning").as_posix()
    os.environ["LOCAL_ADAPTER_IDLE_TTL_SECONDS"] = "900"
    os.environ["LOCAL_ADAPTER_CLEANUP_INTERVAL_SECONDS"] = "60"
    os.environ["LOCAL_ADAPTER_GENERATE_TIMEOUT_SECONDS"] = "20"
    for key, value in (extra_env or {}).items():
        os.environ[key] = value
    _clear_app_modules()
    from app.main import app

    return TestClient(app)


def bootstrap_runtime(client: TestClient) -> str:
    user = client.post("/api/v1/users/bootstrap").json()["user"]
    client.post("/api/v1/model-providers/bootstrap")
    client.post("/api/v1/skills/seed")
    return user["id"]


def preview_fixture(client: TestClient) -> dict:
    sample = FIXTURE_PATH.read_text(encoding="utf-8")
    response = client.post(
        "/api/v1/imports/preview",
        files={"file": ("mvp-e2e-chat.txt", sample, "text/plain")},
    )
    response.raise_for_status()
    return response.json()


def commit_fixture(client: TestClient, user_id: str, preview: dict) -> dict:
    payload = {
        "user_id": user_id,
        "file_name": "mvp-e2e-chat.txt",
        "source_type": preview["source_type"],
        "file_size": len(FIXTURE_PATH.read_bytes()),
        "preview": {"total_messages": preview["total_messages"]},
        "normalized_messages": preview["normalized_messages"],
    }
    response = client.post("/api/v1/imports/commit", json=payload)
    response.raise_for_status()
    return response.json()


def extract_persona_fixture(client: TestClient, user_id: str, import_id: str) -> dict:
    response = client.post(
        "/api/v1/personas/extract",
        json={
            "user_id": user_id,
            "import_id": import_id,
            "name": "Integration Persona",
            "persist": True,
            "set_default": True,
        },
    )
    response.raise_for_status()
    return response.json()


def create_full_state(client: TestClient) -> tuple[str, dict, dict, dict]:
    user_id = bootstrap_runtime(client)
    preview = preview_fixture(client)
    commit = commit_fixture(client, user_id, preview)
    persona = extract_persona_fixture(client, user_id, commit["import_job"]["id"])
    return user_id, preview, commit, persona


def create_connector(
    client: TestClient,
    user_id: str,
    *,
    status: str = "active",
    mode: str = "mock",
    delivery_mode: str = "webhook",
    force_delivery_failure: bool = False,
    reply_webhook_url: str = "",
) -> dict:
    response = client.post(
        "/api/v1/connectors",
        json={
            "user_id": user_id,
            "connector_type": "feishu",
            "name": "Feishu Test Connector",
            "status": status,
            "config": {
                "mode": mode,
                "delivery_mode": delivery_mode,
                "verification_token": "local-test-token",
                "reply_webhook_url": reply_webhook_url,
                "force_delivery_failure": force_delivery_failure,
            },
            "metadata": {"source": "integration-test"},
        },
    )
    response.raise_for_status()
    return response.json()


def create_model_provider(
    client: TestClient,
    *,
    name: str,
    provider_type: str,
    base_url: str,
    model_name: str,
    api_key_ref: str | None = None,
    is_default: bool = False,
    is_enabled: bool = True,
    settings: dict | None = None,
) -> dict:
    response = client.post(
        "/api/v1/model-providers",
        json={
            "name": name,
            "provider_type": provider_type,
            "base_url": base_url,
            "model_name": model_name,
            "api_key_ref": api_key_ref,
            "settings": settings or {},
            "is_default": is_default,
            "is_enabled": is_enabled,
        },
    )
    response.raise_for_status()
    return response.json()


def build_feishu_webhook_payload(
    text: str,
    *,
    message_id: str | None = None,
    external_user_id: str = "ou_test_user",
    external_chat_id: str = "oc_test_chat",
    sender_name: str = "Feishu Tester",
    verification_token: str = "local-test-token",
) -> dict:
    return {
        "header": {"token": verification_token},
        "event": {
            "message": {
                "message_id": message_id or f"msg_{uuid.uuid4().hex}",
                "chat_id": external_chat_id,
                "create_time": "1710752400000",
                "message_type": "text",
                "content": json.dumps({"text": text}, ensure_ascii=False),
            },
            "sender": {
                "sender_id": {"open_id": external_user_id},
                "sender_name": sender_name,
            },
        }
    }


def build_wechat_workbook_bytes() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "\u804a\u5929\u8bb0\u5f55"
    rows = [
        ["\u4f1a\u8bdd\u4fe1\u606f"],
        ["\u5fae\u4fe1ID", "wxid_test_user", None, "\u6635\u79f0", "Dominus"],
        [
            "\u5bfc\u51fa\u5de5\u5177",
            "WeFlow",
            "\u5bfc\u51fa\u7248\u672c",
            "0.0.2",
            "\u5e73\u53f0",
            "wechat",
            "\u5bfc\u51fa\u65f6\u95f4",
            "2026-02-12 18:46:25",
        ],
        [
            "\u5e8f\u53f7",
            "\u65f6\u95f4",
            "\u53d1\u9001\u8005\u8eab\u4efd",
            "\u6d88\u606f\u7c7b\u578b",
            "\u5185\u5bb9",
        ],
        ["1", "2025-11-27 15:02:08", "\u738b\u5f66\u83e1\uff082.26\uff09", "\u7cfb\u7edf\u6d88\u606f", "Greetings shown above"],
        [
            "2",
            "2025-11-27 15:02:08",
            "\u738b\u5f66\u83e1\uff082.26\uff09",
            "\u6587\u672c\u6d88\u606f",
            "I've accepted your friend request. Now let's chat!",
        ],
        ["3", "2025-11-27 16:48:48", "\u6211", "\u6587\u672c\u6d88\u606f", "\u521a\u624d\u73a9\u7684\u5f88\u9ad8\u5174"],
        ["4", "2025-11-27 16:48:50", "\u6211", "\u52a8\u753b\u8868\u60c5", "[\u5176\u4ed6\u6d88\u606f]"],
        [
            "5",
            "2025-11-27 17:30:03",
            "\u738b\u5f66\u83e1\uff082.26\uff09",
            "\u6587\u672c\u6d88\u606f",
            "\u54c8\u54c8\u4f46\u662f\u6211\u4eec\u4e5f\u6ca1\u6709\u62ff\u5230\u5956\u5440",
        ],
    ]
    for row in rows:
        worksheet.append(row)

    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def build_community_skill_package(
    *,
    slug: str,
    tool_name: str,
    title: str,
    description: str,
    handler_slug: str | None = None,
    triggers: list[str] | None = None,
) -> dict:
    payload: dict = {
        "manifest": {
            "schema_version": "1.0",
            "name": slug,
            "slug": slug,
            "version": "1.0.0",
            "title": title,
            "description": description,
            "tools": [
                {
                    "name": tool_name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "query": {"type": "string"},
                        },
                    },
                    "returns": {"type": "object"},
                }
            ],
            "permissions": ["message:read"],
            "triggers": triggers or [],
        },
        "runtime_config": {},
        "source": "integration-test",
        "activate": True,
    }
    if handler_slug:
        payload["runtime_config"]["handler_slug"] = handler_slug
    return payload


def build_community_skill_zip_bytes(package: dict) -> bytes:
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("skill.json", json.dumps(package["manifest"], ensure_ascii=False))
        if package.get("runtime_config"):
            archive.writestr("runtime.json", json.dumps(package["runtime_config"], ensure_ascii=False))
    return stream.getvalue()


class IntegrationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = TEST_RUN_ROOT / f"case-{uuid.uuid4().hex}"
        self.tempdir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.tempdir / "test.db"
        self.client = build_client(self.db_path)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_imports_preview_endpoint(self) -> None:
        bootstrap_runtime(self.client)
        preview = preview_fixture(self.client)
        self.assertEqual(preview["total_messages"], 7)
        self.assertEqual(len(preview["normalized_messages"]), 7)
        self.assertEqual(preview["normalized_messages"][0]["speaker"], "Morgan")

    def test_imports_commit_endpoint(self) -> None:
        user_id = bootstrap_runtime(self.client)
        preview = preview_fixture(self.client)
        commit = commit_fixture(self.client, user_id, preview)
        self.assertEqual(commit["import_job"]["status"], "committed")
        self.assertEqual(len(commit["normalized_messages"]), 7)

    def test_imports_preview_endpoint_accepts_wechat_xlsx(self) -> None:
        user_id = bootstrap_runtime(self.client)
        workbook_bytes = build_wechat_workbook_bytes()

        preview_response = self.client.post(
            "/api/v1/imports/preview",
            files={
                "file": (
                    "wechat-chat.xlsx",
                    workbook_bytes,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        preview_response.raise_for_status()
        preview = preview_response.json()

        self.assertEqual(preview["source_type"], "xlsx")
        self.assertEqual(preview["total_messages"], 4)
        self.assertEqual(preview["detected_participants"], ["Dominus", "\u738b\u5f66\u83e1\uff082.26\uff09"])
        self.assertEqual(preview["normalized_messages"][0]["role"], "system")
        self.assertEqual(preview["normalized_messages"][1]["speaker"], "\u738b\u5f66\u83e1\uff082.26\uff09")
        self.assertEqual(preview["normalized_messages"][2]["speaker"], "Dominus")
        self.assertEqual(preview["normalized_messages"][2]["role"], "assistant")
        self.assertEqual(preview["normalized_messages"][2]["metadata"]["source_format"], "wechat_weflow_xlsx")
        self.assertTrue(preview["normalized_messages"][2]["metadata"]["is_self"])
        self.assertEqual(preview["source_metadata"]["conversation_owner"], "Dominus")
        self.assertEqual(preview["source_metadata"]["export_tool"], "WeFlow")
        self.assertEqual(preview["source_metadata"]["speaker_stats"]["Dominus"]["message_count"], 1)

        commit_response = self.client.post(
            "/api/v1/imports/commit",
            json={
                "user_id": user_id,
                "file_name": "wechat-chat.xlsx",
                "source_type": preview["source_type"],
                "file_size": len(workbook_bytes),
                "preview": {
                    "total_messages": preview["total_messages"],
                    "source_metadata": preview["source_metadata"],
                },
                "normalized_messages": preview["normalized_messages"],
            },
        )
        commit_response.raise_for_status()
        commit = commit_response.json()

        self.assertEqual(commit["import_job"]["source_type"], "xlsx")
        self.assertEqual(commit["import_job"]["normalized_summary"]["source_format"], "wechat_weflow_xlsx")
        self.assertEqual(commit["import_job"]["normalized_summary"]["conversation_owner"], "Dominus")
        self.assertEqual(commit["import_job"]["normalized_summary"]["speaker_stats"]["Dominus"]["message_count"], 1)

    def test_persona_extract_endpoint_accepts_source_speaker(self) -> None:
        user_id = bootstrap_runtime(self.client)
        workbook_bytes = build_wechat_workbook_bytes()
        preview = self.client.post(
            "/api/v1/imports/preview",
            files={
                "file": (
                    "wechat-chat.xlsx",
                    workbook_bytes,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        ).json()
        commit = self.client.post(
            "/api/v1/imports/commit",
            json={
                "user_id": user_id,
                "file_name": "wechat-chat.xlsx",
                "source_type": preview["source_type"],
                "file_size": len(workbook_bytes),
                "preview": {
                    "total_messages": preview["total_messages"],
                    "source_metadata": preview["source_metadata"],
                },
                "normalized_messages": preview["normalized_messages"],
            },
        ).json()

        response = self.client.post(
            "/api/v1/personas/extract",
            json={
                "user_id": user_id,
                "import_id": commit["import_job"]["id"],
                "name": "Dominus Persona",
                "source_speaker": "Dominus",
                "persist": True,
                "set_default": True,
            },
        )
        response.raise_for_status()
        payload = response.json()

        self.assertEqual(payload["source_speaker"], "Dominus")
        self.assertEqual(payload["source_message_count"], 1)
        self.assertEqual(payload["persona"]["user_id"], user_id)

    def test_persona_extract_endpoint(self) -> None:
        user_id, _, commit, persona = create_full_state(self.client)
        self.assertEqual(persona["persona"]["user_id"], user_id)
        self.assertTrue(persona["source_message_count"] >= 1)
        self.assertTrue(persona["persona"]["confidence_scores"])
        self.assertTrue(persona["persona"]["evidence_samples"])
        self.assertIn("topics", persona["persona"]["evidence_samples"])

    def test_agent_respond_endpoint(self) -> None:
        user_id, _, commit, persona = create_full_state(self.client)
        response = self.client.post(
            "/api/v1/agent/respond",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "message": "Please remember that I prefer concise answers and practical steps.",
            },
        )
        response.raise_for_status()
        payload = response.json()
        self.assertEqual(payload["debug"]["provider_name"], "deepseek")
        self.assertEqual(payload["debug"]["persona_id"], persona["persona"]["id"])
        self.assertGreaterEqual(payload["debug"]["memory_write_count"], 1)
        self.assertTrue(payload["debug"]["trace_id"])
        self.assertEqual(payload["debug"]["model_mode"], "mock")
        self.assertIn("memory-search", payload["debug"]["skills_used"])
        self.assertTrue(payload["debug"]["skill_invocation_summary"])
        self.assertTrue(payload["debug"]["skill_output_summary"])

    def test_skills_list_endpoint_returns_local_manifests(self) -> None:
        bootstrap_runtime(self.client)
        response = self.client.get("/api/v1/skills")
        response.raise_for_status()
        skills = response.json()
        self.assertEqual({item["slug"] for item in skills}, {"memory-search", "task-extractor"})
        self.assertEqual(skills[0]["manifest"]["schema_version"], "1.0")
        self.assertIn("tools", skills[0]["manifest"])
        self.assertIn("permissions", skills[0]["manifest"])
        self.assertIn("triggers", skills[0]["manifest"])

    def test_skill_enable_disable_endpoints(self) -> None:
        bootstrap_runtime(self.client)
        skills = self.client.get("/api/v1/skills").json()
        target = next(item for item in skills if item["slug"] == "memory-search")
        removable = next(item for item in skills if item["slug"] == "task-extractor")

        disabled = self.client.post(f"/api/v1/skills/{target['id']}/disable")
        disabled.raise_for_status()
        self.assertEqual(disabled.json()["status"], "disabled")

        enabled = self.client.post(f"/api/v1/skills/{target['id']}/enable")
        enabled.raise_for_status()
        self.assertEqual(enabled.json()["status"], "active")

        deleted = self.client.delete(f"/api/v1/skills/{removable['id']}")
        deleted.raise_for_status()
        self.assertTrue(deleted.json()["deleted"])

    def test_skill_invocations_endpoint(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        self.client.post(
            "/api/v1/agent/respond",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "message": "Please remember what response style I prefer before answering.",
            },
        ).raise_for_status()

        response = self.client.get("/api/v1/skills/invocations")
        response.raise_for_status()
        invocations = response.json()
        self.assertTrue(invocations)
        self.assertEqual(invocations[0]["skill_slug"], "memory-search")
        self.assertEqual(invocations[0]["status"], "success")
        self.assertIn("invocation_id", invocations[0])
        self.assertIn("input", invocations[0])
        self.assertIn("output", invocations[0])
        self.assertIn("started_at", invocations[0])
        self.assertIn("finished_at", invocations[0])

    def test_skill_install_endpoint_accepts_community_manifest(self) -> None:
        bootstrap_runtime(self.client)
        package = build_community_skill_package(
            slug="community-memory-proxy",
            tool_name="community-memory-proxy",
            title="Community Memory Proxy",
            description="Community memory recall wrapper.",
            handler_slug="memory-search",
            triggers=["recall profile"],
        )

        response = self.client.post("/api/v1/skills/install", json=package)
        response.raise_for_status()
        payload = response.json()

        self.assertFalse(payload["is_builtin"])
        self.assertEqual(payload["slug"], "community-memory-proxy")
        self.assertEqual(payload["runtime_config"]["handler_slug"], "memory-search")
        self.assertTrue(Path(payload["runtime_config"]["manifest_path"]).exists())
        self.assertTrue(Path(payload["runtime_config"]["runtime_path"]).exists())

    def test_skill_install_upload_endpoint_accepts_zip_package(self) -> None:
        bootstrap_runtime(self.client)
        package = build_community_skill_package(
            slug="community-task-zip",
            tool_name="community-task-zip",
            title="Community Task Zip",
            description="Community task extractor package.",
            handler_slug="task-extractor",
            triggers=["shiproom"],
        )

        response = self.client.post(
            "/api/v1/skills/install/upload",
            files={"file": ("community-task.zip", build_community_skill_zip_bytes(package), "application/zip")},
        )
        response.raise_for_status()
        payload = response.json()

        self.assertEqual(payload["slug"], "community-task-zip")
        self.assertEqual(payload["runtime_config"]["handler_slug"], "task-extractor")
        self.assertEqual(payload["runtime_config"]["source"], "upload:community-task.zip")

    def test_installed_community_skill_executes_via_proxy_handler(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        builtin_task = next(
            item for item in self.client.get("/api/v1/skills").json() if item["slug"] == "task-extractor"
        )
        self.client.post(f"/api/v1/skills/{builtin_task['id']}/disable").raise_for_status()

        package = build_community_skill_package(
            slug="community-shiproom-tasks",
            tool_name="community-shiproom-tasks",
            title="Community Shiproom Tasks",
            description="Task extraction triggered by shiproom notes.",
            handler_slug="task-extractor",
            triggers=["shiproom"],
        )
        install_response = self.client.post("/api/v1/skills/install", json=package)
        install_response.raise_for_status()

        response = self.client.post(
            "/api/v1/agent/respond",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "message": "Shiproom: prepare rollout checklist for tomorrow.",
            },
        )
        response.raise_for_status()
        payload = response.json()

        self.assertIn("community-shiproom-tasks", payload["debug"]["skills_used"])
        self.assertNotIn("task-extractor", payload["debug"]["skills_used"])
        self.assertEqual(payload["debug"]["fallback_status"], "mock_provider_grounded")
        self.assertIn("structured action items", payload["response"].lower())
        self.assertTrue(
            any(item["skill_slug"] == "community-shiproom-tasks" for item in payload["debug"]["skill_invocations"])
        )

    def test_memory_search_grounds_final_answer(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        first = self.client.post(
            "/api/v1/agent/respond",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "message": "Please remember that I prefer concise answers and practical steps.",
            },
        )
        first.raise_for_status()

        second = self.client.post(
            "/api/v1/agent/respond",
            json={
                "user_id": user_id,
                "conversation_id": first.json()["conversation_id"],
                "persona_id": persona["persona"]["id"],
                "message": "What style of response do I prefer? Keep it practical.",
            },
        )
        second.raise_for_status()
        payload = second.json()
        self.assertIn("memory-search", payload["debug"]["skills_used"])
        self.assertEqual(payload["debug"]["fallback_status"], "mock_provider_grounded")
        self.assertIn("concise answers", payload["response"].lower())

    def test_task_extractor_grounds_final_answer(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        response = self.client.post(
            "/api/v1/agent/respond",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "message": "Todo: follow up with Alice today and write the release summary this week.",
            },
        )
        response.raise_for_status()
        payload = response.json()
        self.assertIn("task-extractor", payload["debug"]["skills_used"])
        self.assertEqual(payload["debug"]["fallback_status"], "mock_provider_grounded")
        self.assertIn("structured action items", payload["response"].lower())
        self.assertIn("follow up with alice today", payload["response"].lower())

    def test_skill_failure_falls_back_cleanly(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        response = self.client.post(
            "/api/v1/agent/respond",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "message": "Todo: [force-skill-error] prepare the rollout checklist.",
            },
        )
        response.raise_for_status()
        payload = response.json()
        self.assertIn("task-extractor", payload["debug"]["skills_used"])
        self.assertEqual(payload["debug"]["fallback_status"], "skill_error_fallback")
        self.assertTrue(any(item["status"] == "error" for item in payload["debug"]["skill_invocations"]))
        self.assertIn("skills failed", payload["response"].lower())

    def test_memories_list_endpoint(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        self.client.post(
            "/api/v1/agent/respond",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "message": "Please remember that I prefer concise answers and practical steps.",
            },
        ).raise_for_status()
        response = self.client.get("/api/v1/memories")
        response.raise_for_status()
        memories = response.json()
        self.assertGreaterEqual(len(memories), 2)
        self.assertIn("confidence_score", memories[0])
        self.assertIn("memory_label", memories[0]["metadata"])

    def test_memory_search_router_prioritizes_profile_preferences(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        self.client.post(
            "/api/v1/memories",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "memory_type": "semantic",
                "content": "I prefer concise answers with practical steps.",
                "metadata": {
                    "memory_label": "preference",
                    "source": "manual",
                    "origin": "user_message",
                },
            },
        ).raise_for_status()
        self.client.post(
            "/api/v1/memories",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "memory_type": "session",
                "content": "We briefly discussed release checklists in passing.",
                "metadata": {
                    "memory_label": "session",
                    "source": "manual",
                    "origin": "user_message",
                },
            },
        ).raise_for_status()

        response = self.client.post(
            "/api/v1/memories/search",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "query": "What style of response do I prefer?",
                "limit": 5,
            },
        )
        response.raise_for_status()
        rows = response.json()

        self.assertTrue(rows)
        self.assertEqual(rows[0]["metadata"]["memory_label"], "preference")
        self.assertIn("concise answers", rows[0]["content"].lower())

    def test_memory_search_router_prioritizes_episodic_recall(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        self.client.post(
            "/api/v1/memories",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "memory_type": "episodic",
                "content": "Last time we discussed the launch checklist and deployment timing.",
                "metadata": {
                    "memory_label": "episodic",
                    "source": "manual",
                    "origin": "user_message",
                },
            },
        ).raise_for_status()
        self.client.post(
            "/api/v1/memories",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "memory_type": "semantic",
                "content": "I prefer concise answers with practical steps.",
                "metadata": {
                    "memory_label": "preference",
                    "source": "manual",
                    "origin": "user_message",
                },
            },
        ).raise_for_status()

        response = self.client.post(
            "/api/v1/memories/search",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "query": "What happened last time we talked about the launch?",
                "limit": 5,
            },
        )
        response.raise_for_status()
        rows = response.json()

        self.assertTrue(rows)
        self.assertEqual(rows[0]["metadata"]["memory_label"], "episodic")
        self.assertIn("launch checklist", rows[0]["content"].lower())

    def test_memories_debug_endpoint(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        self.client.post(
            "/api/v1/agent/respond",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "message": "Please remember that I prefer concise answers and practical steps.",
            },
        ).raise_for_status()
        response = self.client.get("/api/v1/memories/debug")
        response.raise_for_status()
        payload = response.json()
        self.assertGreaterEqual(payload["total_memories"], 2)
        self.assertGreaterEqual(payload["total_episodes"], 2)
        self.assertGreaterEqual(payload["total_facts"], 1)
        self.assertGreaterEqual(payload["total_revisions"], 1)
        self.assertGreaterEqual(payload["candidate_counts"]["pending"], 1)
        self.assertTrue(payload["recent_memories"])
        self.assertTrue(payload["recent_episodes"])
        self.assertTrue(payload["recent_facts"])
        self.assertTrue(payload["recent_revisions"])
        self.assertTrue(payload["recent_candidates"])
        self.assertIn("profile_summary", payload)
        self.assertTrue(payload["profile_summary"])
        self.assertTrue(payload["user_profile_snapshot"])
        self.assertTrue(payload["relationship_state_snapshot"])
        self.assertIn("lifecycle_counts", payload)
        self.assertGreaterEqual(payload["lifecycle_counts"]["active"], 1)

    def test_memory_candidate_review_queue_supports_approve_and_reject(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        self.client.post(
            "/api/v1/memories",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "memory_type": "semantic",
                "content": "I prefer concise answers with practical steps.",
                "importance_score": 0.82,
                "confidence_score": 0.8,
                "metadata": {
                    "memory_label": "preference",
                    "source": "manual",
                    "origin": "user_message",
                    "state": "active",
                },
            },
        ).raise_for_status()

        candidates_response = self.client.get("/api/v1/memories/candidates?status=pending&limit=10")
        candidates_response.raise_for_status()
        candidates = candidates_response.json()

        self.assertTrue(candidates)
        self.assertEqual(candidates[0]["candidate_type"], "preference")
        self.assertEqual(candidates[0]["status"], "pending")

        approve_response = self.client.patch(
            f"/api/v1/memories/candidates/{candidates[0]['id']}",
            json={"status": "approved", "reviewer_type": "human"},
        )
        approve_response.raise_for_status()
        approved = approve_response.json()
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["reviewer_type"], "human")
        self.assertIsNotNone(approved["processed_at"])

        self.client.post(
            "/api/v1/memories",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "memory_type": "instruction",
                "content": "Please remember that you should not use a playful tone.",
                "importance_score": 0.88,
                "confidence_score": 0.84,
                "metadata": {
                    "memory_label": "instruction",
                    "source": "manual",
                    "origin": "user_message",
                    "state": "active",
                },
            },
        ).raise_for_status()

        refreshed_candidates = self.client.get("/api/v1/memories/candidates?status=pending&limit=10")
        refreshed_candidates.raise_for_status()
        pending_rows = refreshed_candidates.json()
        self.assertTrue(pending_rows)

        reject_response = self.client.patch(
            f"/api/v1/memories/candidates/{pending_rows[0]['id']}",
            json={"status": "rejected", "reviewer_type": "human"},
        )
        reject_response.raise_for_status()
        rejected = reject_response.json()
        self.assertEqual(rejected["status"], "rejected")
        self.assertIsNotNone(rejected["processed_at"])

    def test_gated_memory_candidate_requires_approval_before_fact_commit(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        create_response = self.client.post(
            "/api/v1/memories",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "memory_type": "semantic",
                "content": "I might prefer shorter answers when I am tired.",
                "importance_score": 0.62,
                "confidence_score": 0.58,
                "metadata": {
                    "memory_label": "preference",
                    "source": "manual",
                    "origin": "user_message",
                    "requires_review": True,
                    "state": "active",
                },
            },
        )
        create_response.raise_for_status()
        memory = create_response.json()

        self.assertEqual(memory["metadata"]["state"], "pending_review")
        self.assertFalse(memory["metadata"]["current_version"])
        self.assertTrue(memory["metadata"]["fact_write_gated"])

        from sqlalchemy import select

        from app.db.session import SessionLocal
        from app.models.memory import Memory
        from app.models.memory_fact import MemoryFact
        from app.models.memory_revision import MemoryRevision

        with SessionLocal() as db:
            facts_before = db.scalars(
                select(MemoryFact).where(MemoryFact.user_id == uuid.UUID(user_id))
            ).all()
            self.assertEqual(facts_before, [])

        candidates_response = self.client.get("/api/v1/memories/candidates?status=pending&limit=10")
        candidates_response.raise_for_status()
        candidates = candidates_response.json()

        self.assertTrue(candidates)
        self.assertEqual(candidates[0]["candidate_type"], "preference")
        self.assertIsNone(candidates[0]["proposed_value"]["fact_id"])
        self.assertTrue(candidates[0]["proposed_value"]["fact_write_gated"])

        approve_response = self.client.patch(
            f"/api/v1/memories/candidates/{candidates[0]['id']}",
            json={"status": "approved", "reviewer_type": "human"},
        )
        approve_response.raise_for_status()
        approved = approve_response.json()

        self.assertEqual(approved["status"], "approved")
        self.assertIsNotNone(approved["proposed_value"]["fact_id"])
        self.assertIsNotNone(approved["proposed_value"]["fact_revision_id"])

        with SessionLocal() as db:
            facts_after = db.scalars(
                select(MemoryFact).where(MemoryFact.user_id == uuid.UUID(user_id))
            ).all()
            revisions_after = db.scalars(
                select(MemoryRevision).where(MemoryRevision.fact_id == facts_after[0].id)
            ).all()
            refreshed_memory = db.scalar(select(Memory).where(Memory.id == uuid.UUID(memory["id"])))

            self.assertEqual(len(facts_after), 1)
            self.assertEqual(len(revisions_after), 1)
            self.assertIsNotNone(refreshed_memory)
            self.assertEqual(refreshed_memory.details["state"], "active")
            self.assertTrue(refreshed_memory.details["current_version"])
            self.assertFalse(refreshed_memory.details["fact_write_gated"])
            self.assertEqual(refreshed_memory.details["review_status"], "approved")

    def test_memory_maintenance_decays_facts_and_expires_stale_candidates(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        active_response = self.client.post(
            "/api/v1/memories",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "memory_type": "semantic",
                "content": "I prefer practical answers with short checklists.",
                "importance_score": 0.82,
                "confidence_score": 0.82,
                "metadata": {
                    "memory_label": "preference",
                    "source": "manual",
                    "origin": "user_message",
                    "decay_policy": "volatile",
                    "state": "active",
                },
            },
        )
        active_response.raise_for_status()

        gated_response = self.client.post(
            "/api/v1/memories",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "memory_type": "semantic",
                "content": "I might prefer soft reminders on weekends.",
                "importance_score": 0.55,
                "confidence_score": 0.52,
                "metadata": {
                    "memory_label": "preference",
                    "source": "manual",
                    "origin": "user_message",
                    "requires_review": True,
                    "state": "active",
                },
            },
        )
        gated_response.raise_for_status()
        gated_memory_id = gated_response.json()["id"]

        from datetime import datetime, timedelta, timezone
        from sqlalchemy import select

        from app.db.session import SessionLocal
        from app.models.memory import Memory
        from app.models.memory_candidate import MemoryCandidate
        from app.models.memory_fact import MemoryFact
        from app.models.user_profile import UserProfile

        old_date = datetime.now(timezone.utc) - timedelta(days=80)
        with SessionLocal() as db:
            fact = db.scalar(select(MemoryFact).where(MemoryFact.user_id == uuid.UUID(user_id)))
            self.assertIsNotNone(fact)
            fact.decay_policy = "volatile"
            fact.last_confirmed_at = old_date
            fact.last_used_at = None
            fact.stability_score = 0.13
            fact.importance = 0.15
            fact.confidence = 0.3

            pending_candidates = db.scalars(
                select(MemoryCandidate).where(
                    MemoryCandidate.user_id == uuid.UUID(user_id),
                    MemoryCandidate.status == "pending",
                )
            ).all()
            stale_candidate = next(
                (
                    candidate
                    for candidate in pending_candidates
                    if str(candidate.proposed_value.get("memory_id")) == gated_memory_id
                ),
                None,
            )
            self.assertIsNotNone(stale_candidate)
            stale_candidate.created_at = old_date
            db.commit()

        response = self.client.post("/api/v1/memories/maintenance/run")
        response.raise_for_status()
        report = response.json()

        self.assertGreaterEqual(report["facts_scanned"], 1)
        self.assertGreaterEqual(report["facts_decayed"], 1)
        self.assertGreaterEqual(report["facts_archived"], 1)
        self.assertGreaterEqual(report["candidates_ignored"], 1)
        self.assertGreaterEqual(report["profiles_rebuilt"], 1)

        with SessionLocal() as db:
            archived_fact = db.scalar(select(MemoryFact).where(MemoryFact.user_id == uuid.UUID(user_id)))
            gated_memory = db.scalar(select(Memory).where(Memory.id == uuid.UUID(gated_memory_id)))
            ignored_candidate = db.scalar(
                select(MemoryCandidate).where(
                    MemoryCandidate.user_id == uuid.UUID(user_id),
                    MemoryCandidate.status == "ignored",
                )
            )
            profile = db.scalar(select(UserProfile).where(UserProfile.user_id == uuid.UUID(user_id)))

            self.assertIsNotNone(archived_fact)
            self.assertEqual(archived_fact.status, "archived")
            self.assertEqual(archived_fact.details["archive_reason"], "decayed_below_threshold")
            self.assertIsNotNone(gated_memory)
            self.assertEqual(gated_memory.details["state"], "ignored")
            self.assertIsNotNone(ignored_candidate)
            self.assertIn("maintenance_stale_candidate", ignored_candidate.reason_codes)
            self.assertIsNotNone(profile)
            self.assertGreaterEqual(profile.profile_version, 1)

    def test_duplicate_preference_memory_strengthens_existing_record(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        payload = {
            "user_id": user_id,
            "persona_id": persona["persona"]["id"],
            "memory_type": "semantic",
            "content": "I prefer concise answers with practical steps.",
            "importance_score": 0.82,
            "confidence_score": 0.8,
            "metadata": {
                "memory_label": "preference",
                "source": "manual",
                "origin": "user_message",
                "state": "active",
            },
        }

        first = self.client.post("/api/v1/memories", json=payload)
        first.raise_for_status()
        first_memory = first.json()

        debug_after_first = self.client.get("/api/v1/memories/debug")
        debug_after_first.raise_for_status()

        second = self.client.post("/api/v1/memories", json=payload)
        second.raise_for_status()
        second_memory = second.json()

        debug_after_second = self.client.get("/api/v1/memories/debug")
        debug_after_second.raise_for_status()
        debug_payload = debug_after_second.json()

        self.assertEqual(second_memory["id"], first_memory["id"])
        self.assertEqual(
            debug_payload["total_memories"],
            debug_after_first.json()["total_memories"],
        )
        self.assertEqual(second_memory["metadata"]["reinforcement_count"], 2)
        self.assertEqual(second_memory["metadata"]["duplicate_count"], 2)
        self.assertTrue(second_memory["metadata"]["current_version"])
        self.assertIn("concise answers with practical steps", debug_payload["profile_summary"].lower())

        from sqlalchemy import select

        from app.db.session import SessionLocal
        from app.models.memory_fact import MemoryFact
        from app.models.memory_revision import MemoryRevision
        from app.models.relationship_state import RelationshipState
        from app.models.user_profile import UserProfile

        with SessionLocal() as db:
            facts = db.scalars(
                select(MemoryFact).where(MemoryFact.user_id == uuid.UUID(user_id))
            ).all()
            revisions = db.scalars(
                select(MemoryRevision).where(MemoryRevision.fact_id == facts[0].id).order_by(MemoryRevision.revision_no)
            ).all()
            profile = db.scalar(select(UserProfile).where(UserProfile.user_id == uuid.UUID(user_id)))
            relationship = db.scalar(
                select(RelationshipState).where(
                    RelationshipState.user_id == uuid.UUID(user_id),
                    RelationshipState.persona_id == uuid.UUID(persona["persona"]["id"]),
                )
            )

        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0].fact_type, "preference")
        self.assertEqual(facts[0].reinforcement_count, 2)
        self.assertEqual(facts[0].status, "active")
        self.assertEqual(len(revisions), 2)
        self.assertEqual([item.op for item in revisions], ["create", "reinforce"])
        self.assertEqual(str(facts[0].current_revision_id), str(revisions[-1].id))
        self.assertIsNotNone(profile)
        self.assertIn("concise answers with practical steps", profile.profile_summary.lower())
        self.assertEqual(profile.stable_preferences["items"][0], "I prefer concise answers with practical steps.")
        self.assertIsNotNone(relationship)
        self.assertEqual(relationship.relationship_stage, "new")
        self.assertEqual(relationship.preferred_tone, "concise")

    def test_conflicting_preference_marks_older_memory_as_superseded_and_updates_profile(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        first = self.client.post(
            "/api/v1/memories",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "memory_type": "instruction",
                "content": "Always answer in a concise style.",
                "importance_score": 0.9,
                "confidence_score": 0.88,
                "metadata": {
                    "memory_label": "instruction",
                    "source": "manual",
                    "origin": "user_message",
                    "state": "active",
                    "fact_key": "answer style",
                    "polarity": "positive",
                },
            },
        )
        first.raise_for_status()
        first_memory = first.json()

        second = self.client.post(
            "/api/v1/memories",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "memory_type": "instruction",
                "content": "Do not answer in a concise style.",
                "importance_score": 0.92,
                "confidence_score": 0.9,
                "metadata": {
                    "memory_label": "instruction",
                    "source": "manual",
                    "origin": "user_message",
                    "state": "active",
                    "fact_key": "answer style",
                    "polarity": "negative",
                },
            },
        )
        second.raise_for_status()
        second_memory = second.json()

        memories_response = self.client.get("/api/v1/memories")
        memories_response.raise_for_status()
        memories = memories_response.json()
        first_row = next(item for item in memories if item["id"] == first_memory["id"])
        second_row = next(item for item in memories if item["id"] == second_memory["id"])

        self.assertEqual(first_row["metadata"]["state"], "archived")
        self.assertFalse(first_row["metadata"]["current_version"])
        self.assertEqual(first_row["metadata"]["superseded_by"], second_memory["id"])
        self.assertEqual(second_row["metadata"]["state"], "active")
        self.assertTrue(second_row["metadata"]["current_version"])
        self.assertEqual(first_row["metadata"]["conflict_group"], second_row["metadata"]["conflict_group"])

        debug_response = self.client.get("/api/v1/memories/debug")
        debug_response.raise_for_status()
        debug_payload = debug_response.json()

        self.assertEqual(debug_payload["lifecycle_counts"]["superseded"], 1)
        self.assertTrue(debug_payload["conflict_groups"])
        self.assertIn("do not answer in a concise style", debug_payload["profile_summary"].lower())
        self.assertNotIn("always answer in a concise style", debug_payload["profile_summary"].lower())

        from sqlalchemy import select

        from app.db.session import SessionLocal
        from app.models.memory_fact import MemoryFact
        from app.models.memory_revision import MemoryRevision
        from app.models.relationship_state import RelationshipState
        from app.models.user_profile import UserProfile

        with SessionLocal() as db:
            facts = db.scalars(
                select(MemoryFact).where(MemoryFact.user_id == uuid.UUID(user_id))
            ).all()
            revisions = db.scalars(
                select(MemoryRevision).where(MemoryRevision.fact_id == facts[0].id).order_by(MemoryRevision.revision_no)
            ).all()
            profile = db.scalar(select(UserProfile).where(UserProfile.user_id == uuid.UUID(user_id)))
            relationship = db.scalar(
                select(RelationshipState).where(
                    RelationshipState.user_id == uuid.UUID(user_id),
                    RelationshipState.persona_id == uuid.UUID(persona["persona"]["id"]),
                )
            )

        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0].fact_type, "instruction")
        self.assertEqual(facts[0].status, "active")
        self.assertEqual(facts[0].value_text, "Do not answer in a concise style.")
        self.assertEqual(len(revisions), 2)
        self.assertEqual([item.op for item in revisions], ["create", "supersede"])
        self.assertEqual(str(revisions[-1].supersedes_revision_id), str(revisions[0].id))
        self.assertEqual(str(facts[0].current_revision_id), str(revisions[-1].id))
        self.assertIsNotNone(revisions[0].valid_to)
        self.assertIsNotNone(profile)
        self.assertIn("do not answer in a concise style", profile.profile_summary.lower())
        self.assertIsNotNone(relationship)
        self.assertEqual(relationship.preferred_tone, "concise")
        self.assertTrue(any("do not answer in a concise style" in item.lower() for item in relationship.recent_sensitivities))

    def test_second_turn_recalls_first_memory(self) -> None:
        user_id, preview, commit, persona = create_full_state(self.client)
        first = self.client.post(
            "/api/v1/agent/respond",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "message": "Please remember that I prefer concise answers and practical steps.",
            },
        )
        first.raise_for_status()
        first_payload = first.json()

        second = self.client.post(
            "/api/v1/agent/respond",
            json={
                "user_id": user_id,
                "conversation_id": first_payload["conversation_id"],
                "persona_id": persona["persona"]["id"],
                "message": "What style of response do I prefer? Keep it practical.",
            },
        )
        second.raise_for_status()
        second_payload = second.json()

        self.assertEqual(preview["total_messages"], 7)
        self.assertEqual(len(commit["normalized_messages"]), 7)
        self.assertGreaterEqual(first_payload["debug"]["memory_write_count"], 1)
        self.assertIn("memory-search", second_payload["debug"]["skills_used"])
        self.assertIn("concise answers", second_payload["response"].lower())
        self.assertTrue(
            any(
                "concise answers" in item["content"].lower() or "practical steps" in item["content"].lower()
                for item in second_payload["debug"]["memory_hits"]
            )
        )

    def test_persona_differs_for_different_import_samples(self) -> None:
        user_id = bootstrap_runtime(self.client)

        first_preview = preview_fixture(self.client)
        first_commit = commit_fixture(self.client, user_id, first_preview)
        first_persona = extract_persona_fixture(self.client, user_id, first_commit["import_job"]["id"])

        alt_sample = ALT_FIXTURE_PATH.read_text(encoding="utf-8")
        alt_preview = self.client.post(
            "/api/v1/imports/preview",
            files={"file": ("mvp-e2e-detailed-chat.txt", alt_sample, "text/plain")},
        ).json()
        alt_commit = self.client.post(
            "/api/v1/imports/commit",
            json={
                "user_id": user_id,
                "file_name": "mvp-e2e-detailed-chat.txt",
                "source_type": alt_preview["source_type"],
                "file_size": len(alt_sample.encode("utf-8")),
                "preview": {"total_messages": alt_preview["total_messages"]},
                "normalized_messages": alt_preview["normalized_messages"],
            },
        ).json()
        second_persona = extract_persona_fixture(self.client, user_id, alt_commit["import_job"]["id"])

        self.assertNotEqual(first_persona["persona"]["verbosity"], second_persona["persona"]["verbosity"])
        self.assertNotEqual(first_persona["persona"]["common_topics"], second_persona["persona"]["common_topics"])

    def test_memory_write_can_be_disabled(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        before = self.client.get("/api/v1/memories")
        before.raise_for_status()

        response = self.client.post(
            "/api/v1/agent/respond",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "message": "Please do not store this as a new memory.",
                "controls": {
                    "skills_enabled": True,
                    "memory_write_enabled": False,
                },
            },
        )
        response.raise_for_status()
        payload = response.json()

        after = self.client.get("/api/v1/memories")
        after.raise_for_status()
        self.assertEqual(len(before.json()), len(after.json()))
        self.assertEqual(payload["debug"]["memory_write_count"], 0)
        self.assertFalse(payload["debug"]["memory_write_enabled"])

    def test_skills_can_be_disabled(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        response = self.client.post(
            "/api/v1/agent/respond",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "message": "Todo: follow up with Alice today and write the release summary this week.",
                "controls": {
                    "skills_enabled": False,
                    "memory_write_enabled": True,
                },
            },
        )
        response.raise_for_status()
        payload = response.json()

        self.assertFalse(payload["debug"]["skills_enabled"])
        self.assertEqual(payload["debug"]["skills_used"], [])
        self.assertEqual(payload["debug"]["skill_invocations"], [])
        self.assertEqual(payload["debug"]["explanation"]["skill_outputs_used"], [])

    def test_persona_change_produces_observable_style_change(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        first = self.client.post(
            "/api/v1/agent/respond",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "message": "Say how you will answer the next request.",
                "controls": {
                    "skills_enabled": False,
                    "memory_write_enabled": False,
                },
            },
        )
        first.raise_for_status()

        updated_persona = self.client.put(
            f"/api/v1/personas/{persona['persona']['id']}",
            json={
                "tone": "analytical",
                "verbosity": "detailed",
                "common_topics": ["architecture", "tradeoffs", "analysis"],
                "common_phrases": ["Let us reason it through carefully."],
            },
        )
        updated_persona.raise_for_status()

        second = self.client.post(
            "/api/v1/agent/respond",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "message": "Say how you will answer the next request.",
                "controls": {
                    "skills_enabled": False,
                    "memory_write_enabled": False,
                },
            },
        )
        second.raise_for_status()

        first_payload = first.json()
        second_payload = second.json()
        self.assertNotEqual(first_payload["response"], second_payload["response"])
        self.assertIn("concise", first_payload["response"].lower())
        self.assertIn("detailed", second_payload["response"].lower())
        self.assertIn("analytical", second_payload["response"].lower())
        self.assertIn("common_topics", second_payload["debug"]["explanation"]["persona_fields_used"])

    def test_long_conversation_generates_summary_and_uses_compression(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        conversation_id = None

        turns = [
            "Milestone alpha needs a concise launch summary.",
            "We also decided the onboarding flow should stay lightweight.",
            "Please remember that the root cause should be explained before the fix.",
            "We want follow-up notes to stay practical and calm.",
            "What have we already said about milestone alpha?",
        ]

        last_payload = None
        for message in turns:
            response = self.client.post(
                "/api/v1/agent/respond",
                json={
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "persona_id": persona["persona"]["id"],
                    "message": message,
                    "controls": {
                        "skills_enabled": False,
                        "memory_write_enabled": False,
                    },
                },
            )
            response.raise_for_status()
            last_payload = response.json()
            conversation_id = last_payload["conversation_id"]

        self.assertIsNotNone(last_payload)
        self.assertTrue(last_payload["debug"]["compression_active"])
        self.assertGreater(last_payload["debug"]["summarized_message_count"], 0)
        self.assertIn("milestone alpha", (last_payload["debug"]["conversation_summary"] or "").lower())
        self.assertIn("milestone alpha", last_payload["response"].lower())

        detail = self.client.get(f"/api/v1/conversations/{conversation_id}")
        detail.raise_for_status()
        self.assertTrue(detail.json()["conversation"]["summary"])
        self.assertIn("milestone alpha", detail.json()["conversation"]["summary"].lower())

    def test_connector_test_endpoint_logs_delivery_and_returns_outbound_payload(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        connector = create_connector(self.client, user_id)

        listed = self.client.get("/api/v1/connectors")
        listed.raise_for_status()
        self.assertTrue(any(item["connector_id"] == connector["connector_id"] for item in listed.json()))

        updated = self.client.patch(
            f"/api/v1/connectors/{connector['connector_id']}",
            json={"metadata": {"source": "integration-test", "note": "updated"}},
        )
        updated.raise_for_status()
        self.assertEqual(updated.json()["metadata"]["note"], "updated")

        tested = self.client.post(
            f"/api/v1/connectors/{connector['connector_id']}/test",
            json={
                "message_text": "Please remember that I prefer concise answers and practical steps.",
                "sender_name": "Connector Test",
                "external_user_id": "ou_test_user",
                "external_chat_id": "oc_test_chat",
                "mode": "mock",
            },
        )
        tested.raise_for_status()
        payload = tested.json()

        self.assertEqual(payload["connector"]["connector_type"], "feishu")
        self.assertEqual(payload["normalized_input"]["text"], "Please remember that I prefer concise answers and practical steps.")
        self.assertEqual(payload["mapping"]["default_persona_id"], persona["persona"]["id"])
        self.assertEqual(payload["delivery_status"], "mock_delivered")
        self.assertIn("content", payload["outbound_response"])
        self.assertGreaterEqual(payload["agent_response"]["debug"]["memory_write_count"], 1)
        self.assertEqual(payload["trace"]["mapped_conversation_id"], payload["agent_response"]["conversation_id"])
        self.assertEqual(payload["trace"]["persona_id"], persona["persona"]["id"])
        self.assertEqual(payload["trace"]["delivery_status"], "mock_delivered")

        deliveries = self.client.get(f"/api/v1/connectors/{connector['connector_id']}/deliveries")
        deliveries.raise_for_status()
        self.assertTrue(deliveries.json())
        self.assertEqual(deliveries.json()[0]["delivery_status"], "mock_delivered")
        self.assertEqual(
            deliveries.json()[0]["normalized_input"]["text"],
            "Please remember that I prefer concise answers and practical steps.",
        )
        self.assertEqual(
            deliveries.json()[0]["trace"]["mapped_conversation_id"],
            deliveries.json()[0]["agent_response"]["conversation_id"],
        )

    def test_same_feishu_chat_reuses_internal_conversation_and_recalls_memory(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        connector = create_connector(self.client, user_id)

        first = self.client.post(
            f"/api/v1/connectors/feishu/webhook/{connector['connector_id']}",
            json=build_feishu_webhook_payload(
                "Please remember that I prefer concise answers and practical steps.",
                message_id="msg_first",
            ),
        )
        first.raise_for_status()
        self.assertEqual(first.json()["delivery_status"], "mock_delivered")
        self.assertTrue(first.json()["connector_trace_id"])
        self.assertIsNotNone(first.json()["mapped_conversation_id"])

        second = self.client.post(
            f"/api/v1/connectors/feishu/webhook/{connector['connector_id']}",
            json=build_feishu_webhook_payload(
                "What style of response do I prefer? Keep it practical.",
                message_id="msg_second",
            ),
        )
        second.raise_for_status()
        self.assertEqual(second.json()["delivery_status"], "mock_delivered")

        deliveries = self.client.get(f"/api/v1/connectors/{connector['connector_id']}/deliveries")
        deliveries.raise_for_status()
        rows = deliveries.json()
        self.assertGreaterEqual(len(rows), 2)

        mappings = self.client.get(f"/api/v1/connectors/{connector['connector_id']}/mappings")
        mappings.raise_for_status()
        self.assertEqual(len(mappings.json()), 1)
        self.assertEqual(mappings.json()[0]["default_persona_id"], persona["persona"]["id"])

        latest = rows[0]
        first_delivery = rows[1]
        self.assertEqual(latest["external_message_id"], "msg_second")
        self.assertEqual(latest["normalized_input"]["text"], "What style of response do I prefer? Keep it practical.")
        self.assertIn("response", latest["agent_response"])
        self.assertIn("content", latest["outbound_response"])
        self.assertIn("concise answers", latest["outbound_response"]["content"]["text"].lower())
        self.assertIn("memory-search", latest["agent_response"]["debug"]["skills_used"])
        self.assertEqual(latest["trace"]["persona_id"], persona["persona"]["id"])
        self.assertEqual(latest["trace"]["mapped_conversation_id"], first_delivery["trace"]["mapped_conversation_id"])
        self.assertEqual(latest["trace"]["mapped_conversation_id"], latest["agent_response"]["conversation_id"])
        self.assertEqual(first_delivery["trace"]["mapped_conversation_id"], first_delivery["agent_response"]["conversation_id"])
        self.assertEqual(latest["mapping"]["internal_conversation_id"], first_delivery["mapping"]["internal_conversation_id"])

    def test_connector_delivery_failure_is_logged_without_breaking_agent_flow(self) -> None:
        user_id, _, _, _ = create_full_state(self.client)
        connector = create_connector(self.client, user_id)

        first = self.client.post(
            f"/api/v1/connectors/feishu/webhook/{connector['connector_id']}",
            json=build_feishu_webhook_payload(
                "Please remember that I prefer concise answers and practical steps.",
                message_id="msg_before_failure",
            ),
        )
        first.raise_for_status()

        self.client.patch(
            f"/api/v1/connectors/{connector['connector_id']}",
            json={
                "config": {
                    "mode": "mock",
                    "verification_token": "local-test-token",
                    "reply_webhook_url": "",
                    "force_delivery_failure": True,
                }
            },
        ).raise_for_status()

        response = self.client.post(
            f"/api/v1/connectors/feishu/webhook/{connector['connector_id']}",
            json=build_feishu_webhook_payload(
                "Todo: follow up with Alice today and write the release summary this week.",
                message_id="msg_failure",
            ),
        )
        response.raise_for_status()
        payload = response.json()

        self.assertEqual(payload["delivery_status"], "failed")
        self.assertIn("Forced connector delivery failure", payload["error"])

        deliveries = self.client.get(f"/api/v1/connectors/{connector['connector_id']}/deliveries")
        deliveries.raise_for_status()
        rows = deliveries.json()
        latest = rows[0]
        self.assertEqual(latest["delivery_status"], "failed")
        self.assertIn("response", latest["agent_response"])
        self.assertIn("structured action items", latest["outbound_response"]["content"]["text"].lower())
        self.assertIn("task-extractor", latest["agent_response"]["debug"]["skills_used"])
        self.assertTrue(latest["trace"]["mapped_conversation_id"])
        self.assertEqual(latest["mapping"]["internal_conversation_id"], rows[1]["mapping"]["internal_conversation_id"])

        mappings = self.client.get(f"/api/v1/connectors/{connector['connector_id']}/mappings")
        mappings.raise_for_status()
        self.assertEqual(len(mappings.json()), 1)
        self.assertEqual(mappings.json()[0]["internal_conversation_id"], latest["mapping"]["internal_conversation_id"])

    def test_connector_trace_is_complete_in_mock_and_live_modes(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)

        mock_connector = create_connector(self.client, user_id, mode="mock")
        live_connector = create_connector(
            self.client,
            user_id,
            mode="live",
            reply_webhook_url="mock://success",
        )

        mock_response = self.client.post(
            f"/api/v1/connectors/{mock_connector['connector_id']}/test",
            json={
                "message_text": "Please remember that I prefer concise answers and practical steps.",
                "external_chat_id": "trace_chat",
                "mode": "mock",
            },
        )
        mock_response.raise_for_status()
        live_response = self.client.post(
            f"/api/v1/connectors/{live_connector['connector_id']}/test",
            json={
                "message_text": "What style of response do I prefer? Keep it practical.",
                "external_chat_id": "trace_chat_live",
                "mode": "live",
            },
        )
        live_response.raise_for_status()

        for payload, expected_mode in (
            (mock_response.json(), "mock_delivered"),
            (live_response.json(), "delivered"),
        ):
            self.assertTrue(payload["trace"]["connector_trace_id"])
            self.assertIn("text_preview", payload["trace"]["inbound_summary"])
            self.assertEqual(payload["trace"]["normalized_input"]["connector_type"], "feishu")
            self.assertEqual(payload["trace"]["persona_id"], persona["persona"]["id"])
            self.assertTrue(payload["trace"]["mapped_conversation_id"])
            self.assertIn("memory-search", payload["trace"]["skills_used"])
            self.assertTrue(payload["trace"]["fallback_status"])
            self.assertIn("provider_name", payload["trace"]["outbound_summary"])
        self.assertEqual(payload["trace"]["delivery_status"], expected_mode)

    def test_model_provider_registry_supports_openai_compatible_and_ollama(self) -> None:
        bootstrap_runtime(self.client)

        openai_provider = create_model_provider(
            self.client,
            name="OpenAI Compatible Test",
            provider_type="openai_compatible",
            base_url="mock://success/openai",
            model_name="gpt-test",
            api_key_ref=None,
            is_default=True,
            settings={"supports_streaming": True, "supports_tool_calling": True},
        )
        ollama_provider = create_model_provider(
            self.client,
            name="Ollama Test",
            provider_type="ollama",
            base_url="mock://success/ollama",
            model_name="qwen2.5:7b",
            api_key_ref=None,
            is_default=False,
            settings={"supports_tool_calling": False},
        )

        listed = self.client.get("/api/v1/model-providers")
        listed.raise_for_status()
        provider_types = {item["provider_type"] for item in listed.json()}

        self.assertIn("deepseek", provider_types)
        self.assertIn("openai_compatible", provider_types)
        self.assertIn("ollama", provider_types)
        self.assertTrue(openai_provider["is_default"])
        self.assertFalse(ollama_provider["is_default"])

    def test_model_provider_validation_accepts_mock_openai_compatible_endpoint(self) -> None:
        bootstrap_runtime(self.client)
        provider = create_model_provider(
            self.client,
            name="OpenAI Compatible Test",
            provider_type="openai_compatible",
            base_url="mock://success/openai",
            model_name="gpt-test",
            api_key_ref=None,
            is_default=True,
            settings={"supports_streaming": True, "supports_tool_calling": True},
        )

        response = self.client.post(
            "/api/v1/model-providers/validate",
            json={"provider_id": provider["id"]},
        )
        response.raise_for_status()
        payload = response.json()

        self.assertEqual(payload["provider_type"], "openai_compatible")
        self.assertEqual(payload["mode"], "live")
        self.assertTrue(payload["completion_ok"])
        self.assertTrue(payload["stream_ok"])
        self.assertTrue(payload["tool_call_ok"])

    def test_agent_can_use_mock_openai_compatible_provider_as_default(self) -> None:
        user_id, _, _, persona = create_full_state(self.client)
        provider = create_model_provider(
            self.client,
            name="OpenAI Compatible Test",
            provider_type="openai_compatible",
            base_url="mock://success/openai",
            model_name="gpt-test",
            api_key_ref=None,
            is_default=True,
            settings={"supports_streaming": True, "supports_tool_calling": True},
        )

        response = self.client.post(
            "/api/v1/agent/respond",
            json={
                "user_id": user_id,
                "persona_id": persona["persona"]["id"],
                "message": "Tell me which model provider is answering now.",
                "controls": {
                    "skills_enabled": False,
                    "memory_write_enabled": False,
                },
            },
        )
        response.raise_for_status()
        payload = response.json()

        self.assertEqual(provider["provider_type"], "openai_compatible")
        self.assertEqual(payload["debug"]["provider_name"], "openai_compatible")
        self.assertEqual(payload["debug"]["model_mode"], "live")

    def test_model_provider_validation_skips_cleanly_without_api_key(self) -> None:
        bootstrap_runtime(self.client)
        response = self.client.post("/api/v1/model-providers/validate", json={})
        response.raise_for_status()
        payload = response.json()

        self.assertEqual(payload["mode"], "mock")
        self.assertFalse(payload["api_key_configured"])
        self.assertFalse(payload["completion_ok"])
        self.assertIn("skipped", payload["error"].lower())

    def test_fine_tune_job_creation_exports_local_dataset(self) -> None:
        user_id, _, commit, _ = create_full_state(self.client)

        response = self.client.post(
            "/api/v1/fine-tuning/jobs",
            json={
                "user_id": user_id,
                "import_id": commit["import_job"]["id"],
                "name": "Local Persona Tune",
                "source_speaker": "Assistant",
                "backend": "local_qlora",
                "base_model": "Qwen/Qwen2.5-7B-Instruct",
                "context_window": 4,
            },
        )
        response.raise_for_status()
        payload = response.json()

        self.assertEqual(payload["job"]["status"], "pending")
        self.assertEqual(payload["job"]["source_speaker"], "Assistant")
        self.assertGreater(payload["job"]["train_examples"], 0)
        self.assertTrue(payload["dataset_preview"])
        self.assertTrue(Path(payload["job"]["dataset_path"]).exists())
        self.assertTrue(Path(payload["job"]["config_path"]).exists())
        self.assertTrue(Path(payload["job"]["output_dir"]).exists())
        self.assertIn("run_job.py", payload["job"]["launcher_command"])
        self.assertTrue((Path(payload["job"]["dataset_path"]) / "train.jsonl").exists())

    def test_fine_tune_job_list_and_detail_endpoints(self) -> None:
        user_id, _, commit, _ = create_full_state(self.client)
        created = self.client.post(
            "/api/v1/fine-tuning/jobs",
            json={
                "user_id": user_id,
                "import_id": commit["import_job"]["id"],
                "name": "Second Tune",
                "source_speaker": "Assistant",
            },
        )
        created.raise_for_status()
        job_id = created.json()["job"]["id"]

        listed = self.client.get("/api/v1/fine-tuning/jobs")
        listed.raise_for_status()
        self.assertTrue(any(item["id"] == job_id for item in listed.json()))

        detail = self.client.get(f"/api/v1/fine-tuning/jobs/{job_id}")
        detail.raise_for_status()
        detail_payload = detail.json()
        self.assertEqual(detail_payload["job"]["id"], job_id)
        self.assertTrue(detail_payload["dataset_preview"])

    def test_fine_tune_job_launch_runs_mock_training_and_records_artifact(self) -> None:
        user_id, _, commit, _ = create_full_state(self.client)
        previous_mock_flag = os.environ.get("LAIVER_FINE_TUNE_MOCK")
        os.environ["LAIVER_FINE_TUNE_MOCK"] = "1"
        try:
            created = self.client.post(
                "/api/v1/fine-tuning/jobs",
                json={
                    "user_id": user_id,
                    "import_id": commit["import_job"]["id"],
                    "name": "Mock Tune",
                    "source_speaker": "Assistant",
                    "backend": "local_lora",
                    "base_model": "mock://qwen-mini",
                },
            )
            created.raise_for_status()
            job_id = created.json()["job"]["id"]

            launched = self.client.post(f"/api/v1/fine-tuning/jobs/{job_id}/launch?wait=true")
            launched.raise_for_status()
            launched_payload = launched.json()

            self.assertEqual(launched_payload["status"], "completed")
            self.assertTrue(launched_payload["artifact_path"])
            self.assertTrue(Path(launched_payload["artifact_path"]).exists())
            self.assertTrue((Path(launched_payload["output_dir"]) / "training_plan.json").exists())
            self.assertTrue((Path(launched_payload["output_dir"]) / "training_result.json").exists())

            detail = self.client.get(f"/api/v1/fine-tuning/jobs/{job_id}")
            detail.raise_for_status()
            detail_payload = detail.json()
            self.assertEqual(detail_payload["job"]["status"], "completed")
            self.assertTrue(detail_payload["job"]["artifact_path"])
            self.assertIsNotNone(detail_payload["registered_provider"])
            self.assertEqual(detail_payload["registered_provider"]["provider_type"], "local_adapter")
            self.assertEqual(detail_payload["job"]["registered_provider_id"], detail_payload["registered_provider"]["id"])
        finally:
            if previous_mock_flag is None:
                os.environ.pop("LAIVER_FINE_TUNE_MOCK", None)
            else:
                os.environ["LAIVER_FINE_TUNE_MOCK"] = previous_mock_flag

    def test_agent_can_use_registered_local_adapter_provider_as_default(self) -> None:
        user_id, _, commit, persona = create_full_state(self.client)
        previous_mock_flag = os.environ.get("LAIVER_FINE_TUNE_MOCK")
        os.environ["LAIVER_FINE_TUNE_MOCK"] = "1"
        try:
            created = self.client.post(
                "/api/v1/fine-tuning/jobs",
                json={
                    "user_id": user_id,
                    "import_id": commit["import_job"]["id"],
                    "name": "Local Adapter Runtime",
                    "source_speaker": "Assistant",
                    "backend": "local_lora",
                    "base_model": "mock://qwen-mini",
                },
            )
            created.raise_for_status()
            job_id = created.json()["job"]["id"]

            launched = self.client.post(f"/api/v1/fine-tuning/jobs/{job_id}/launch?wait=true")
            launched.raise_for_status()

            detail = self.client.get(f"/api/v1/fine-tuning/jobs/{job_id}")
            detail.raise_for_status()
            provider = detail.json()["registered_provider"]
            self.assertIsNotNone(provider)

            promoted = self.client.patch(
                f"/api/v1/model-providers/{provider['id']}",
                json={"is_default": True},
            )
            promoted.raise_for_status()
            self.assertEqual(promoted.json()["provider_type"], "local_adapter")

            warmed = self.client.post(f"/api/v1/model-providers/{provider['id']}/warm")
            warmed.raise_for_status()
            self.assertEqual(warmed.json()["status"], "mock_ready")
            self.assertTrue(warmed.json()["resident"])

            response = self.client.post(
                "/api/v1/agent/respond",
                json={
                    "user_id": user_id,
                    "persona_id": persona["persona"]["id"],
                    "message": "Reply in the currently selected local model voice.",
                    "controls": {
                        "skills_enabled": False,
                        "memory_write_enabled": False,
                    },
                },
            )
            response.raise_for_status()
            payload = response.json()

            self.assertEqual(payload["debug"]["provider_name"], "local_adapter")
            self.assertEqual(payload["debug"]["model_mode"], "live")

            runtime_rows = self.client.get("/api/v1/model-providers/local-adapters/runtime")
            runtime_rows.raise_for_status()
            runtime = next(item for item in runtime_rows.json() if item["provider_id"] == provider["id"])
            self.assertGreaterEqual(runtime["request_count"], 1)
        finally:
            if previous_mock_flag is None:
                os.environ.pop("LAIVER_FINE_TUNE_MOCK", None)
            else:
                os.environ["LAIVER_FINE_TUNE_MOCK"] = previous_mock_flag

    def test_local_adapter_runtime_warm_and_evict_endpoints(self) -> None:
        user_id, _, commit, _ = create_full_state(self.client)
        previous_mock_flag = os.environ.get("LAIVER_FINE_TUNE_MOCK")
        os.environ["LAIVER_FINE_TUNE_MOCK"] = "1"
        try:
            created = self.client.post(
                "/api/v1/fine-tuning/jobs",
                json={
                    "user_id": user_id,
                    "import_id": commit["import_job"]["id"],
                    "name": "Runtime Warm Check",
                    "source_speaker": "Assistant",
                    "backend": "local_lora",
                    "base_model": "mock://qwen-mini",
                },
            )
            created.raise_for_status()
            job_id = created.json()["job"]["id"]

            launched = self.client.post(f"/api/v1/fine-tuning/jobs/{job_id}/launch?wait=true")
            launched.raise_for_status()

            detail = self.client.get(f"/api/v1/fine-tuning/jobs/{job_id}")
            detail.raise_for_status()
            provider = detail.json()["registered_provider"]
            self.assertIsNotNone(provider)

            listed = self.client.get("/api/v1/model-providers/local-adapters/runtime")
            listed.raise_for_status()
            row = next(item for item in listed.json() if item["provider_id"] == provider["id"])
            self.assertEqual(row["status"], "idle")
            self.assertFalse(row["resident"])

            warmed = self.client.post(f"/api/v1/model-providers/{provider['id']}/warm")
            warmed.raise_for_status()
            self.assertEqual(warmed.json()["status"], "mock_ready")
            self.assertTrue(warmed.json()["resident"])

            evicted = self.client.post(f"/api/v1/model-providers/{provider['id']}/evict")
            evicted.raise_for_status()
            self.assertEqual(evicted.json()["status"], "idle")
            self.assertFalse(evicted.json()["resident"])
        finally:
            if previous_mock_flag is None:
                os.environ.pop("LAIVER_FINE_TUNE_MOCK", None)
            else:
                os.environ["LAIVER_FINE_TUNE_MOCK"] = previous_mock_flag

    def test_local_adapter_runtime_auto_evicts_when_idle_ttl_is_zero(self) -> None:
        previous_mock_flag = os.environ.get("LAIVER_FINE_TUNE_MOCK")
        os.environ["LAIVER_FINE_TUNE_MOCK"] = "1"
        tempdir = TEST_RUN_ROOT / f"idle-evict-{uuid.uuid4().hex}"
        tempdir.mkdir(parents=True, exist_ok=True)
        client = build_client(
            tempdir / "test.db",
            extra_env={
                "LOCAL_ADAPTER_IDLE_TTL_SECONDS": "0",
                "LOCAL_ADAPTER_CLEANUP_INTERVAL_SECONDS": "0",
            },
        )
        client.__enter__()
        try:
            user_id, _, commit, _ = create_full_state(client)
            created = client.post(
                "/api/v1/fine-tuning/jobs",
                json={
                    "user_id": user_id,
                    "import_id": commit["import_job"]["id"],
                    "name": "Zero TTL Runtime",
                    "source_speaker": "Assistant",
                    "backend": "local_lora",
                    "base_model": "mock://qwen-mini",
                },
            )
            created.raise_for_status()
            job_id = created.json()["job"]["id"]
            client.post(f"/api/v1/fine-tuning/jobs/{job_id}/launch?wait=true").raise_for_status()

            detail = client.get(f"/api/v1/fine-tuning/jobs/{job_id}")
            detail.raise_for_status()
            provider = detail.json()["registered_provider"]

            warmed = client.post(f"/api/v1/model-providers/{provider['id']}/warm")
            warmed.raise_for_status()
            self.assertTrue(warmed.json()["resident"])

            listed = client.get("/api/v1/model-providers/local-adapters/runtime")
            listed.raise_for_status()
            runtime = next(item for item in listed.json() if item["provider_id"] == provider["id"])
            self.assertFalse(runtime["resident"])
            self.assertEqual(runtime["status"], "idle")
            self.assertEqual(runtime["last_eviction_reason"], "idle_timeout")
            self.assertGreaterEqual(runtime["evict_count"], 1)
        finally:
            client.__exit__(None, None, None)
            shutil.rmtree(tempdir, ignore_errors=True)
            if previous_mock_flag is None:
                os.environ.pop("LAIVER_FINE_TUNE_MOCK", None)
            else:
                os.environ["LAIVER_FINE_TUNE_MOCK"] = previous_mock_flag

    def test_local_adapter_generation_timeout_returns_guarded_failure(self) -> None:
        previous_mock_flag = os.environ.get("LAIVER_FINE_TUNE_MOCK")
        os.environ["LAIVER_FINE_TUNE_MOCK"] = "1"
        tempdir = TEST_RUN_ROOT / f"timeout-{uuid.uuid4().hex}"
        tempdir.mkdir(parents=True, exist_ok=True)
        client = build_client(
            tempdir / "test.db",
            extra_env={
                "LOCAL_ADAPTER_GENERATE_TIMEOUT_SECONDS": "0.01",
            },
        )
        client.__enter__()
        try:
            user_id, _, commit, _ = create_full_state(client)
            created = client.post(
                "/api/v1/fine-tuning/jobs",
                json={
                    "user_id": user_id,
                    "import_id": commit["import_job"]["id"],
                    "name": "Timeout Runtime",
                    "source_speaker": "Assistant",
                    "backend": "local_lora",
                    "base_model": "mock://qwen-mini",
                },
            )
            created.raise_for_status()
            job_id = created.json()["job"]["id"]
            client.post(f"/api/v1/fine-tuning/jobs/{job_id}/launch?wait=true").raise_for_status()

            detail = client.get(f"/api/v1/fine-tuning/jobs/{job_id}")
            detail.raise_for_status()
            provider = detail.json()["registered_provider"]

            updated = client.patch(
                f"/api/v1/model-providers/{provider['id']}",
                json={
                    "settings": {
                        **provider["settings"],
                        "mock_latency_ms": 150,
                    }
                },
            )
            updated.raise_for_status()

            completion = client.post(
                "/api/v1/model-providers/complete",
                json={
                    "provider_id": provider["id"],
                    "messages": [
                        {"role": "user", "content": "Say hello after the timeout guard."}
                    ],
                    "temperature": 0,
                    "max_tokens": 32,
                },
            )
            completion.raise_for_status()
            payload = completion.json()

            self.assertEqual(payload["provider"], "local_adapter")
            self.assertEqual(payload["finish_reason"], "mock")
            self.assertIn("timeout", payload["content"].lower())
        finally:
            client.__exit__(None, None, None)
            shutil.rmtree(tempdir, ignore_errors=True)
            if previous_mock_flag is None:
                os.environ.pop("LAIVER_FINE_TUNE_MOCK", None)
            else:
                os.environ["LAIVER_FINE_TUNE_MOCK"] = previous_mock_flag

    def test_feishu_webhook_rejects_invalid_verification_token(self) -> None:
        user_id, _, _, _ = create_full_state(self.client)
        connector = create_connector(self.client, user_id)

        response = self.client.post(
            f"/api/v1/connectors/feishu/webhook/{connector['connector_id']}",
            json=build_feishu_webhook_payload(
                "This should be rejected.",
                verification_token="wrong-token",
            ),
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("verification token mismatch", response.text.lower())

    def test_duplicate_feishu_message_is_idempotent(self) -> None:
        user_id, _, _, _ = create_full_state(self.client)
        connector = create_connector(self.client, user_id)
        payload = build_feishu_webhook_payload(
            "Please remember that I prefer concise answers and practical steps.",
            message_id="msg_duplicate",
        )

        first = self.client.post(
            f"/api/v1/connectors/feishu/webhook/{connector['connector_id']}",
            json=payload,
        )
        first.raise_for_status()

        second = self.client.post(
            f"/api/v1/connectors/feishu/webhook/{connector['connector_id']}",
            json=payload,
        )
        second.raise_for_status()

        deliveries = self.client.get(f"/api/v1/connectors/{connector['connector_id']}/deliveries")
        deliveries.raise_for_status()

        self.assertEqual(len(deliveries.json()), 1)
        self.assertEqual(first.json()["connector_trace_id"], second.json()["connector_trace_id"])


if __name__ == "__main__":
    unittest.main()
