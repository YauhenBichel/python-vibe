"""Undefined-name scan. Deterministic compiler-style oracle. No model.

A small model will write `subtotl` next to `subtotal = ...` and then say
done. The existing test suite often does not call the broken function, so
`run` exits 0. This scan is the extra oracle: names that are loaded but
never bound, the way a compiler would complain.
"""

from __future__ import annotations

import ast
from pathlib import Path

def _builtin_names() -> set[str]:
    raw = __builtins__
    names = set(raw) if isinstance(raw, dict) else set(dir(raw))
    # Module dunders are bound by the interpreter, not by the source.
    return names | {
        "Ellipsis", "NotImplemented", "False", "None", "True",
        "__file__", "__name__", "__doc__", "__package__", "__spec__",
        "__loader__", "__builtins__", "__debug__",
    }


_BUILTINS = _builtin_names()


def _store_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    if isinstance(node, ast.Name):
        names.add(node.id)
    elif isinstance(node, (ast.Tuple, ast.List)):
        for child in node.elts:
            names.update(_store_names(child))
    elif isinstance(node, ast.Starred):
        names.update(_store_names(node.value))
    return names


def _assign_names(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Assign):
        names: set[str] = set()
        for target in node.targets:
            names.update(_store_names(target))
        return names
    if isinstance(node, ast.AnnAssign) and node.target:
        return _store_names(node.target)
    if isinstance(node, ast.AugAssign):
        return _store_names(node.target)
    if isinstance(node, ast.NamedExpr):
        return _store_names(node.target)
    if isinstance(node, (ast.For, ast.AsyncFor)):
        return _store_names(node.target)
    if isinstance(node, ast.withitem) and node.optional_vars:
        return _store_names(node.optional_vars)
    if isinstance(node, ast.ExceptHandler) and node.name:
        return {node.name}
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        found: set[str] = set()
        for alias in node.names:
            found.add(alias.asname or alias.name.split(".")[0])
        return found
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return {node.name}
    # `type Properties = dict[str, JsonValue]`, the 3.12 alias spelling.
    if isinstance(node, ast.TypeAlias):
        return _store_names(node.name)
    # `case InputSubmitted(text):` binds `text` for the branch body.
    if isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
        return {node.name}
    if isinstance(node, ast.MatchMapping) and node.rest:
        return {node.rest}
    return set()


def _argument_names(args: ast.arguments) -> set[str]:
    """Every parameter name a signature binds."""
    names = {
        arg.arg
        for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs)
    }
    if args.vararg:
        names.add(args.vararg.arg)
    if args.kwarg:
        names.add(args.kwarg.arg)
    return names


def _type_param_names(node: ast.AST) -> set[str]:
    """Names bound by PEP 695 type parameters: `def tool[F](...)`.

    Python 3.12 spelling, and the only place `F` or `T` is declared in a
    file that uses it. Without this they read as undefined, which was
    the largest group left in a real project after module scope was
    handled properly.
    """
    return {param.name for param in getattr(node, "type_params", []) or []}


