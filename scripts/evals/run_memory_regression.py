from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = WORKSPACE_ROOT / "apps" / "api"
FIXTURE_PATH = WORKSPACE_ROOT / "docs" / "fixtures" / "mvp-e2e-chat.txt"
TEST_RUN_ROOT = WORKSPACE_ROOT / ".tmp" / "test-runs"

if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


@dataclass(frozen=True)
class EvalResult:
    name: str
    passed: bool
    checks: dict[str, bool]
    details: dict[str, Any]


def _clear_app_modules() -> None:
    db_session = sys.modules.get("app.db.session")
    if db_session is not None and hasattr(db_session, "engine"):
        db_session.engine.dispose()
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


def _build_client(tempdir: Path) -> TestClient:
    db_path = tempdir / "memory-regression.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ["AUTO_INIT_DB"] = "true"
    os.environ["COMMUNITY_SKILLS_DIR"] = (tempdir / "community-skills").as_posix()
    os.environ["FINE_TUNE_ARTIFACTS_DIR"] = (tempdir / "fine-tuning").as_posix()
    os.environ["LOCAL_ADAPTER_IDLE_TTL_SECONDS"] = "900"
    os.environ["LOCAL_ADAPTER_CLEANUP_INTERVAL_SECONDS"] = "60"
    os.environ["LOCAL_ADAPTER_GENERATE_TIMEOUT_SECONDS"] = "20"
    _clear_app_modules()

    from app.main import app

    return TestClient(app)


def _bootstrap(client: TestClient) -> str:
    user = client.post("/api/v1/users/bootstrap").json()["user"]
    client.post("/api/v1/model-providers/bootstrap").raise_for_status()
    client.post("/api/v1/skills/seed").raise_for_status()
    return user["id"]


def _create_persona(client: TestClient, user_id: str, *, name: str = "Memory Eval Persona") -> dict[str, Any]:
    sample = FIXTURE_PATH.read_text(encoding="utf-8")
    preview_response = client.post(
        "/api/v1/imports/preview",
        files={"file": ("mvp-e2e-chat.txt", sample, "text/plain")},
    )
    preview_response.raise_for_status()
    preview = preview_response.json()

    commit_response = client.post(
        "/api/v1/imports/commit",
        json={
            "user_id": user_id,
            "file_name": "mvp-e2e-chat.txt",
            "source_type": preview["source_type"],
            "file_size": len(sample.encode("utf-8")),
            "preview": {"total_messages": preview["total_messages"]},
            "normalized_messages": preview["normalized_messages"],
        },
    )
    commit_response.raise_for_status()
    commit = commit_response.json()

    persona_response = client.post(
        "/api/v1/personas/extract",
        json={
            "user_id": user_id,
            "import_id": commit["import_job"]["id"],
            "name": name,
            "persist": True,
            "set_default": True,
        },
    )
    persona_response.raise_for_status()
    return persona_response.json()["persona"]


def _assert_response(response: Any) -> dict[str, Any]:
    response.raise_for_status()
    return response.json()


def _post_memory(
    client: TestClient,
    *,
    user_id: str,
    persona_id: str,
    content: str,
    memory_type: str = "semantic",
    label: str = "preference",
    importance: float = 0.82,
    confidence: float = 0.8,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload_metadata = {
        "memory_label": label,
        "source": "memory-regression",
        "origin": "user_message",
        "state": "active",
    }
    if metadata:
        payload_metadata.update(metadata)
    return _assert_response(
        client.post(
            "/api/v1/memories",
            json={
                "user_id": user_id,
                "persona_id": persona_id,
                "memory_type": memory_type,
                "content": content,
                "importance_score": importance,
                "confidence_score": confidence,
                "metadata": payload_metadata,
            },
        )
    )


def _run_isolated(name: str, fn: Callable[[TestClient, str, dict[str, Any]], EvalResult]) -> EvalResult:
    tempdir = TEST_RUN_ROOT / f"memory-eval-{name}-{uuid.uuid4().hex}"
    tempdir.mkdir(parents=True, exist_ok=True)
    try:
        with _build_client(tempdir) as client:
            user_id = _bootstrap(client)
            persona = _create_persona(client, user_id, name=f"{name} Persona")
            return fn(client, user_id, persona)
    except Exception as exc:
        return EvalResult(
            name=name,
            passed=False,
            checks={"exception": False},
            details={"error": f"{type(exc).__name__}: {exc}"},
        )
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)


