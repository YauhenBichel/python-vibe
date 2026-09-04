#!/usr/bin/env python3
"""Everyday explore / edit / run. Thin wrapper over `python -m harness run`.

The loop lives in `harness.agent`, not here, so the probe, the server and
this script all drive the same code.

  PYTHONPATH=src python3.13 scripts/run/agent.py --project /path/to/app \\
    "find a real NameError and fix it"
  PYTHONPATH=src python3.13 scripts/run/agent.py --project /path/to/app --brief

Writes stay under --project and go through PythonVibeGuard + .bak.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from finetune.everyday import (  # noqa: E402
    DEFAULT_EVERYDAY_OLLAMA,
    TINY_OLLAMA,
    is_tiny_model,
)
from harness.cli import _printer, _prompt_user  # noqa: E402
from harness import Agent, AgentOptions  # noqa: E402
from harness.scan.project_brief import classify_project, render_brief  # noqa: E402
from harness.skillkit.catalog import list_skills, render_catalog  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("task", nargs="?", default="")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--scope", default="")
    parser.add_argument("--brief", action="store_true")
    parser.add_argument("--skill", action="append", default=[], metavar="NAME")
    parser.add_argument(
        "--engine",
        default="ollama",
        help="ollama (local or OLLAMA_HOST), mlx, or openai (remote weights)",
    )
    parser.add_argument("--tiny", action="store_true")
    parser.add_argument("--model", default=DEFAULT_EVERYDAY_OLLAMA)
    parser.add_argument("--max-tokens", type=int, default=700)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--dry-run", dest="allow_writes", action="store_false")
    parser.add_argument(
        "--record",
        type=Path,
        help="write turns here instead of .python-vibe/traces.jsonl",
    )
    parser.add_argument(
        "--no-record",
        action="store_true",
        help="write no trace of this run",
    )
    args = parser.parse_args()

    project = args.project.expanduser().resolve()
    if not project.is_dir():
        sys.exit(f"not a directory: {project}")
    if args.brief:
        try:
            brief = classify_project(project, args.scope)
        except ValueError as exc:
            sys.exit(str(exc))
        print(render_brief(brief, scope=args.scope))
        print()
        print(render_catalog(list_skills(project)))
        return
    if not args.task:
        sys.exit("task required (or pass --brief)")
    if args.tiny:
        args.model, args.engine = TINY_OLLAMA, "ollama"
    if is_tiny_model(args.model) or args.engine == "mlx":
        print(
            "warning: 0.5B sidecar — expect missed Action: lines. "
            f"Everyday default is {DEFAULT_EVERYDAY_OLLAMA}.",
            file=sys.stderr,
        )

    options = AgentOptions(
        project=project,
        task=args.task,
        model=args.model,
        engine=args.engine,
        scope=args.scope,
        skills=tuple(args.skill),
        steps=args.steps,
        max_tokens=args.max_tokens,
        allow_writes=args.allow_writes,
        record=args.record,
        keep_no_record=args.no_record,
        on_event=_printer(True),
        on_question=_prompt_user if sys.stdin.isatty() else None,
    )
    try:
        result = Agent(options).run()
    except ValueError as exc:
        sys.exit(str(exc))
    print(result.summary)
    if not result.ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
