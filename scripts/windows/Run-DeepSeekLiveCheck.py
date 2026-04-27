from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def main() -> int:
    workspace_root = Path(__file__).resolve().parents[2]
    api_root = workspace_root / "apps" / "api"
    if str(api_root) not in sys.path:
        sys.path.insert(0, str(api_root))

    os.environ.setdefault("DATABASE_URL", "sqlite:///./apps/api/.tmp-deepseek-live.db")
    os.environ.setdefault("AUTO_INIT_DB", "true")

    from app.main import app

    with TestClient(app) as client:
        bootstrap = client.post("/api/v1/model-providers/bootstrap")
        bootstrap.raise_for_status()
        response = client.post("/api/v1/model-providers/validate", json={})
        response.raise_for_status()
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