def _profile_preference_recall(client: TestClient, user_id: str, persona: dict[str, Any]) -> EvalResult:
    _post_memory(
        client,
        user_id=user_id,
        persona_id=persona["id"],
        content="I prefer concise answers with practical steps.",
    )
    _post_memory(
        client,
        user_id=user_id,
        persona_id=persona["id"],
        content="We briefly discussed release checklists in passing.",
        memory_type="session",
        label="session",
    )
    rows = _assert_response(
        client.post(
            "/api/v1/memories/search",
            json={
                "user_id": user_id,
                "persona_id": persona["id"],
                "query": "What style of response do I prefer?",
                "limit": 5,
            },
        )
    )
    top = rows[0] if rows else {}
    checks = {
        "has_results": bool(rows),
        "top_is_preference": top.get("metadata", {}).get("memory_label") == "preference",
        "top_mentions_concise": "concise answers" in top.get("content", "").lower(),
    }
    return EvalResult(
        name="profile_preference_recall",
        passed=all(checks.values()),
        checks=checks,
        details={"top_result": top, "result_count": len(rows)},
    )


def _episodic_recall(client: TestClient, user_id: str, persona: dict[str, Any]) -> EvalResult:
    _post_memory(
        client,
        user_id=user_id,
        persona_id=persona["id"],
        content="Last time we discussed the launch checklist and deployment timing.",
        memory_type="episodic",
        label="episodic",
    )
    _post_memory(
        client,
        user_id=user_id,
        persona_id=persona["id"],
        content="I prefer concise answers with practical steps.",
        label="preference",
    )
    rows = _assert_response(
        client.post(
            "/api/v1/memories/search",
            json={
                "user_id": user_id,
                "persona_id": persona["id"],
                "query": "What happened last time we talked about the launch?",
                "limit": 5,
            },
        )
    )
    top = rows[0] if rows else {}
    checks = {
        "has_results": bool(rows),
        "top_is_episodic": top.get("metadata", {}).get("memory_label") == "episodic",
        "top_mentions_launch": "launch checklist" in top.get("content", "").lower(),
    }
    return EvalResult(
        name="episodic_recall",
        passed=all(checks.values()),
        checks=checks,
        details={"top_result": top, "result_count": len(rows)},
    )


def _chat_grounding(client: TestClient, user_id: str, persona: dict[str, Any]) -> EvalResult:
    first = _assert_response(
        client.post(
            "/api/v1/agent/respond",
            json={
                "user_id": user_id,
                "persona_id": persona["id"],
                "message": "Please remember that I prefer concise answers and practical steps.",
            },
        )
    )
    second = _assert_response(
        client.post(
            "/api/v1/agent/respond",
            json={
                "user_id": user_id,
                "conversation_id": first["conversation_id"],
                "persona_id": persona["id"],
                "message": "What style of response do I prefer? Keep it practical.",
            },
        )
    )
    memory_hits = second["debug"]["memory_hits"]
    checks = {
        "first_wrote_memory": first["debug"]["memory_write_count"] >= 1,
        "used_memory_search": "memory-search" in second["debug"]["skills_used"],
        "answer_grounded": "concise answers" in second["response"].lower(),
        "hit_grounded": any(
            "concise answers" in item["content"].lower() or "practical steps" in item["content"].lower()
            for item in memory_hits
        ),
    }
    return EvalResult(
        name="chat_grounding",
        passed=all(checks.values()),
        checks=checks,
        details={
            "response": second["response"],
            "fallback_status": second["debug"]["fallback_status"],
            "memory_hits": memory_hits,
        },
    )


def _duplicate_reinforcement(client: TestClient, user_id: str, persona: dict[str, Any]) -> EvalResult:
    kwargs = {
        "client": client,
        "user_id": user_id,
        "persona_id": persona["id"],
        "content": "I prefer concise answers with practical steps.",
    }
    first = _post_memory(**kwargs)
    second = _post_memory(**kwargs)
    debug = _assert_response(client.get("/api/v1/memories/debug"))
    checks = {
        "same_memory_id": second["id"] == first["id"],
        "reinforcement_count_2": second["metadata"].get("reinforcement_count") == 2,
        "duplicate_count_2": second["metadata"].get("duplicate_count") == 2,
        "profile_updated": "concise answers with practical steps" in debug.get("profile_summary", "").lower(),
        "relationship_snapshot_present": bool(debug.get("relationship_state_snapshot")),
    }
    return EvalResult(
        name="duplicate_reinforcement",
        passed=all(checks.values()),
        checks=checks,
        details={"memory": second, "profile_summary": debug.get("profile_summary", "")},
    )


