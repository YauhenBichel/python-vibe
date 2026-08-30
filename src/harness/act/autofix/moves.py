"""Moving a file, and repairing what pointed at it.

Splitting a module, moving a helper to where it belongs and renaming a
file are ordinary work, and the harness could not do any of it. Asked to
move something it spent twenty steps and changed nothing.

The decision is usually already made by whoever asked — this file goes
there — so the work is mechanical, and mechanical work is what this
harness is good at. The part worth doing carefully is the imports: a
moved module leaves every `from pkg.old import name` pointing at
nothing, and asking a model to remember them all is how they get missed.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from harness.act.code import apply_source, resolve_project_file
from harness.paths import rel_posix

# "move a/b.py to c/d.py", "rename a/b.py to c/d.py"
_MOVE = re.compile(
    r"\b(?:move|rename)\b[^\w/]*([\w./-]+\.py)\b.{0,20}?\b(?:to|into|as)\b[^\w/]*([\w./-]+\.py)\b",
    re.I,
)


def move_targets(task: str) -> tuple[str, str] | None:
    """The two paths a move names, or None when it names fewer than two."""
    found = _MOVE.search(task)
    if not found:
        return None
    source, destination = found.group(1), found.group(2)
    if source == destination:
        return None
    return source, destination


# Folders a project puts its code under, which imports do not name.
# A file at src/pkg/mod.py is imported as pkg.mod, not src.pkg.mod.
IMPORT_ROOTS = ("src", "lib")


def module_names(rel: str) -> list[str]:
    """Every dotted name an import might use for this path.

    A file under `src/` is imported without the `src`, because that is
    what ends up on the path. Computing only the name relative to the
    project root meant a real move rewrote nothing: the file became
    `src.harness.observe.report_md` while every import said
    `harness.observe.report_md`.
    """
    parts = list(Path(rel).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return []
    names = [".".join(parts)]
    if parts[0] in IMPORT_ROOTS and len(parts) > 1:
        names.append(".".join(parts[1:]))
    return names


def module_name(rel: str) -> str:
    """The name an import is most likely to use for this path."""
    names = module_names(rel)
    return names[-1] if names else ""


def _rewritten(source: str, old: str, new: str) -> str:
    """`source` with every import of `old` pointing at `new` instead."""
    if not old or not new:
        return source
    text = re.sub(rf"(?<![\w.]){re.escape(old)}(?![\w])", new, source)
    return text


def importers(project: Path, old: str) -> list[Path]:
    """Files that name the module being moved."""
    root = Path(project).resolve()
    hits = []
    for path in sorted(root.rglob("*.py")):
        if any(part.startswith(".") or part == "__pycache__" for part in path.parts):
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if re.search(rf"(?<![\w.]){re.escape(old)}(?![\w])", body):
            hits.append(path)
    return hits


def apply_file_move(project: Path, task: str, *, write: bool = True) -> str:
    """Move the file the task names and repair the imports. "" if unsure.

    Everything is checked before anything is written: both paths stay
    inside the project, the source exists, the destination does not, and
    every file that would be rewritten still parses afterwards. A move
    that would leave the project unparseable is refused whole rather
    than half-applied.
    """
    targets = move_targets(task)
    if targets is None:
        return ""
    source_rel, destination_rel = targets
    try:
        source = resolve_project_file(project, source_rel)
        destination = resolve_project_file(project, destination_rel)
    except (ValueError, OSError):
        return ""
    if not source.is_file() or destination.exists():
        return ""

    root = Path(project).resolve()
    old_names = module_names(rel_posix(source, root))
    new_names = module_names(rel_posix(destination, root))
    if not old_names or len(old_names) != len(new_names):
        return ""

    edits: list[tuple[Path, str, str]] = []
    seen: set[Path] = set()
    for old_module, new_module in zip(old_names, new_names, strict=True):
        for path in importers(project, old_module):
            if path == source or path in seen:
                continue
            original = path.read_text(encoding="utf-8")
            changed = _rewritten(original, old_module, new_module)
            if changed == original:
                continue
            seen.add(path)
            try:
                ast.parse(changed)
            except SyntaxError:
                return ""
            edits.append((path, original, changed))

    body = source.read_text(encoding="utf-8")
    if not write:
        return (
            f"would move {source_rel} to {destination_rel} "
            f"and repair {len(edits)} file(s)"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(body, encoding="utf-8")
    source.unlink()
    for path, original, changed in edits:
        apply_source(path, changed, original=original)
    repaired = f", and repaired {len(edits)} import(s)" if edits else ""
    return f"moved {source_rel} to {destination_rel}{repaired}"
