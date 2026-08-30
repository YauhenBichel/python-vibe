"""Repairing a name: a misspelling, or one only a person can settle."""

from __future__ import annotations

"""Mechanical fixes the 8B fails to express. Deterministic. No model.

Live 8B (29 Aug 2026): left `subtotal` unbound after a NameError task, and
spent twelve `Find:` turns that never matched `def calc(x: int, ...)`.
Those are compiler jobs. The harness does them, then runs the suite,
before the first generate. A green suite ends the run without a model.
"""
import ast
import io
import keyword
import tokenize
from pathlib import Path
from typing import NamedTuple
from harness.act.code import apply_source
from harness.scan.names import undefined_in_file, undefined_names
from harness.task import looks_like_bugfix, named_project_file




def levenshtein(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    prev = list(range(len(right) + 1))
    for i, char in enumerate(left, 1):
        cur = [i]
        for j, other in enumerate(right, 1):
            cur.append(
                min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (char != other))
            )
        prev = cur
    return prev[-1]


def _is_typo(bad: str, good: str) -> bool:
    if bad == good or good.startswith("__"):
        return False
    gap = abs(len(bad) - len(good))
    if gap > 2:
        return False
    distance = levenshtein(bad, good)
    if distance == 1:
        return True
    return distance == 2 and min(len(bad), len(good)) >= 6


def _class_body_ids(tree: ast.AST) -> set[int]:
    """Ids of method defs and class-body stores. Those names are not in scope
    inside a method body — counting them bound `stauts` to `status`.
    """
    found: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found.add(id(item))
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    for name in ast.walk(target):
                        if isinstance(name, ast.Name):
                            found.add(id(name))
            elif isinstance(item, ast.AnnAssign):
                found.add(id(item.target))
    return found


def _bound_in_scope(source: str) -> set[str]:
    """Names a method body can actually load: parameters and real locals."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return set()
    in_class_body = _class_body_ids(tree)
    bound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            if id(node) not in in_class_body:
                bound.add(node.id)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if id(node) not in in_class_body:
                bound.add(node.name)
            for arg in (
                *node.args.args,
                *node.args.posonlyargs,
                *node.args.kwonlyargs,
            ):
                bound.add(arg.arg)
    return bound


def _all_defined_names(source: str) -> set[str]:
    """Every name the file defines, including class-body methods."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            found.add(node.id)
        elif isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            found.add(node.name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for arg in (
                    *node.args.args,
                    *node.args.posonlyargs,
                    *node.args.kwonlyargs,
                ):
                    found.add(arg.arg)
    return found


def typo_pairs(source: str) -> list[tuple[str, str]]:
    """Unique undefined-name → nearby bound-name pairs."""
    leftover = undefined_names(source)
    if not leftover:
        return []
    bound = _bound_in_scope(source)
    pairs: list[tuple[str, str]] = []
    for bad in leftover:
        hits = [good for good in bound if _is_typo(bad, good)]
        if len(hits) == 1:
            pairs.append((bad, hits[0]))
    return pairs


class UnboundTypo(NamedTuple):
    """A leftover misspelling the harness must not guess at."""

    rel: str
    bad: str
    near: tuple[str, ...]


def unbound_typo(task: str, project: Path) -> UnboundTypo | None:
    """Named-file leftover typo with no unique in-scope bind, or None."""
    if not looks_like_bugfix(task):
        return None
    named = named_project_file(task, project)
    if not named:
        return None
    path = Path(project) / named
    leftover = undefined_in_file(path)
    if not leftover:
        return None
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if typo_pairs(source):
        return None
    known = _all_defined_names(source)
    for bad in leftover:
        near = tuple(sorted(name for name in known if _is_typo(bad, name)))
        if near:
            return UnboundTypo(named, bad, near)
    return None


def replacement_from_answer(
    answer: str, bound: set[str], forbidden: set[str]
) -> str | None:
    """Python text to put where the leftover name is. None if still unsafe.

    A Constant (`"ok"`, `None`, `200`) is taken as written. A Name that
    is in scope is bound. A Name that is only the method (`status`) is
    refused. A bare word that is not in scope is the string they typed,
    because the question was "what did you mean?", not "which name?".
    """
    text = answer.strip()
    if not text:
        return None
    if text.lower().startswith("return "):
        text = text[7:].strip()
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError:
        return None
    node = tree.body
    if isinstance(node, ast.Constant):
        return ast.unparse(node)
    if isinstance(node, ast.Name):
        if node.id in forbidden:
            return None
        if node.id in bound:
            return node.id
        if node.id.isidentifier() and not keyword.iskeyword(node.id):
            return ast.unparse(ast.Constant(node.id))
        return None
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        if node.value.id in bound:
            return ast.unparse(node)
        return None
    return None


def apply_person_bind(
    project: Path, task: str, answer: str, *, write: bool = True
) -> str:
    """Write the leftover typo as the person said. Empty if still unsafe."""
    found = unbound_typo(task, project)
    if found is None:
        return ""
    path = Path(project) / found.rel
    try:
        original = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    bound = _bound_in_scope(original)
    forbidden = {name for name in found.near if name not in bound}
    repl = replacement_from_answer(answer, bound, forbidden)
    if repl is None:
        return ""
    text = _rename_name_tokens(original, found.bad, repl)
    if text == original:
        return ""
    if write:
        try:
            apply_source(path, text, original=original)
        except ValueError:
            return ""
    return f"bound `{found.bad}` → {repl} in {found.rel} (your answer)"


def _rename_name_tokens(source: str, bad: str, good: str) -> str:
    """Replace `bad` where Python reads it as a name, and nowhere else.

    A plain search also rewrites the word inside strings and comments. An
    error message that mentions the misspelling is text the person wrote,
    and the harness has no business changing it.
    """
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return source
    lines = source.splitlines(keepends=True)
    spots = [
        token
        for token in tokens
        if token.type == tokenize.NAME and token.string == bad
    ]
    for token in reversed(spots):
        row = token.start[0] - 1
        line = lines[row]
        lines[row] = line[: token.start[1]] + good + line[token.end[1] :]
    return "".join(lines)


def apply_typo_fixes(source: str) -> str:
    text = source
    for bad, good in typo_pairs(source):
        text = _rename_name_tokens(text, bad, good)
    return text
