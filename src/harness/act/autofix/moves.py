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
import builtins
import re
from dataclasses import dataclass
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


# "move the function refuse_x out of a/b.py into a/c.py", and the same
# sentence with `from`/`to`. The function name comes first because that
# is how people write it; the two paths follow in source-then-
# destination order.
_MOVE_FUNCTION = re.compile(
    r"\bmove\b[^\w]*(?:the\s+)?(?:function\s+|def\s+)?"
    r"(?P<name>[A-Za-z_]\w*)\b(?!\.py)"
    r"[^\w/]*(?:\bout\s+of\b|\bfrom\b|\bin\b)[^\w/]*(?P<source>[\w./-]+\.py)\b"
    r".{0,24}?\b(?:into|to)\b[^\w/]*(?P<destination>[\w./-]+\.py)\b",
    re.I,
)


def function_move_targets(task: str) -> tuple[str, str, str] | None:
    """(name, source, destination) for a function move, or None."""
    found = _MOVE_FUNCTION.search(task)
    if not found:
        return None
    source, destination = found.group("source"), found.group("destination")
    if source == destination:
        return None
    return found.group("name"), source, destination


def _definition(tree: ast.Module, name: str) -> ast.stmt | None:
    """The top-level def or class of that name, decorators included."""
    for node in tree.body:
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ) and node.name == name:
            return node
    return None


def _span(node: ast.stmt, lines: list[str]) -> tuple[int, int]:
    """The line range to cut, counting decorators and the blank lines after."""
    start = node.lineno - 1
    for decorator in getattr(node, "decorator_list", []):
        start = min(start, decorator.lineno - 1)
    end = node.end_lineno or node.lineno
    while end < len(lines) and not lines[end].strip():
        end += 1
    return start, end


def _free_names(node: ast.stmt) -> set[str]:
    """Names the definition reads but does not create for itself.

    A function carried into another file keeps whatever it referred to,
    and the destination may not have it. Reporting that is the whole
    reason this refuses instead of writing half a move.
    """
    bound: set[str] = {node.name}
    for child in ast.walk(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bound.add(child.name)
            for arg in [
                *child.args.posonlyargs,
                *child.args.args,
                *child.args.kwonlyargs,
            ]:
                bound.add(arg.arg)
            for extra in (child.args.vararg, child.args.kwarg):
                if extra is not None:
                    bound.add(extra.arg)
        elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
            bound.add(child.id)
        elif isinstance(child, ast.alias):
            bound.add((child.asname or child.name).split(".")[0])
        elif isinstance(child, ast.ExceptHandler) and child.name:
            bound.add(child.name)
    used = {
        child.id
        for child in ast.walk(node)
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)
    }
    return {name for name in used - bound if not hasattr(builtins, name)}


def _already_there(tree: ast.Module, name: str) -> bool:
    return _definition(tree, name) is not None


@dataclass(frozen=True)
class _PlannedMove:
    """A function move that has passed every check and written nothing."""

    name: str
    source: Path
    source_before: str
    source_after: str
    destination: Path
    destination_before: str
    destination_after: str
    # (path, before, after) — `apply_source` keeps a .bak from the
    # original, so every write carries the text it replaces.
    edits: tuple[tuple[Path, str, str], ...]


def _plan_function_move(project: Path, task: str) -> _PlannedMove | None:
    """Work the move out in full, or return None. Writes nothing.

    Everything is decided here so that `apply_function_move` either
    writes a whole move or writes nothing at all. A half-applied move
    leaves a project that does not import.
    """
    targets = function_move_targets(task)
    if targets is None:
        return None
    name, source_rel, destination_rel = targets
    root = Path(project).resolve()
    source = resolve_project_file(project, source_rel)
    destination = resolve_project_file(project, destination_rel)
    if source is None or destination is None or not source.is_file():
        return None
    try:
        source_text = source.read_text(encoding="utf-8")
        source_tree = ast.parse(source_text)
        destination_text = (
            destination.read_text(encoding="utf-8") if destination.is_file() else ""
        )
        destination_tree = ast.parse(destination_text)
    except (OSError, SyntaxError):
        return None

    node = _definition(source_tree, name)
    if node is None or _already_there(destination_tree, name):
        return None
    # What the definition reads has to exist where it lands, or the move
    # produces a file that fails on first call.
    if any(
        free not in _module_level_names(destination_tree)
        for free in _free_names(node)
    ):
        return None

    lines = source_text.splitlines(keepends=True)
    first, last = _span(node, lines)
    body = "".join(lines[first:last]).rstrip("\n")
    source_after = "".join(lines[:first] + lines[last:])
    landed = destination_text.rstrip("\n")
    destination_after = f"{landed}\n\n\n{body}\n" if landed else f"{body}\n"
    for text in (source_after, destination_after):
        try:
            ast.parse(text)
        except SyntaxError:
            return None

    edits = _repointed_callers(
        project,
        name,
        module_name(rel_posix(source, root)),
        module_name(rel_posix(destination, root)),
        skip={source, destination},
    )
    if edits is None:
        return None
    return _PlannedMove(
        name,
        source,
        source_text,
        source_after,
        destination,
        destination_text,
        destination_after,
        edits,
    )


