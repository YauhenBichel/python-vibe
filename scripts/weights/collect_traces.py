#!/usr/bin/env python3
"""Run the tasks this project already has, and keep every turn.

  PYTHONPATH=src python scripts/weights/collect_traces.py --passes 3
  PYTHONPATH=src python scripts/weights/collect_traces.py --out /tmp/turns.jsonl

A run records its turns beside the project it ran in, which is right for
somebody working on their own code and useless for gathering training
data: the benchmark and the eval build a project in a temporary
directory and delete it afterwards, so every turn they produce goes with
it. Between them they hold thirty-three tasks that nobody has to invent,
and each run leaves about twenty turns.

This points the recording at one file that outlives the run. It changes
nothing about what is recorded — the same redaction applies, and a turn
carrying a secret is still dropped rather than written.
"""
from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "measure"))

from harness import Agent, AgentOptions  # noqa: E402
from harness.observe.eval_tasks import all_tasks  # noqa: E402

DEFAULT_OUT = ROOT / "data" / "agent-loop" / "collected.jsonl"


def bench_tasks() -> list[tuple[str, str, dict]]:
    """(id, task, files) for every benchmark case."""
    import bench  # noqa: PLC0415

    return [
        (case.key, case.task, {**bench.BASE, **case.files}) for case in bench.CASES
    ]


def eval_task_list() -> list[tuple[str, str, dict]]:
    """The held-out execution tasks, as the same shape."""
    return [
        (task.id, task.prompt, {name: body for name, body in task.files})
        for task in all_tasks()
    ]


def run_one(task: str, files: dict, record: Path, steps: int) -> int:
    """Run one task in a throwaway project. Returns turns added."""
    before = _line_count(record)
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        for rel, body in files.items():
            dest = project / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(body, encoding="utf-8")
        try:
            Agent(
                AgentOptions(
                    project=project, task=task, steps=steps, record=record
                )
            ).run()
        except Exception as exc:  # noqa: BLE001 - one bad task must not stop the rest
            print(f"    error: {str(exc)[:60]}", flush=True)
    return _line_count(record) - before


def _line_count(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for _ in path.open(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--passes", type=int, default=1)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    jobs = bench_tasks() + eval_task_list()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    print(f"{len(jobs)} tasks x {args.passes} pass(es) -> {args.out}", flush=True)
    started = time.time()
    for number in range(1, args.passes + 1):
        for key, task, files in jobs:
            added = run_one(task, files, args.out, args.steps)
            print(
                f"  pass {number} {key}: +{added} turn(s), "
                f"{_line_count(args.out)} total",
                flush=True,
            )
    print(
        f"{_line_count(args.out)} turns in {time.time() - started:.0f}s. "
        f"Build with: scripts/weights/build_agent_data.py",
        flush=True,
    )


if __name__ == "__main__":
    main()
