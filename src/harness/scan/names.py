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


def _function_bound(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    bound = {fn.name} | _argument_names(fn.args)
    for node in ast.walk(fn):
        if node is fn:
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        # A nested function or lambda binds its own parameters. Only their
        # names were collected, so every such parameter read looked
        # undefined: `item`, `text`, `prompt` across this project's own code.
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            bound.update(_argument_names(node.args))
        bound.update(_assign_names(node))
        if isinstance(node, ast.comprehension):
            bound.update(_store_names(node.target))
    return bound


def undefined_names(source: str) -> list[str]:
    """Load-names in functions that are not bound in the module or the function."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    module_bound = set(_BUILTINS)
    for node in tree.body:
        module_bound.update(_assign_names(node))
        if isinstance(node, ast.ClassDef):
            module_bound.add(node.name)
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
