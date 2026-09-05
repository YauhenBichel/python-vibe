#!/usr/bin/env python3
"""Greenfield GitHub-CLI job × three repeats on llama3.1:8b.

  PYTHONPATH=src python scripts/measure/eval_cli_app.py

Empty folder each time. The harness scaffolds pkg/ + tests/. Pass means
list, show, urllib, and mocked tests exist (score_cli_app list_show_ready).
"""

from __future__ import annotations

import json
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


def _run_one(model: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp)
        result = Agent(
            AgentOptions(
                project=dest,
                task=TASK,
                model=model,
                keep_no_record=True,
                steps=STEPS,
            )
        ).run()
        missing = [gap.key for gap in required_gaps(dest, TASK)]
        return {
            "ok": not missing,
            "missing": missing,
            "stopped": result.stopped,
            "writes": list(result.writes),
            "summary": result.summary[:160],
        }


def main() -> None:
    model = DEFAULT_EVERYDAY_OLLAMA
    if "--model" in sys.argv:
        model = sys.argv[sys.argv.index("--model") + 1]
    rows = []
    for _repeat in range(REPEATS):
        row = _run_one(model)
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