def _function_bound(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    bound = {fn.name} | _argument_names(fn.args) | _type_param_names(fn)
    for node in ast.walk(fn):
        if node is fn:
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
            bound.update(_type_param_names(node))
        # A nested function or lambda binds its own parameters. Only their
        # names were collected, so every such parameter read looked
        # undefined: `item`, `text`, `prompt` across this project's own code.
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            bound.update(_argument_names(node.args))
        bound.update(_assign_names(node))
        if isinstance(node, ast.comprehension):
            bound.update(_store_names(node.target))
    return bound


def _module_scope_bound(tree: ast.Module) -> set[str]:
    """Every name module scope binds, including inside `if` and `try`.

    Only the top level of `tree.body` used to count, so the two most
    common shapes in typed and cross-platform code read as undefined:

        if TYPE_CHECKING:
            from rich.markdown import Markdown   # used in an annotation

        try:
            import termios                       # POSIX only
        except ImportError:
            termios = None

    Both run fine. On a sample of 600 files from a real project, 18 were
    reported as having an undefined name and these two shapes accounted
    for them. Function and class bodies are separate scopes and are not
    descended into.
    """
    bound: set[str] = set()

    def walk(body: list[ast.stmt]) -> None:
        for node in body:
            bound.update(_assign_names(node))
            bound.update(_type_param_names(node))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            for field in ("body", "orelse", "finalbody"):
                inner = getattr(node, field, None)
                if isinstance(inner, list):
                    walk([item for item in inner if isinstance(item, ast.stmt)])
            for handler in getattr(node, "handlers", []) or []:
                bound.update(_assign_names(handler))
                walk(handler.body)
            for item in getattr(node, "items", []) or []:
                bound.update(_assign_names(item))

    walk(tree.body)
    return bound


def undefined_names(source: str) -> list[str]:
    """Load-names in functions that are not bound in the module or the function."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    module_bound = set(_BUILTINS) | _module_scope_bound(tree)
    found: list[str] = []
    seen: set[str] = set()

    def scan(function: ast.AST, bound: set[str]) -> None:
        inner = bound | _function_bound(function)
        for child in ast.walk(function):
            if not isinstance(child, ast.Name) or not isinstance(child.ctx, ast.Load):
                continue
            if child.id in inner or child.id in seen:
                continue
            seen.add(child.id)
            found.append(child.id)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            scan(node, module_bound)
        elif isinstance(node, ast.ClassDef):
            # Methods were never scanned, and every unittest test is one.
            # A test calling a function it forgot to import looked clean.
            class_bound = set(module_bound)
            for member in node.body:
                class_bound.update(_assign_names(member))
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    class_bound.add(member.name)
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    scan(member, class_bound)
    return found


def new_undefined(original: str, draft: str) -> list[str]:
    """Undefined names the draft added. Existing planted bugs are ignored."""
    before = set(undefined_names(original))
    return [name for name in undefined_names(draft) if name not in before]


def undefined_in_file(path: Path) -> list[str]:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return []
    return undefined_names(source)


def _module_file(project: Path, dotted: str) -> Path | None:
    """The file a `from a.b import c` refers to, if it is in this project."""
    parts = dotted.split(".")
    for candidate in (
        project.joinpath(*parts).with_suffix(".py"),
        project.joinpath(*parts, "__init__.py"),
        project.joinpath(*parts[1:]).with_suffix(".py") if len(parts) > 1 else None,
    ):
        if candidate is not None and candidate.is_file():
            return candidate
    return None


def _defined_in(source: str) -> set[str]:
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return set()
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        names.update(_assign_names(node))
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
    return names


def missing_import_targets(project: Path, source: str) -> list[tuple[str, str]]:
    """Imports of names this project's own modules do not define.

    A test that imports a function nobody has written yet reads as valid
    Python — the import binds the name, so the undefined-name scan sees
    nothing — and fails only when the suite runs.
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    missing: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.level or not node.module:
            continue
        target = _module_file(Path(project), node.module)
        if target is None:
            continue
        try:
            defined = _defined_in(target.read_text(encoding="utf-8"))
        except OSError:
            continue
        for alias in node.names:
            if alias.name != "*" and alias.name not in defined:
                missing.append((node.module, alias.name))
    return missing


# Names a small model reaches for without importing them. The fix for
# these is an import line, never a rename.
_IMPORTABLE = {
    "Path": "from pathlib import Path",
    "PurePath": "from pathlib import PurePath",
    "dataclass": "from dataclasses import dataclass",
    "field": "from dataclasses import field",
    "Counter": "from collections import Counter",
    "defaultdict": "from collections import defaultdict",
    "Any": "from typing import Any",
    "Iterable": "from collections.abc import Iterable",
    "Sequence": "from collections.abc import Sequence",
    "Callable": "from collections.abc import Callable",
    "datetime": "from datetime import datetime",
    "date": "from datetime import date",
    "timedelta": "from datetime import timedelta",
    "os": "import os",
    "sys": "import sys",
    "re": "import re",
    "json": "import json",
    "csv": "import csv",
    "math": "import math",
    "shutil": "import shutil",
    "subprocess": "import subprocess",
    "tempfile": "import tempfile",
    "zipfile": "import zipfile",
    "tarfile": "import tarfile",
    "urllib": "import urllib.request",
    "unittest": "import unittest",
}


def import_for(name: str) -> str:
    """The import line that binds `name`, if it is one of the usual ones."""
    return _IMPORTABLE.get(name, "")
