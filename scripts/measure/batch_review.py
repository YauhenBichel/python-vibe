#!/usr/bin/env python3
"""Review (and optionally rewrite) up to 100 small first-party files.

Loads the LoRA once. Each file is its own prompt — the 0.5B window cannot
hold a repo.

  PYTHONPATH=src python scripts/measure/batch_review.py \\
    --project /path/to/your/app --limit 100

  # rewrite only files whose review was not "no issues"
  PYTHONPATH=src python scripts/measure/batch_review.py --project … --limit 100 --fix

Writes scratch/batch-review.jsonl. --fix keeps a .bak per file and refuses
a tiny overwrite. Do not run --fix on OpenSRE until you have read the report.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from harness.act.code import apply_source, extract_python, read_project_file  # noqa: E402
from harness.model.engine import make_generate  # noqa: E402
from harness.guard.fallbacks import PYTHON_VIBE_FALLBACK  # noqa: E402
from harness.scan.project_scan import list_small_py_files  # noqa: E402
from harness.observe.report_md import write_report  # noqa: E402
from harness.guard.python_vibe import PythonVibeGuard  # noqa: E402
from harness.guard.run import complete  # noqa: E402

REPORT = ROOT / "scratch" / "batch-review.jsonl"
REPORT_MD = ROOT / "scratch" / "batch-review.md"


def _clear_history(generate_once) -> None:
    history = getattr(generate_once, "history", None)
    if history is not None:
        history.clear()


def _ask(generate_once, prompt: str) -> str:
    _clear_history(generate_once)
    outcome = complete(generate_once, PythonVibeGuard(), PYTHON_VIBE_FALLBACK, prompt)
    return outcome.output or ""


def _review_prompt(rel: str, body: str) -> str:
    return (
        f"Review this project file. Path: {rel}\n"
        "List concrete bugs or crash risks only. If none, say: no issues.\n"
        "Do not rewrite the file.\n\n"
        f"```python\n{body}\n```\n"
    )


def _fix_prompt(rel: str, body: str, note: str) -> str:
    return (
        f"Edit this project file. {note}\n"
        f"Path: {rel}\n"
        "Reply with the complete new file in one ```python block. "
        "Keep the rest of the file.\n\n"
        f"```python\n{body}\n```\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--max-bytes", type=int, default=2500)
    parser.add_argument(
        "--min-bytes",
        type=int,
        default=200,
        help="skip empty __init__.py stubs (default 200)",
    )
    parser.add_argument("--engine", default="auto")
    parser.add_argument("--max-tokens", type=int, default=500)
    parser.add_argument(
        "--fix",
        action="store_true",
        help="rewrite files (after a review skip when it says no issues)",
    )
    parser.add_argument(
        "--note",
        default="keep behaviour; only fix a real crash or NameError",
    )
    args = parser.parse_args()
    project = args.project.expanduser().resolve()
    if not project.is_dir():
        sys.exit(f"not a directory: {project}")

    files = list_small_py_files(
        project,
        limit=args.limit,
        max_bytes=args.max_bytes,
        min_bytes=args.min_bytes,
    )
    if not files:
        sys.exit("no small first-party .py files (under --max-bytes, not in .venv)")

    label, generate_once = make_generate(args.engine, args.max_tokens)
    print(f"engine {label}  files {len(files)}  fix={args.fix}", file=sys.stderr)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("", encoding="utf-8")

    applied = 0
    skipped = 0
    for path in files:
        rel = str(path.relative_to(project))
        original = path.read_text(encoding="utf-8")
        body = read_project_file(path)
        review = _ask(generate_once, _review_prompt(rel, body)).strip()
        row: dict = {"file": rel, "bytes": path.stat().st_size, "review": review, "applied": False}
        no_issue = review.lower().startswith("no issue")
        if args.fix and not no_issue:
            draft = _ask(generate_once, _fix_prompt(rel, body, args.note))
            source = extract_python(draft)
            try:
                if not source:
                    raise ValueError("no python block")
                apply_source(path, source, original=original)
                row["applied"] = True
                applied += 1
                print(f"applied {rel}", file=sys.stderr)
            except ValueError as exc:
                row["apply_error"] = str(exc)
                skipped += 1
                print(f"skip {rel}: {exc}", file=sys.stderr)
        else:
            skipped += 1
            print(f"review {rel}: {review[:80].replace(chr(10), ' ')}", file=sys.stderr)
        with REPORT.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    write_report(
        REPORT,
        REPORT_MD,
        project=str(project),
        extra={"engine": label, "limit": args.limit, "fix": args.fix},
    )
    print(
        json.dumps(
            {
                "files": len(files),
                "applied": applied,
                "skipped": skipped,
                "report": str(REPORT),
                "markdown": str(REPORT_MD),
            }
        )
    )


if __name__ == "__main__":
    main()
