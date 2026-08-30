#!/usr/bin/env python3
"""Everyday gate. Offline always; --live compares an Ollama model.

  PYTHONPATH=src python scripts/measure/eval_everyday.py
  PYTHONPATH=src python scripts/measure/eval_everyday.py --live --model llama3.1:8b

Do not claim everyday-ready until --live parse rate and /run pass beat the
same numbers for an untuned 8B on this machine.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from finetune.agent_system import AGENT_SYSTEM  # noqa: E402
from finetune.everyday import DEFAULT_EVERYDAY_OLLAMA, is_tiny_model  # noqa: E402
from harness.act.parse import parse_turn  # noqa: E402
from harness.observe.eval_gate import action_parse_rate, bugfix_fixture_ready, held_out_run_pass  # noqa: E402


def _offline() -> dict:
    parsed_ok, parsed_n = action_parse_rate()
    run_ok, run_n = held_out_run_pass()
    ready, reason = bugfix_fixture_ready()
    report = {
        "action_parse": {"ok": parsed_ok, "n": parsed_n},
        "held_out_gold_run": {"ok": run_ok, "n": run_n},
        "bugfix_fixture_1kb": {"ok": ready, "detail": reason},
    }
    print(json.dumps(report, indent=2))
    if parsed_n == 0 or parsed_ok < parsed_n:
        sys.exit("action parse fixtures failed")
    if run_n == 0 or run_ok < run_n:
        sys.exit("held-out gold /run failed")
    if not ready:
        sys.exit(reason)
    return report


def _live(model: str) -> None:
    from harness.model.ollama_generate import OllamaGenerate

    if is_tiny_model(model):
        print(f"warning: {model} is the 0.5B sidecar", file=sys.stderr)
    backend = OllamaGenerate(model, AGENT_SYSTEM)
    if not backend.healthy():
        sys.exit(f"ollama {backend.host} is down")
    drafts_path = ROOT / "eval" / "action_prompts.jsonl"
    if not drafts_path.is_file():
        sys.exit(f"missing {drafts_path}")
    ok = 0
    rows = [
        json.loads(line)
        for line in drafts_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for row in rows:
        draft = backend(row["prompt"])
        turn = parse_turn(draft)
        hit = bool(turn and turn.action == row["action"])
        ok += int(hit)
        print(
            json.dumps(
                {
                    "want": row["action"],
                    "got": turn.action if turn else None,
                    "ok": hit,
                }
            )
        )
    print(json.dumps({"live_parse": {"ok": ok, "n": len(rows), "model": model}}))
    if ok < max(1, len(rows) // 2):
        sys.exit(f"{model} parse rate {ok}/{len(rows)} below 50% — not everyday-ready")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--model", default=DEFAULT_EVERYDAY_OLLAMA)
    args = parser.parse_args()
    _offline()
    if args.live:
        _live(args.model)
    print("eval: pass")


if __name__ == "__main__":
    main()