def _conflict_supersede(client: TestClient, user_id: str, persona: dict[str, Any]) -> EvalResult:
    first = _post_memory(
        client,
        user_id=user_id,
        persona_id=persona["id"],
        content="Always answer in a concise style.",
        label="instruction",
        importance=0.9,
        confidence=0.88,
        metadata={"fact_key": "answer style", "polarity": "positive"},
    )
    second = _post_memory(
        client,
        user_id=user_id,
        persona_id=persona["id"],
        content="Do not answer in a concise style.",
        label="instruction",
        importance=0.92,
        confidence=0.9,
        metadata={"fact_key": "answer style", "polarity": "negative"},
    )
    rows = _assert_response(client.get("/api/v1/memories"))
    first_row = next(item for item in rows if item["id"] == first["id"])
    second_row = next(item for item in rows if item["id"] == second["id"])
    debug = _assert_response(client.get("/api/v1/memories/debug"))
    profile_summary = debug.get("profile_summary", "").lower()
    checks = {
        "first_archived": first_row["metadata"].get("state") == "archived",
        "first_superseded_by_second": first_row["metadata"].get("superseded_by") == second["id"],
        "second_active": second_row["metadata"].get("state") == "active",
        "superseded_count": debug.get("lifecycle_counts", {}).get("superseded", 0) >= 1,
        "profile_contains_current": "do not answer in a concise style" in profile_summary,
        "profile_excludes_old": "always answer in a concise style" not in profile_summary,
    }
    return EvalResult(
        name="conflict_supersede",
        passed=all(checks.values()),
        checks=checks,
        details={"first": first_row, "second": second_row, "profile_summary": debug.get("profile_summary", "")},
    )


def _gated_candidate_approval(client: TestClient, user_id: str, persona: dict[str, Any]) -> EvalResult:
    memory = _post_memory(
        client,
        user_id=user_id,
        persona_id=persona["id"],
        content="I might prefer shorter answers when I am tired.",
        importance=0.62,
        confidence=0.58,
        metadata={"requires_review": True},
    )
    candidates = _assert_response(client.get("/api/v1/memories/candidates?status=pending&limit=10"))
    candidate = candidates[0] if candidates else {}
    approved = _assert_response(
        client.patch(
            f"/api/v1/memories/candidates/{candidate.get('id')}",
            json={"status": "approved", "reviewer_type": "memory-regression"},
        )
    )
    rows = _assert_response(client.get("/api/v1/memories"))
    refreshed = next(item for item in rows if item["id"] == memory["id"])
    checks = {
        "memory_pending_before_review": memory["metadata"].get("state") == "pending_review",
        "fact_write_gated": bool(memory["metadata"].get("fact_write_gated")),
        "candidate_pending": candidate.get("status") == "pending",
        "candidate_without_fact_before_review": candidate.get("proposed_value", {}).get("fact_id") is None,
        "candidate_approved": approved.get("status") == "approved",
        "approval_created_fact": bool(approved.get("proposed_value", {}).get("fact_id")),
        "memory_active_after_approval": refreshed["metadata"].get("state") == "active",
    }
    return EvalResult(
        name="gated_candidate_approval",
        passed=all(checks.values()),
        checks=checks,
        details={"memory_before": memory, "candidate": candidate, "approved": approved, "memory_after": refreshed},
    )


EVALS: dict[str, Callable[[TestClient, str, dict[str, Any]], EvalResult]] = {
    "profile_preference_recall": _profile_preference_recall,
    "episodic_recall": _episodic_recall,
    "chat_grounding": _chat_grounding,
    "duplicate_reinforcement": _duplicate_reinforcement,
    "conflict_supersede": _conflict_supersede,
    "gated_candidate_approval": _gated_candidate_approval,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Laiver memory regression evals.")
    parser.add_argument(
        "--case",
        action="append",
        choices=sorted(EVALS),
        help="Run only the selected case. Can be passed multiple times.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    args = parser.parse_args()

    selected = args.case or list(EVALS)
    results = [_run_isolated(name, EVALS[name]) for name in selected]
    passed = sum(1 for result in results if result.passed)
    payload = {
        "passed": passed,
        "failed": len(results) - passed,
        "total": len(results),
        "results": [
            {
                "name": result.name,
                "passed": result.passed,
                "checks": result.checks,
                "details": result.details,
            }
            for result in results
        ],
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        for result in results:
            status = "PASS" if result.passed else "FAIL"
            print(f"{status} {result.name}")
            for check, ok in result.checks.items():
                print(f"  {'ok' if ok else 'not ok'} {check}")
        print(json.dumps({"passed": passed, "failed": len(results) - passed, "total": len(results)}))

    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
