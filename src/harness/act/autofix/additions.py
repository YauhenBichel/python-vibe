"""Adding a small function, and appending rather than replacing."""

from __future__ import annotations

"""Mechanical fixes the 8B fails to express. Deterministic. No model.

Live 8B (29 Aug 2026): left `subtotal` unbound after a NameError task, and
spent twelve `Find:` turns that never matched `def calc(x: int, ...)`.
Those are compiler jobs. The harness does them, then runs the suite,
before the first generate. A green suite ends the run without a model.
"""
import ast
import re
from pathlib import Path
from harness.act.code import apply_source
from harness.task import (
    looks_like_add_feature,
    named_project_file,
    question_symbol,
)




def _top_level_names(tree: ast.Module) -> set[str]:
    """Names a module defines at its top level."""
    found: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            found.add(node.name)
        else:
            found.update(_assign_names_for_module(node))
    return found


def _assign_names_for_module(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Assign):
        names: set[str] = set()
        for target in node.targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
        return names
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return {node.target.id}
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return {alias.asname or alias.name.split(".")[0] for alias in node.names}
    return set()


def append_instead_of_replacing(original: str, draft: str) -> str:
    """Merge a short draft of new definitions onto the file, or "".

    `edit` replaces a whole file, so a correct new function sent on its
    own is shorter than what it would replace and is refused for that.
    A live 8B wrote a working `slugify`, had it thrown away twice — once
    for a missing fence, then for being 89 characters against 276 — and
    spent the rest of its budget sending the same correct code back.

    Appending is what it meant, and it is safe: nothing in the file is
    removed. Only when every top-level name in the draft is new, so this
    cannot quietly drop a rewrite of something that already exists.
    """
    if not original.strip() or not draft.strip():
        return ""
    if len(draft) >= max(40, (len(original) * 2) // 3):
        return ""  # long enough to be a real rewrite; leave it alone
    try:
        first, second = ast.parse(original), ast.parse(draft)
    except (SyntaxError, ValueError):
        return ""
    allowed = (
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
        ast.Import,
        ast.ImportFrom,
    )
    if not second.body or not all(isinstance(n, allowed) for n in second.body):
        return ""
    added = _top_level_names(second)
    if not added or added & _top_level_names(first):
        return ""
    merged = original.rstrip() + "\n\n\n" + draft.strip() + "\n"
    try:
        ast.parse(merged)
    except SyntaxError:
        return ""
    return merged


def apply_function_rename(source: str, old: str, new: str) -> str:
    """Rename one `def old` and `old(` calls. Keep the rest of the signature.

    Matching requires a call shape, so prose that merely mentions the name
    is left alone. Text inside a string that looks like a call is rewritten
    too; for a message naming the function that is usually wanted, and it
    is the same on every supported Python version, which a token-based
    rename would not be.
    """
    if not old or not new or old == new:
        return source
    if not re.search(rf"^def {re.escape(old)}\b", source, re.MULTILINE):
        return source
    if re.search(rf"^def {re.escape(new)}\b", source, re.MULTILINE):
        return source
    text = re.sub(
        rf"^def {re.escape(old)}\b",
        f"def {new}",
        source,
        count=1,
        flags=re.MULTILINE,
    )
    return re.sub(rf"\b{re.escape(old)}\s*\(", f"{new}(", text)


def _impl_py(project: Path) -> list[tuple[Path, str]]:
    """First-party Python files that are not tests, with project-relative paths."""
    from harness.scan.project_brief import iter_text_files

    root = Path(project).resolve()
    found: list[tuple[Path, str]] = []
    for path, _size in iter_text_files(root):
        if path.suffix != ".py":
            continue
        rel = path.resolve().relative_to(root).as_posix()
        if "test" in rel.lower():
            continue
        found.append((path, rel))
    return found


_COUNT_NAME = re.compile(r"(lines?|count|^n_)", re.I)


def usual_first_arg(source: str) -> tuple[str, str]:
    """Most common first parameter and its annotation, or empty strings."""
    found: list[tuple[str, str]] = []
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return "", ""
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        args = [a for a in node.args.args if a.arg not in {"self", "cls"}]
        if not args:
            continue
        hint = ast.unparse(args[0].annotation) if args[0].annotation else ""
        found.append((args[0].arg, hint))
    if not found:
        return "", ""
    name = max(set(item[0] for item in found), key=lambda n: sum(1 for a, _h in found if a == n))
    hints = [hint for arg, hint in found if arg == name and hint]
    hint = max(set(hints), key=hints.count) if hints else "list[int]"
    return name, hint


def apply_add_function(project: Path, task: str, *, write: bool = True) -> str:
    """Add a count function that matches its neighbors. Empty if unsure.

    Live 8B read `add a function total_lines` as a file-line counter and
    opened a path. In an orders module the usual argument is `prices`.
    """
    if not looks_like_add_feature(task):
        return ""
    symbol = question_symbol(task)
    if not symbol or not _COUNT_NAME.search(symbol):
        return ""
    from harness.skillkit.target import pick_module

    dest = named_project_file(task, project) or pick_module(project, "", task)
    if not dest:
        return ""
    path = Path(project) / dest
    if not path.is_file():
        return ""
    try:
        body = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    if re.search(rf"^def {re.escape(symbol)}\b", body, re.MULTILINE):
        return ""
    name, hint = usual_first_arg(body)
    if name != "prices" or "list" not in hint.lower():
        return ""
    stub = f"\n\ndef {symbol}({name}: {hint}) -> int:\n    return len({name})\n"
    merged = body.rstrip() + stub
    try:
        ast.parse(merged)
    except SyntaxError:
        return ""
    if write:
        apply_source(path, merged, original=body)
    return f"added def {symbol}({name}) in {dest}"
