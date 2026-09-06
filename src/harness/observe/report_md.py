"""Turn batch-review JSONL into markdown. No model. Not a second harness."""

from __future__ import annotations

import json
from pathlib import Path


def load_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _clean_review(text: str) -> str:
    first = (text or "").strip()
    if first.lower().startswith("no issue"):
        return "no issues"
    return first.split("\n", 1)[0].strip() or "(empty)"


def render_markdown(
    rows: list[dict],
    *,
    project: str,
    extra: dict | None = None,
) -> str:
    extra = extra or {}
    clean = 0
    flagged = 0
    applied = 0
    lines = [
        "# py-harness batch review",
        "",
        f"Project: `{project}`",
        "",
        "This file is **formatted from JSONL**. The 0.5B model reviewed one "
        "small `.py` file at a time. `PythonVibeGuard` only gates the draft "
        "(empty / keys / `curl|sh`). It does not judge review quality. "
        "There is no separate markdown harness.",
        "",
    ]
    if extra:
        bits = [f"{k}={v}" for k, v in extra.items()]
        lines.append("Run: " + ", ".join(bits))
        lines.append("")
    body: list[str] = ["| File | Bytes | Review | Applied |", "| --- | ---: | --- | --- |"]
    extras: list[str] = []
    for row in rows:
        review = str(row.get("review") or "")
        label = _clean_review(review)
        if label == "no issues":
            clean += 1
        else:
            flagged += 1
        if row.get("applied"):
            applied += 1
        rel = row.get("file", "")
        body.append(
            f"| `{rel}` | {row.get('bytes', '')} | {label} | "
            f"{'yes' if row.get('applied') else 'no'} |"
        )
        if "```" in review or (label == "no issues" and len(review) > 40):
            extras.append(
                f"### `{rel}`\n\nThe model said no issues but also emitted extra text "
                f"(ignored for apply).\n"
            )
    lines += [
        f"- Files: **{len(rows)}**",
        f"- Said no issues: **{clean}**",
        f"- Other review text: **{flagged}**",
        f"- Applied rewrites: **{applied}**",
        "",
        "## Files",
        "",
    ]
    lines.extend(body)
    if extras:
        lines += ["", "## Extra model text (not applied)", ""]
        lines.extend(extras)
    lines += [
        "",
        "## How to read this",
        "",
        "A hundred `no issues` on 200–350 byte `__init__.py` / constants / "
        "verifiers is the expected 0.5B outcome: the files are tiny re-exports. "
        "It is not a sign OpenSRE was audited. For a real review, open a module "
        "over ~1 KB with `--file` or raise `--min-bytes`.",
        "",
    ]
    return "\n".join(lines) + "\n"


def write_report(jsonl: Path, dest: Path, *, project: str, extra: dict | None = None) -> Path:
    dest.write_text(
        render_markdown(load_rows(jsonl), project=project, extra=extra),
        encoding="utf-8",
    )
    return dest
