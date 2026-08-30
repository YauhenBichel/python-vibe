"""The repairs that run before any model turn, in order."""

from __future__ import annotations

"""Mechanical fixes the 8B fails to express. Deterministic. No model.

Live 8B (29 Aug 2026): left `subtotal` unbound after a NameError task, and
spent twelve `Find:` turns that never matched `def calc(x: int, ...)`.
Those are compiler jobs. The harness does them, then runs the suite,
before the first generate. A green suite ends the run without a model.
"""
from pathlib import Path
from harness.act.code import apply_source
from harness.task import (
    looks_like_add_feature,
    looks_like_bugfix,
    looks_like_fix_smell,
    looks_like_write_tests,
    named_project_file,
    rename_pair,
)

from harness.act.autofix.additions import (
    _impl_py,
    apply_add_function,
    apply_function_rename,
)
from harness.act.autofix.moves import apply_file_move
from harness.act.autofix.conflicts import _resolve_conflict, looks_like_conflict
from harness.act.autofix.cover import apply_cover_test
from harness.act.autofix.names import apply_typo_fixes, typo_pairs


def apply_mechanical(
    project: Path, task: str, rel: str, *, write: bool = True
) -> str:
    """Write a rename, unique typo, or missing AAA test. Return a note, or empty."""
    if not rel:
        rel = named_project_file(task, project)
    notes: list[str] = []
    path = Path(project) / rel if rel else None
    text = original = ""
    if path is not None and path.is_file():
        try:
            original = path.read_text(encoding="utf-8")
        except OSError:
            original = ""
        text = original
        if looks_like_fix_smell(task):
            old, new = rename_pair(task)
            if old and new:
                renamed = apply_function_rename(text, old, new)
                if renamed != text:
                    text = renamed
                    notes.append(f"renamed def {old} → def {new} in {rel}")
        if looks_like_bugfix(task):
            fixed = apply_typo_fixes(text)
            if fixed != text:
                pairs = typo_pairs(original)
                text = fixed
                shown = ", ".join(f"{bad} → {good}" for bad, good in pairs)
                notes.append(f"bound unique NameError typo ({shown}) in {rel}")
        if text != original and notes and write:
            apply_source(path, text, original=original)
    elif looks_like_bugfix(task):
        for dest, dest_rel in _impl_py(project):
            try:
                original = dest.read_text(encoding="utf-8")
            except OSError:
                continue
            fixed = apply_typo_fixes(original)
            if fixed == original:
                continue
            pairs = typo_pairs(original)
            if write:
                apply_source(dest, fixed, original=original)
            shown = ", ".join(f"{bad} → {good}" for bad, good in pairs)
            notes.append(f"bound unique NameError typo ({shown}) in {dest_rel}")
    if looks_like_add_feature(task):
        added = apply_add_function(project, task, write=write)
        if added:
            notes.append(added)
        cover = apply_cover_test(project, task, write=write)
        if cover:
            notes.append(cover)
    moved = apply_file_move(project, task, write=write)
    if moved:
        notes.append(moved)
    if path is not None and path.is_file() and looks_like_conflict(task):
        note = _resolve_conflict(path, rel, original, write=write)
        if note:
            notes.append(note)
    if looks_like_write_tests(task):
        cover = apply_cover_test(project, task, write=write)
        if cover:
            notes.append(cover)
    if not notes:
        return ""
    verb = "applied" if write else "would apply (read-only)"
    return (
        f"Harness {verb} a mechanical fix (no model):\n"
        + "\n".join(f"- {item}" for item in notes)
        + (
            "\nNext Action must be run Argv: -m unittest discover -s tests -q. "
            "Do not patch this file again."
            if write
            else "\nAction: done Summary: say what you would change and why."
        )
    )
