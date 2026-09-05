#!/usr/bin/env python3
"""Everyday-ready bar: harness 8B vs a clean 8B on this laptop.

  PYTHONPATH=src python scripts/measure/eval_everyday_bar.py

Live parse is the fifteen action_prompts.jsonl rows. The fix is
compute_total returning 0 in a ≥1 KB file — not a planted NameError.
Clean 8B means the same Ollama model with no AGENT_SYSTEM and no
agent loop (one-shot draft). Default twelve steps on the harness fix.
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

from finetune.agent_system import AGENT_SYSTEM  # noqa: E402
from finetune.everyday import DEFAULT_EVERYDAY_OLLAMA  # noqa: E402
from harness import Agent, AgentOptions  # noqa: E402
from harness.act.code import extract_python  # noqa: E402
from harness.act.parse import parse_turn  # noqa: E402
from harness.model.ollama_generate import OllamaGenerate  # noqa: E402

TASK = "fix compute_total in pkg/util_stats.py so it sums the rows"
FIXTURE = ROOT / "eval" / "fixtures" / "everyday_fix"
PROMPTS = ROOT / "eval" / "action_prompts.jsonl"
REPEATS = 3
STEPS = 12


def _prompts() -> list[dict]:
    return [
        json.loads(line)
        for line in PROMPTS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _parse(model: str, system: str) -> dict:
    backend = OllamaGenerate(model, system)
    if not backend.healthy():
        sys.exit(f"ollama {backend.host} is down")
    ok = 0
    rows = _prompts()
    for row in rows:
        draft = backend(row["prompt"])
        turn = parse_turn(draft)
        hit = bool(turn and turn.action == row["action"])
        ok += int(hit)
        print(
            json.dumps(
                {
                    "kind": "parse",
                    "system": "harness" if system else "clean",
                    "want": row["action"],
                    "got": turn.action if turn else None,
                    "ok": hit,
                }
            ),
            flush=True,
        )
    return {"ok": ok, "n": len(rows)}


def _suite_and_sum(project: Path) -> bool:
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        return False
    for name in list(sys.modules):
        if name == "pkg" or name.startswith("pkg."):
            del sys.modules[name]
    sys.path.insert(0, str(project))
    try:
        from pkg.util_stats import compute_total  # type: ignore

        return float(compute_total([1.0, 2.0, 3.0])) == 6.0
    except Exception:
        return False
    finally:
        if sys.path and sys.path[0] == str(project):
            sys.path.pop(0)
        for name in list(sys.modules):
            if name == "pkg" or name.startswith("pkg."):
                del sys.modules[name]


def _harness_fix(model: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp)
        shutil.copytree(FIXTURE, dest, dirs_exist_ok=True)
        result = Agent(
            AgentOptions(
                project=dest,
                task=TASK,
                model=model,
                keep_no_record=True,
                steps=STEPS,
            )
        ).run()
        ok = _suite_and_sum(dest)
        return {
            "ok": ok,
            "stopped": result.stopped,
            "writes": list(result.writes),
        }


def _clean_fix(model: str) -> dict:
    backend = OllamaGenerate(model, "")
    src = (FIXTURE / "pkg" / "util_stats.py").read_text(encoding="utf-8")
    draft = backend(
        "Fix compute_total so it sums the rows. Return only Python.\n\n" + src
    )
    extracted = extract_python(draft) or ""
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp)
        shutil.copytree(FIXTURE, dest, dirs_exist_ok=True)
        target = dest / "pkg" / "util_stats.py"
        if "def compute_total" in extracted and len(extracted) > 40:
            if extracted.lstrip().startswith(("import ", "from ", '"""')):
                target.write_text(extracted, encoding="utf-8")
            else:
                body = target.read_text(encoding="utf-8")
                start = body.find("def compute_total")
                end = body.find("\n\ndef ", start + 1)
                if start >= 0 and end > start:
                    target.write_text(body[:start] + extracted + body[end:], encoding="utf-8")
        ok = _suite_and_sum(dest)
        return {"ok": ok, "extracted": bool(extracted)}


def main() -> None:
    model = DEFAULT_EVERYDAY_OLLAMA
    if "--model" in sys.argv:
        model = sys.argv[sys.argv.index("--model") + 1]
    harness_parse = _parse(model, AGENT_SYSTEM)
    clean_parse = _parse(model, "")
    harness_fix = []
    clean_fix = []
    for _repeat in range(REPEATS):
        row = _harness_fix(model)
        harness_fix.append(row)
        print(json.dumps({"kind": "harness_fix", **row}), flush=True)
    for _repeat in range(REPEATS):
        row = _clean_fix(model)
        clean_fix.append(row)
        print(json.dumps({"kind": "clean_fix", **row}), flush=True)
    summary = {
        "model": model,
        "harness_parse": harness_parse,
        "clean_parse": clean_parse,
        "harness_fix": sum(int(row["ok"]) for row in harness_fix),
        "clean_fix": sum(int(row["ok"]) for row in clean_fix),
        "n_fix": REPEATS,
    }
    parse_beats = harness_parse["ok"] > clean_parse["ok"]
    fix_beats = summary["harness_fix"] > summary["clean_fix"]
    summary["everyday_ready"] = parse_beats and fix_beats
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
