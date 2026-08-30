"""Resolving a merge conflict where keeping both sides is safe."""

from __future__ import annotations

"""Mechanical fixes the 8B fails to express. Deterministic. No model.

Live 8B (29 Aug 2026): left `subtotal` unbound after a NameError task, and
spent twelve `Find:` turns that never matched `def calc(x: int, ...)`.
Those are compiler jobs. The harness does them, then runs the suite,
before the first generate. A green suite ends the run without a model.
"""
import ast
from pathlib import Path
from harness.act.code import apply_source




CONFLICT_START = "<<<<<<< "


CONFLICT_MID = "======="


CONFLICT_END = ">>>>>>> "


def conflict_blocks(source: str) -> list[tuple[list[str], list[str]]]:
    """The two sides of every merge conflict in `source`."""
    blocks: list[tuple[list[str], list[str]]] = []
    lines = source.splitlines(keepends=True)
    index = 0
    while index < len(lines):
        if not lines[index].startswith(CONFLICT_START):
            index += 1
            continue
        index += 1
        ours: list[str] = []
        while index < len(lines) and lines[index].rstrip("\n") != CONFLICT_MID:
            ours.append(lines[index])
            index += 1
        index += 1
        theirs: list[str] = []
        while index < len(lines) and not lines[index].startswith(CONFLICT_END):
            theirs.append(lines[index])
            index += 1
        index += 1
        blocks.append((ours, theirs))
    return blocks


def resolve_keeping_both(source: str) -> str:
    """Merge every conflict by keeping both sides, or "" if that is unsafe.

    Two branches that each added something to the same file is the common
    case and the safe one: nothing is lost by keeping both. A conflict
    where one side is empty is a deletion against an edit, and which one
    is wanted is not something to guess at.

    Asked to resolve a real conflict, a live 8B spent twenty steps and
    left all three markers in place. Asked to resolve one in a file that
    had none, it reported the conflict resolved. Neither needed a model.
    """
    blocks = conflict_blocks(source)
    if not blocks:
        return ""
    if any(not "".join(ours).strip() or not "".join(theirs).strip()
           for ours, theirs in blocks):
        return ""
    out: list[str] = []
    lines = source.splitlines(keepends=True)
    index = 0
    while index < len(lines):
        if not lines[index].startswith(CONFLICT_START):
            out.append(lines[index])
            index += 1
            continue
        index += 1
        ours = []
        while lines[index].rstrip("\n") != CONFLICT_MID:
            ours.append(lines[index]); index += 1
        index += 1
        theirs = []
        while not lines[index].startswith(CONFLICT_END):
            theirs.append(lines[index]); index += 1
        index += 1
        out.extend(ours)
        # Two definitions need air between them; two import lines do not.
        if theirs and theirs[0].lstrip().startswith(("def ", "class ", "@")):
            out.append("\n\n")
        out.extend(theirs)
    merged = "".join(out)
    try:
        ast.parse(merged)
    except SyntaxError:
        return ""
    return merged


def looks_like_conflict(task: str) -> bool:
    """Whether the task is about a merge conflict."""
    lowered = task.lower()
    return "conflict" in lowered and any(
        word in lowered for word in ("merge", "resolve", "rebase", "<<<<")
    )


def _resolve_conflict(path: Path, rel: str, original: str, *, write: bool) -> str:
    """Keep both sides of every conflict in the file, or say what is there."""
    blocks = conflict_blocks(original)
    if not blocks:
        # Saying so is the point. Asked to resolve a conflict in a file
        # that had none, a live 8B reported the conflict resolved.
        return f"{rel} has no merge conflict in it. Nothing to resolve"
    merged = resolve_keeping_both(original)
    if not merged:
        return (
            f"{rel} has {len(blocks)} conflict(s) where one side is empty. "
            "That is a deletion against an edit, and which one you want is "
            "not something to guess"
        )
    if write:
        apply_source(path, merged, original=original)
    return f"kept both sides of {len(blocks)} conflict(s) in {rel}"
