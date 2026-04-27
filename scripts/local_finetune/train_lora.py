from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _bootstrap_imports() -> None:
    workspace_root = Path(__file__).resolve().parents[2]
    api_root = workspace_root / "apps" / "api"
    if str(api_root) not in sys.path:
        sys.path.insert(0, str(api_root))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a local Laiver LoRA or QLoRA training job.")
    parser.add_argument("--job-config", required=True, help="Path to the exported fine-tune job config JSON.")
    args = parser.parse_args()

    config_path = Path(args.job_config)
    _bootstrap_imports()

    from app.services.local_fine_tune_runner import run_training_job

    result = run_training_job(config_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
