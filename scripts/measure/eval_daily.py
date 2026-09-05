#!/usr/bin/env python3
"""Three real daily jobs × three repeats on llama3.1:8b.

  PYTHONPATH=src python scripts/measure/eval_daily.py

Copies each fixture, runs Agent, checks the file and the suite.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from finetune.everyday import DEFAULT_EVERYDAY_OLLAMA  # noqa: E402
from harness import Agent, AgentOptions  # noqa: E402
from harness.skillkit.refuse_finish import tests_call  # noqa: E402

FIXTURES = ROOT / "eval" / "fixtures"
JOBS = (
    {
        "name": "write-tests",
        "fixture": "daily_cover",
        "task": "write tests for apply_discount in src/app.py",
        "check": "cover",
        "symbol": "apply_discount",
    },
    {
        "name": "add-function",
        "fixture": "daily_add",
        "task": "add a function clamp(value, lo, hi) that returns value limited to lo..hi, and a unit test",
        "check": "add",
        "symbol": "clamp",
    },
    {
        "name": "logic-bug",
        "fixture": "daily_logic",
        "task": "fix compute_total in src/app.py so it sums the rows",
        "check": "logic",
        "symbol": "compute_total",
    },
)
REPEATS = 3


def _suite_green(project: Path) -> bool:
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return proc.returncode == 0


def _passed(project: Path, job: dict) -> bool:
    if not _suite_green(project):
        return False
    symbol = job["symbol"]
    if job["check"] == "cover":
        return tests_call(project, symbol)
    if job["check"] == "add":
        body = (project / "src" / "app.py").read_text(encoding="utf-8")
        return f"def {symbol}" in body and tests_call(project, symbol)
    if job["check"] == "logic":
        sys.path.insert(0, str(project))
        try:
            from src.app import compute_total  # type: ignore

            return compute_total([1, 2]) == 3
        finally:
            if sys.path and sys.path[0] == str(project):
                sys.path.pop(0)
    return False


def _run_one(job: dict, model: str) -> dict:
    src = FIXTURES / job["fixture"]
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "app"
        shutil.copytree(src, dest)
        options = AgentOptions(
            project=dest,
            task=job["task"],
            model=model,
            keep_no_record=True,
            steps=12,
        )
        result = Agent(options).run()
        ok = _passed(dest, job)
        return {
            "job": job["name"],
            "ok": ok,
            "stopped": result.stopped,
            "summary": result.summary[:160],
        }


def main() -> None:
    model = DEFAULT_EVERYDAY_OLLAMA
    if "--model" in sys.argv:
        model = sys.argv[sys.argv.index("--model") + 1]
    rows = []
    for job in JOBS:
        for _repeat in range(REPEATS):
            row = _run_one(job, model)
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    by_job: dict[str, int] = {}
    for row in rows:
        by_job[row["job"]] = by_job.get(row["job"], 0) + int(row["ok"])
    passed = sum(int(row["ok"]) for row in rows)
    report = {
        "model": model,
        "passed": passed,
        "n": len(rows),
        "by_job": by_job,
    }
    print(json.dumps(report, indent=2))
    if passed < 6:
        print(
            f"{passed}/{len(rows)} — two of three jobs are not daily-ready",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
