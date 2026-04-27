from __future__ import annotations

import json
import os
import shutil
import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = WORKSPACE_ROOT / "apps" / "api"
FIXTURE_PATH = WORKSPACE_ROOT / "docs" / "fixtures" / "mvp-e2e-chat.txt"
TEST_RUN_ROOT = WORKSPACE_ROOT / ".tmp" / "test-runs"

if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def _clear_app_modules() -> None:
    db_session = sys.modules.get("app.db.session")
    if db_session is not None and hasattr(db_session, "engine"):
        db_session.engine.dispose()
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


def main() -> int:
    tempdir = TEST_RUN_ROOT / f"regression-{uuid.uuid4().hex}"
    tempdir.mkdir(parents=True, exist_ok=True)
    try:
        db_path = tempdir / "regression.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
        os.environ["AUTO_INIT_DB"] = "true"
        _clear_app_modules()

        from app.main import app

        sample = FIXTURE_PATH.read_text(encoding="utf-8")

        with TestClient(app) as client:
            user = client.post("/api/v1/users/bootstrap").json()["user"]
            client.post("/api/v1/model-providers/bootstrap")
            client.post("/api/v1/skills/seed")

            preview = client.post(
                "/api/v1/imports/preview",
                files={"file": ("mvp-e2e-chat.txt", sample, "text/plain")},
            ).json()
            commit = client.post(
                "/api/v1/imports/commit",
                json={
                    "user_id": user["id"],
                    "file_name": "mvp-e2e-chat.txt",
                    "source_type": preview["source_type"],
                    "file_size": len(sample.encode("utf-8")),
                    "preview": {"total_messages": preview["total_messages"]},
                    "normalized_messages": preview["normalized_messages"],
                },
            ).json()
            persona = client.post(
                "/api/v1/personas/extract",
                json={
                    "user_id": user["id"],
                    "import_id": commit["import_job"]["id"],
                    "name": "Regression Persona",
                    "persist": True,
                    "set_default": True,
                },
            ).json()
            first = client.post(
                "/api/v1/agent/respond",
                json={
                    "user_id": user["id"],
                    "persona_id": persona["persona"]["id"],
                    "message": "Please remember that I prefer concise answers and practical steps.",
                },
            ).json()
            second = client.post(
                "/api/v1/agent/respond",
                json={
                    "user_id": user["id"],
                    "conversation_id": first["conversation_id"],
                    "persona_id": persona["persona"]["id"],
                    "message": "What style of response do I prefer? Keep it practical.",
                },
            ).json()

            connector = client.post(
                "/api/v1/connectors",
                json={
                    "user_id": user["id"],
                    "connector_type": "feishu",
                    "name": "Regression Connector",
                    "status": "active",
                    "config": {
                        "mode": "mock",
                        "delivery_mode": "webhook",
                        "verification_token": "local-test-token",
                        "reply_webhook_url": "",
                        "force_delivery_failure": False,
                    },
                    "metadata": {"source": "regression"},
                },
            ).json()
            connector_first = client.post(
                f"/api/v1/connectors/feishu/webhook/{connector['connector_id']}",
                json={
                    "header": {"token": "local-test-token"},
                    "event": {
                        "message": {
                            "message_id": "connector_msg_first",
                            "chat_id": "connector_chat_001",
                            "create_time": "1710752400000",
                            "message_type": "text",
                            "content": json.dumps(
                                {"text": "Please remember that I prefer concise answers and practical steps."},
                                ensure_ascii=False,
                            ),
                        },
                        "sender": {
                            "sender_id": {"open_id": "connector_user_001"},
                            "sender_name": "Connector Regression",
                        },
                    }
                },
            ).json()
            connector_second = client.post(
                f"/api/v1/connectors/feishu/webhook/{connector['connector_id']}",
                json={
                    "header": {"token": "local-test-token"},
                    "event": {
                        "message": {
                            "message_id": "connector_msg_second",
                            "chat_id": "connector_chat_001",
                            "create_time": "1710752460000",
                            "message_type": "text",
                            "content": json.dumps(
                                {"text": "What style of response do I prefer? Keep it practical."},
                                ensure_ascii=False,
                            ),
                        },
                        "sender": {
                            "sender_id": {"open_id": "connector_user_001"},
                            "sender_name": "Connector Regression",
                        },
                    }
                },
            ).json()
            connector_deliveries = client.get(
                f"/api/v1/connectors/{connector['connector_id']}/deliveries"
            ).json()
            connector_mappings = client.get(
                f"/api/v1/connectors/{connector['connector_id']}/mappings"
            ).json()

            summary = {
                "preview_total": preview["total_messages"],
                "commit_total": len(commit["normalized_messages"]),
                "first_memory_writes": first["debug"]["memory_write_count"],
                "first_skills_used": first["debug"]["skills_used"],
                "second_skills_used": second["debug"]["skills_used"],
                "second_response": second["response"],
                "second_fallback_status": second["debug"]["fallback_status"],
                "second_memory_hits": [item["content"] for item in second["debug"]["memory_hits"]],
                "recall_ok": any(
                    "concise answers" in item["content"].lower() or "practical steps" in item["content"].lower()
                    for item in second["debug"]["memory_hits"]
                ),
                "grounding_ok": "concise answers" in second["response"].lower()
                or "practical steps" in second["response"].lower(),
                "connector_first_delivery_status": connector_first["delivery_status"],
                "connector_second_delivery_status": connector_second["delivery_status"],
                "connector_mapping_count": len(connector_mappings),
                "connector_trace_ids": [item["trace"]["connector_trace_id"] for item in connector_deliveries[:2]],
                "connector_conversation_ids": [item["trace"]["mapped_conversation_id"] for item in connector_deliveries[:2]],
                "connector_same_conversation": len({item["trace"]["mapped_conversation_id"] for item in connector_deliveries[:2]}) == 1,
                "connector_recall_ok": "concise answers"
                in connector_deliveries[0]["outbound_response"]["content"]["text"].lower(),
            }
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)

    print(json.dumps(summary, ensure_ascii=False))

    if summary["preview_total"] != 7:
        return 1
    if summary["commit_total"] != 7:
        return 1
    if summary["first_memory_writes"] < 1:
        return 1
    if "memory-search" not in summary["first_skills_used"] and "memory-search" not in summary["second_skills_used"]:
        return 1
    if not summary["recall_ok"]:
        return 1
    if not summary["grounding_ok"]:
        return 1
    if summary["connector_first_delivery_status"] != "mock_delivered":
        return 1
    if summary["connector_second_delivery_status"] != "mock_delivered":
        return 1
    if summary["connector_mapping_count"] != 1:
        return 1
    if not summary["connector_same_conversation"]:
        return 1
    if not summary["connector_recall_ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
