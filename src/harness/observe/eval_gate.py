"""Offline everyday gate. Live Ollama comparison is scripts/measure/eval_everyday.py --live."""

from __future__ import annotations

import json
from pathlib import Path

from harness.act.parse import parse_turn
from harness.paths import EVAL_DIR, REPO_ROOT
from harness.act.code import apply_source, write_and_run

ROOT = REPO_ROOT
EVAL = EVAL_DIR


def action_parse_rate(path: Path | None = None) -> tuple[int, int]:
    drafts = path or EVAL / "action_drafts.jsonl"
    ok = 0
    total = 0
    for line in drafts.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        total += 1
        turn = parse_turn(row["draft"])
        if turn and turn.action == row["action"]:
            ok += 1
    return ok, total


def held_out_run_pass(gold_dir: Path | None = None) -> tuple[int, int]:
    import tempfile

    gold = gold_dir or EVAL / "gold"
    ok = 0
    tasks = list((EVAL / "held_out").glob("*.json")) if (EVAL / "held_out").is_dir() else []
    if not tasks:
        return 0, 0
    for spec_path in tasks:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        script = gold / spec["script"]
        argv: list[str] = []
        for item in spec.get("argv") or []:
            cand = EVAL / str(item)
            argv.append(str(cand) if cand.exists() else str(item))
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / script.name
            result = write_and_run(
                script.read_text(encoding="utf-8"),
                dest,
                argv,
            )
        expected = spec["stdout"].strip()
        if result.code == 0 and result.stdout.strip() == expected:
            ok += 1
    return ok, len(tasks)


def bugfix_fixture_ready(project: Path | None = None) -> tuple[bool, str]:
    root = project or EVAL / "fixtures" / "nameerror_pkg"
    broken = root / "pkg" / "util_stats.py"
    gold = EVAL / "gold" / "util_stats.py"
    if not broken.is_file() or not gold.is_file():
        return False, "missing fixture or gold"
    if broken.stat().st_size < 1000:
        return False, f"{broken} is under 1 KB"
    original = broken.read_text(encoding="utf-8")
    if "tota" not in original or "return tota" not in original:
        return False, "fixture no longer has the NameError"
    apply_source(broken, gold.read_text(encoding="utf-8"), original=original)
    try:
        text = broken.read_text(encoding="utf-8")
        if "return total" not in text and "return sum(" not in text:
            return False, "gold apply did not fix the name"
    finally:
        broken.write_text(original, encoding="utf-8")
        bak = broken.with_suffix(broken.suffix + ".bak")
        if bak.is_file():
            bak.unlink()
    return True, "ok"
