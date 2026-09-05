#!/usr/bin/env python3
"""Greenfield GitHub-CLI job × three repeats on llama3.1:8b.

  PYTHONPATH=src python scripts/measure/eval_cli_app.py

Empty folder each time. The harness scaffolds pkg/ + tests/. Pass means
list, show, urllib, and mocked tests exist (score_cli_app list_show_ready).
Each row also records suite green and stopped. Default 12 steps.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from finetune.everyday import DEFAULT_EVERYDAY_OLLAMA  # noqa: E402
from harness import Agent, AgentOptions  # noqa: E402
from harness.scan.app_spec import required_gaps  # noqa: E402

TASK = "design and develop a small cli app for reviewing github PRs"
REPEATS = 3
STEPS = 12


def _run_one(model: str, steps: int) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp)
        result = Agent(
            AgentOptions(
                project=dest,
                task=TASK,
                model=model,
                keep_no_record=True,
                steps=steps,
            )
        ).run()
        missing = [gap.key for gap in required_gaps(dest, TASK)]
        suite = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
            cwd=dest,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        return {
            "ok": not missing,
            "missing": missing,
            "suite": suite.returncode == 0,
            "stopped": result.stopped,
            "writes": list(result.writes),
            "summary": result.summary[:160],
        }


def main() -> None:
    model = DEFAULT_EVERYDAY_OLLAMA
    steps = STEPS
    if "--model" in sys.argv:
        model = sys.argv[sys.argv.index("--model") + 1]
    if "--steps" in sys.argv:
        steps = int(sys.argv[sys.argv.index("--steps") + 1])
    rows = []
    for _repeat in range(REPEATS):
        row = _run_one(model, steps)
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    passed = sum(int(row["ok"]) for row in rows)
    print(
        json.dumps(
            {"model": model, "passed": passed, "n": len(rows)},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
