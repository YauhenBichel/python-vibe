"""Small vs large project brief. Deterministic. No model.

Small repos get a file list (comfortable daily explore / edit / run).
Large repos get a harness: map, --scope, do not read everything.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from harness.paths import TEXT_SUFFIXES, is_secret_name, rel_posix, suffix_globs
from harness.scan.project_scan import SKIP_DIR
from harness.task import (
    everyday_example_path,
    everyday_skill_name,
    looks_like_add_feature,
    looks_like_app_overflow,
    looks_like_everyday_code,
    looks_like_fix_smell,
    looks_like_merge,
    looks_like_new_package,
    looks_like_question,
    looks_like_ship,
    looks_like_ticket,
    looks_like_ticket_work,
    question_symbol,
)

SMALL_MAX_FILES = 40
SMALL_MAX_BYTES = 200_000
MAP_MAX_ENTRIES = 80


@dataclass(frozen=True)
class ProjectBrief:
    kind: str
    files: int
    bytes: int
    listed: tuple[tuple[str, int], ...]
    tops: tuple[tuple[str, int], ...]


def resolve_scope(project: Path, scope: str) -> Path:
    root = project.resolve()
    if not scope or scope in {".", "./"}:
        return root
    path = (root / scope).resolve() if not Path(scope).is_absolute() else Path(scope).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{path} is outside {root}") from exc
    if path.is_file():
        rel = path.relative_to(root)
        parent = rel.parent.as_posix() if rel.parent != Path(".") else "."
        raise ValueError(
            f"scope is a file ({rel}). Use Path: {rel} or Scope: {parent}"
        )
    if not path.is_dir():
        raise ValueError(f"scope is not a directory: {scope}")
    return path


def iter_text_files(project: Path, scope: str = "") -> list[tuple[Path, int]]:
    root = project.resolve()
    base = resolve_scope(project, scope) if scope else root
    found: list[tuple[Path, int]] = []
    for pattern in suffix_globs():
        for path in base.rglob(pattern):
            if not path.is_file():
                continue
            if any(part in SKIP_DIR for part in path.parts):
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if is_secret_name(path.name):
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            found.append((path, size))
    found.sort(key=lambda item: rel_posix(item[0], root))
    return found


def classify_project(project: Path, scope: str = "") -> ProjectBrief:
    root = project.resolve()
    found = iter_text_files(project, scope)
    total = sum(size for _path, size in found)
    listed = tuple(
        (rel_posix(path, root), size) for path, size in found[:SMALL_MAX_FILES]
    )
    counts: dict[str, int] = {}
    for path, _size in found:
        rel = path.relative_to(root)
        top = rel.parts[0] if len(rel.parts) > 1 else str(rel)
        counts[top] = counts.get(top, 0) + 1
    tops = tuple(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:16])
    kind = "small" if len(found) <= SMALL_MAX_FILES and total <= SMALL_MAX_BYTES else "large"
    return ProjectBrief(
        kind=kind,
        files=len(found),
        bytes=total,
        listed=listed,
        tops=tops,
    )


def _kb(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    return f"{n / 1024:.1f} KB"


def render_brief(brief: ProjectBrief, *, scope: str = "") -> str:
    header = (
        f"Mode: {brief.kind}  files={brief.files}  size={_kb(brief.bytes)}"
        + (f"  scope={scope}" if scope else "")
    )
    if brief.kind == "small":
        lines = [
            header,
            "Small project — explore, edit, and run on this laptop.",
            "You can read every listed file. Prefer Action: patch for one-line fixes.",
            "Questions: if you see # auto-read, Action: done. Else read one file, then done. Do not edit.",
            "Files:",
        ]
        for rel, size in brief.listed:
            lines.append(f"  {rel}  {_kb(size)}")
        return "\n".join(lines)
    lines = [
        header,
        "Large project — use the harness. Do not read the whole repo.",
        "Start with Action: map. Then Action: grep with a tight Query.",
        "Pass --scope <subdir> (or Action: map + Scope:) to stay inside one tree.",
        "Do not Action: done after one tiny __init__.py.",
        "Top-level (file counts):",
    ]
    for name, count in brief.tops:
        lines.append(f"  {name}/  {count}" if not name.endswith((".py", ".md")) else f"  {name}  {count}")
    return "\n".join(lines)


def render_brief_for_person(brief: ProjectBrief, *, scope: str = "") -> str:
    """The same facts, addressed to the person who typed the command.

    `render_brief` is written for the model: it ends in instructions like
    "Action: done". That is the first thing a new user sees, and to them it
    reads as noise, so the command line uses this instead.
    """
    size = _kb(brief.bytes)
    lines = [
        f"{brief.files} Python and Markdown files, {size} in total."
        + (f" Looking only at {scope}." if scope else ""),
    ]
    if brief.kind == "small":
        lines.append(
            "Small enough that python-vibe can read all of it, so you can "
            "ask about any part."
        )
    else:
        lines.append(
            "Large, so python-vibe will search rather than read everything. "
            "Add --scope <folder> to keep it in one place."
        )
    lines.append("")
    if brief.kind == "small":
        lines.append("Files:")
        for rel, item_size in brief.listed:
            lines.append(f"  {rel}  {_kb(item_size)}")
    else:
        lines.append("Top-level folders, by number of files:")
        for name, count in brief.tops:
            lines.append(f"  {name}  {count}")
    return "\n".join(lines)


def render_map(project: Path, scope: str = "", *, max_entries: int = MAP_MAX_ENTRIES) -> str:
    root = project.resolve()
    found = iter_text_files(project, scope)
    if not found:
        return "(no project text files in scope)"
    lines = [f"map {scope or '.'}  {len(found)} files  {_kb(sum(s for _p, s in found))}"]
    for path, size in found[:max_entries]:
        lines.append(f"  {rel_posix(path, root)}  {_kb(size)}")
    if len(found) > max_entries:
        lines.append(
            f"# … {len(found) - max_entries} more. Narrow Scope: or pass --scope"
        )
    return "\n".join(lines)


def start_hint(brief: ProjectBrief, task: str, *, located: bool = False) -> str:
    if looks_like_question(task) and located:
        return (
            "The harness already located the symbol. "
            "Action: done Summary: quote the -> type from the def line. "
            "Do not read, locate, grep, or edit."
        )
    if brief.kind == "large":
        return "Start with Action: map, then grep. Do not Action: done yet."
    if looks_like_question(task):
        symbol = question_symbol(task)
        if symbol:
            return (
                f"This is a question. First Action: grep Query: {symbol}. "
                "Then Action: read the file that defines it. "
                "Then Action: done with the answer. Do not edit unless asked."
            )
        return (
            "This is a question. Read what you need, then Action: done with the answer. "
            "Do not edit unless asked."
        )
    if looks_like_ticket(task) and (
        looks_like_ticket_work(task) or not looks_like_ship(task)
    ):
        return (
            "This is a ticket. The brief names Where and Job. "
            "Action: read that Path (or locate the symbol). Then do the Job. "
            "Commit / push / pr only if the task asked."
        )
    if looks_like_ship(task):
        if looks_like_merge(task):
            return (
                "This is a merge task. Action: merge Number: <pr>. No force."
            )
        return (
            "This is a ship task. Order: Action: issue Number: N → "
            "Action: branch Name: proceed/short-slug → patch → "
            "Action: commit Summary: why → Action: push → "
            "Action: pr Title: + Body: Closes #N. No force. Not main/master."
        )
    if looks_like_new_package(task):
        from harness.task import mentions_cli, mentions_http, package_noun

        noun = package_noun(task)
        shape = "argparse and one snake_case function" if mentions_cli(task) else "one snake_case function"
        http = (
            " urllib only — no curl. Token from the environment."
            if mentions_http(task)
            else ""
        )
        return (
            "This is a new-package task. First Action: edit Path: "
            f"pkg/{noun}.py with {shape}.{http} "
            f"Then tests/test_{noun}.py. Do not put logic in scripts/. "
            "pkg/__init__.py is already exports-only. Do not locate. Do not ask."
        )
    if looks_like_app_overflow(task):
        from harness.scan.app_spec import overflow_edit_line

        return (
            f"{overflow_edit_line(task)} Do not locate. Do not grep. Do not ask."
        )
    if looks_like_fix_smell(task):
        return (
            "This is a smell/rename task. Patch one opaque name to readable "
            "snake_case. Do not add features."
        )
    if looks_like_everyday_code(task):
        skill = everyday_skill_name(task) or "write-script"
        example = everyday_example_path(task)
        return (
            f"This is a {skill} task. First Action: edit Path: {example} "
            "with one function. urllib only — no curl. Then a test, then run."
        )
    if looks_like_add_feature(task):
        return (
            "This is an add-feature task. Grep first. If it is missing, add the "
            "smallest change plus a test, then run. Do not invent extras. "
            "Put new logic in pkg/<noun>.py, not __init__.py."
        )
    return "Start with Action: grep or Action: read. Prefer patch for one-line bugs."
