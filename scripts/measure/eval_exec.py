#!/usr/bin/env python3
"""Held-out execution eval: base vs LoRA vs LoRA+repair.

  PYTHONPATH=src python scripts/measure/eval_exec.py --variant all --repeats 3
  PYTHONPATH=src python scripts/measure/eval_exec.py --variant lora-repair --repeats 3 --task weekday

CI does not run this. Unit tests score the reference scripts only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from finetune.models import SPECS  # noqa: E402
from harness.memory import Conversation  # noqa: E402
from harness.model.engine import has_mlx, make_generate, mlx_pythons  # noqa: E402
from harness.observe.eval_loop import Score, run_repeats  # noqa: E402
from harness.observe.eval_tasks import all_tasks  # noqa: E402

VARIANTS = ("base", "base-repair", "lora", "lora-repair")


def _any_mlx() -> bool:
    return any(has_mlx(path) for path in mlx_pythons())


def _load(engine: str, variant: str, max_tokens: int):
    spec = SPECS["python-vibe"]
    adapters = variant.startswith("lora")
    if engine == "auto":
        engine = "mlx" if _any_mlx() else "ollama"
    if adapters and engine != "mlx":
        sys.exit("LoRA variants need --engine mlx (Ollama serves the untuned base)")
    memory = Conversation(system=spec.system)
    return make_generate(
        engine, max_tokens, memory=memory, adapters=adapters
    )


def _summarize(rows: list[Score]) -> dict[str, object]:
    by_task: dict[str, list[Score]] = defaultdict(list)
    for row in rows:
        by_task[row.task_id].append(row)
    tasks = {
        task_id: {
            "n": len(scores),
            "passed": sum(1 for s in scores if s.passed),
            "repaired": sum(1 for s in scores if s.repaired),
            "reasons": [s.reason for s in scores],
        }
        for task_id, scores in by_task.items()
    }
    return {
        "runs": len(rows),
        "passed": sum(1 for s in rows if s.passed),
        "tasks": tasks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=(*VARIANTS, "all"), default="all")
    parser.add_argument("--engine", choices=("auto", "mlx", "ollama"), default="auto")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=700)
    parser.add_argument("--task", action="append", help="run only these task ids")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "scratch" / "eval.jsonl",
        help="JSONL of every Score plus a final summary object",
    )
    args = parser.parse_args()

    wanted = set(args.task or [])
    tasks = [t for t in all_tasks() if not wanted or t.id in wanted]
    if wanted and len(tasks) != len(wanted):
        known = {t.id for t in all_tasks()}
        sys.exit(f"unknown task id(s): {sorted(wanted - known)}")

    variants = list(VARIANTS if args.variant == "all" else (args.variant,))
    if args.engine == "ollama" or (args.engine == "auto" and not _any_mlx()):
        skipped = [v for v in variants if v.startswith("lora")]
        variants = [v for v in variants if not v.startswith("lora")]
        if skipped:
            print(f"skipping {', '.join(skipped)} (need MLX)", flush=True)
        if not variants:
            sys.exit("LoRA variants need --engine mlx (Ollama serves the untuned base)")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    summaries = []
    with args.out.open("w", encoding="utf-8") as fh:
        for variant in variants:
            label, generate = _load(args.engine, variant, args.max_tokens)
            print(f"variant {variant} engine {label} tasks {len(tasks)} x{args.repeats}", flush=True)
            rows = []
            for row in run_repeats(
                tasks, generate, repair=variant.endswith("repair"), repeats=args.repeats
            ):
                rows.append(row)
                rec = {**row.__dict__, "variant": variant, "engine": label}
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
                mark = "ok" if row.passed else "fail"
                print(f"  {mark:4} {row.task_id:14} {row.reason}", flush=True)
            summary = {"variant": variant, "engine": label, **_summarize(rows)}
            summaries.append(summary)
            fh.write(json.dumps({"summary": True, **summary}, ensure_ascii=False) + "\n")
            print(
                f"  {summary['passed']}/{summary['runs']} passed",
                flush=True,
            )
    print(json.dumps(summaries, indent=2))
    print(f"wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