def _import_repaired(text: str, old_module: str, new_module: str, name: str) -> str:
    """Take one name out of an import and give it its own line. "" if absent.

    A real project does not write `from pkg.mod import one_name`. It
    writes a parenthesised list of ten, and a plain string replacement
    matches none of them: on this repository the first version moved the
    function and left every caller importing it from where it used to
    be, and the suite stopped loading.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return ""
    lines = text.splitlines(keepends=True)
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.module != old_module:
            continue
        kept = [alias for alias in node.names if alias.name != name]
        if len(kept) == len(node.names):
            continue
        first, last = node.lineno - 1, node.end_lineno or node.lineno
        replacement = f"from {new_module} import {name}\n"
        if kept:
            spelled = ", ".join(
                a.name if not a.asname else f"{a.name} as {a.asname}" for a in kept
            )
            one_line = f"from {old_module} import {spelled}\n"
            if len(one_line) > 80:
                joined = ",\n    ".join(
                    a.name if not a.asname else f"{a.name} as {a.asname}" for a in kept
                )
                one_line = f"from {old_module} import (\n    {joined},\n)\n"
            replacement = one_line + replacement
        return "".join(lines[:first]) + replacement + "".join(lines[last:])
    return ""


def _repointed_callers(
    project: Path, name: str, old_module: str, new_module: str, *, skip: set[Path]
) -> tuple[tuple[Path, str, str], ...] | None:
    """Files whose import of `name` must follow it. None if one breaks."""
    edits: list[tuple[Path, str, str]] = []
    for path in importers(project, old_module):
        if path in skip:
            continue
        original = path.read_text(encoding="utf-8")
        changed = _import_repaired(original, old_module, new_module, name)
        if not changed or changed == original:
            continue
        try:
            ast.parse(changed)
        except SyntaxError:
            return None
        edits.append((path, original, changed))
    return tuple(edits)


def _write_keeping_a_backup(path: Path, source: str) -> None:
    """Write a file that is deliberately shorter, and keep the original.

    `apply_source` refuses a draft two thirds the length of what it
    replaces, which is right when a model hands over a whole file and
    wrong here: taking a function out makes the source shorter on
    purpose. The backup is kept the same way, so nothing is lost and
    the honest-finish check can still see what changed.
    """
    ast.parse(source)
    backup = path.with_suffix(path.suffix + ".bak")
    if path.is_file():
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source.rstrip() + "\n", encoding="utf-8")


def apply_function_move(project: Path, task: str, *, write: bool = True) -> str:
    """Move the one function the task names, and repair its callers.

    Returns a note, or "" when the task asks for something else or the
    move cannot be made whole. Moving part of a file is the job people
    reach for once a module has grown too big, and doing it by hand
    means finding every caller by eye.
    """
    planned = _plan_function_move(project, task)
    if planned is None:
        return ""
    where = rel_posix(planned.destination, Path(project).resolve())
    if not write:
        return f"would move {planned.name} to {where}"
    _write_keeping_a_backup(planned.destination, planned.destination_after)
    _write_keeping_a_backup(planned.source, planned.source_after)
    for path, original, changed in planned.edits:
        apply_source(path, changed, original=original)
    repaired = (
        f", and repaired {len(planned.edits)} import(s)" if planned.edits else ""
    )
    return f"moved {planned.name} to {where}{repaired}"


def _module_level_names(tree: ast.Module) -> set[str]:
    """Everything a file defines or imports at the top level."""
    found: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            found.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                found.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    found.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            found.add(node.target.id)
    return found
