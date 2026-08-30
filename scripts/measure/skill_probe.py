#!/usr/bin/env python3
"""One-turn probe: how this model uses a skill. No writes.

Uses `harness.agent.prompt.build_preamble`, the same builder the real loop
uses, so what this measures is what the loop actually sends.

  PYTHONPATH=src python3.13 scripts/measure/skill_probe.py \\
    --project eval/fixtures/add_feature_pkg \\
    --skill add-feature "add a function multiply(a, b) and a unit test"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from finetune.everyday import DEFAULT_EVERYDAY_OLLAMA  # noqa: E402
from harness.act.parse import parse_turn_smart  # noqa: E402
from harness.agent.options import AgentOptions  # noqa: E402
from harness.agent.prompt import build_preamble  # noqa: E402
from harness.model.engine import make_generate  # noqa: E402
from harness.task import looks_like_question  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("task")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--scope", default="")
    parser.add_argument("--skill", action="append", default=[])
    parser.add_argument("--model", default=DEFAULT_EVERYDAY_OLLAMA)
    parser.add_argument("--max-tokens", type=int, default=400)
    parser.add_argument("--no-prelude", action="store_true")
    args = parser.parse_args()

    options = AgentOptions(
        project=args.project,
        task=args.task,
        scope=args.scope,
        skills=tuple(args.skill),
        model=args.model,
        max_tokens=args.max_tokens,
    )
    pre = build_preamble(options)
    prompt = pre.prompt
    if args.no_prelude and pre.pre_text:
        prompt = prompt.replace(f"{pre.pre_text}\n\n", "")
    _label, generate = make_generate(
        "ollama", args.max_tokens, model=args.model, system=options.system
    )
    draft = generate(prompt)
    turn = parse_turn_smart(draft, question=looks_like_question(args.task))
    print(
        json.dumps(
            {
                "model": args.model,
                "task": args.task,
                "skills": [item.name for item in pre.skills],
                "prelude": bool(pre.pre_text) and not args.no_prelude,
                "action": turn.action if turn else None,
                "path": turn.path if turn else "",
                "query": turn.query if turn else "",
                "append": bool(turn.append) if turn else False,
                "draft_head": (draft or "")[:240],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
