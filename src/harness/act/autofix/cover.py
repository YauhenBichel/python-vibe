"""Writing one test for a function, and choosing what to call it with."""

from __future__ import annotations

"""Mechanical fixes the 8B fails to express. Deterministic. No model.

Live 8B (29 Aug 2026): left `subtotal` unbound after a NameError task, and
spent twelve `Find:` turns that never matched `def calc(x: int, ...)`.
Those are compiler jobs. The harness does them, then runs the suite,
before the first generate. A green suite ends the run without a model.
"""
import ast
import importlib.util
import os
import re
import sys
from pathlib import Path
from harness.act.code import apply_source
from harness.task import (
    looks_like_file_operation,
    covered_symbol,
    looks_like_add_feature,
    named_project_file,
    question_symbol,
)



def _imports(source: str, name: str) -> bool:
    """Whether `source` brings `name` in by an import."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if (alias.asname or alias.name.split(".")[-1]) == name:
                    return True
    return False


def _test_file_for(
    task: str, project: Path, name: str, dests: list[Path]
) -> Path:
    """Which test file a new test for `name` belongs in.

    This used to be whichever file sorted first, so covering
    `ticket_job` from `ship/ticket.py` appended the test to
    `tests/test_agent_api.py`. It ran, it passed, and it was filed under
    something it has nothing to do with.

    In order: the file that already tests this symbol, the one named
    after the module the task points at, and only then the first.
    """
    for path in dests:
        try:
            body = path.read_text(encoding="utf-8")
        except OSError:
            continue
        # A test named after it, or a file that imports it. Merely
        # mentioning the name is not enough — a docstring in an unrelated
        # test file matched and sent the new test there — and a regex is
        # not enough either, because most of these imports are written
        # across several lines inside brackets.
        if re.search(rf"\bdef test_\w*{re.escape(name)}", body) or _imports(
            body, name
        ):
            return path
    named = named_project_file(task, project)
    if named:
        stem = Path(named).stem
        for path in dests:
            if path.stem in (f"test_{stem}", stem):
                return path
    return dests[0]


def apply_cover_test(project: Path, task: str, *, write: bool = True) -> str:
    """Add one AAA test for the named function.

    Returns a note when a test already names the function, so the run can
    finish without the model appending a dead copy after `if __name__`.
    """
    if looks_like_file_operation(task):
        # Nothing here is a symbol. Guessing one and finding it in some
        # test file is how "already has a test for create" happened.
        return ""
    name = covered_symbol(task) or (
        question_symbol(task) if looks_like_add_feature(task) else ""
    )
    if not name:
        return ""
    tests = Path(project) / "tests"
    dests = sorted(tests.glob("test_*.py")) if tests.is_dir() else []
    if not dests:
        return ""
    dest = _test_file_for(task, project, name, dests)
    body = dest.read_text(encoding="utf-8")
    safe = name.replace(".", "_")
    if name in body or f"def test_{safe}_" in body:
        return f"already has a test for {name}"
    impl = named_project_file(task, project)
    if not impl:
        from harness.skillkit.target import pick_module

        impl = pick_module(project, "", task)
    impl_path = Path(project) / impl if impl else None
    if impl_path is None or not impl_path.is_file():
        return ""
    if f"def {name}" not in impl_path.read_text(encoding="utf-8"):
        return ""
    sample = _sample_values(impl_path, name, project=Path(project))
    if sample is None:
        return ""
    args, expected, class_name, func_name = sample
    module = impl.replace("\\", "/").removesuffix(".py").replace("/", ".")
    imported = class_name or func_name
    names = ", ".join(key for key, _value in args)
    values = ", ".join(repr(value) for _key, value in args)
    assigns = f"{names} = {values}" if args else ""
    if class_name:
        holder = class_name[0].lower() + class_name[1:]
        act = (
            f"        {holder} = {class_name}()\n"
            + (f"        {assigns}\n" if assigns else "")
            + f"        got = {holder}.{func_name}({names})\n"
        )
    else:
        act = (
            (f"        {assigns}\n" if assigns else "")
            + f"        got = {func_name}({names})\n"
        )
    method = (
        f"    def test_{safe}_returns_the_expected_result(self) -> None:\n"
        f"{act}"
        f"        self.assertEqual(got, {expected!r})\n"
    )
    merged = _add_import_symbol(body, module, imported)
    merged = _append_class_method(merged, method)
    try:
        ast.parse(merged)
    except SyntaxError:
        return ""
    if write:
        apply_source(dest, merged, original=body)
    try:
        rel = dest.resolve().relative_to(Path(project).resolve()).as_posix()
    except ValueError:
        rel = dest.as_posix()
    return f"AAA test for {name} in {rel}"


def _find_callable(
    tree: ast.AST, name: str
) -> tuple[str, ast.FunctionDef] | None:
    """(class_name or "", function). Empty class_name is a module function."""
    cls_name, meth = name, ""
    if "." in name:
        cls_name, meth = name.split(".", 1)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name and not meth:
            return "", node
        if not isinstance(node, ast.ClassDef):
            continue
        if meth and node.name != cls_name:
            continue
        if not meth and node.name != name:
            if any(
                isinstance(item, ast.FunctionDef) and item.name == name
                for item in node.body
            ):
                item = next(
                    item
                    for item in node.body
                    if isinstance(item, ast.FunctionDef) and item.name == name
                )
                return node.name, item
            continue
        for item in node.body:
            if not isinstance(item, ast.FunctionDef):
                continue
            if meth and item.name == meth:
                return node.name, item
            if not meth and not item.name.startswith("_"):
                return node.name, item
    return None


MIN_SHARE_REACHED = 0.5


def _lines_reached(call, path: Path, first: int, last: int) -> int:
    """How many lines between `first` and `last` the call actually runs.

    A test built from an argument that returns on the first guard is a
    test of the guard. Counting what ran is the only way to tell that
    apart from a test that exercised the function.
    """
    seen: set[int] = set()
    # Compare real paths: a module loaded from /tmp reports /private/tmp
    # on macOS, and the tracer then matched nothing at all.
    target = os.path.realpath(path)

    def trace(frame, event, _arg):
        if os.path.realpath(frame.f_code.co_filename) != target:
            return None
        if event == "line" and first <= frame.f_lineno <= last:
            seen.add(frame.f_lineno)
        return trace

    previous = sys.gettrace()
    sys.settrace(trace)
    try:
        call()
    finally:
        sys.settrace(previous)
    return len(seen)


def _body_lines(func) -> int:
    """Executable lines in a function, not counting its docstring."""
    body = list(func.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    lines = set()
    for statement in body:
        for node in ast.walk(statement):
            if hasattr(node, "lineno"):
                lines.add(node.lineno)
    return len(lines) or 1


def _candidates(hint: str, arg_name: str, source: str) -> list[object]:
    """Values worth trying for one argument, best guess first.

    The string literals the module compares against are the ones that
    reach a branch: a function that checks `text == "yes"` is only
    exercised by "yes". A placeholder reaches the first return.
    """
    if "list" in hint:
        return [[10, 20], [], [1]]
    if "dict" in hint:
        return [{"prices": [10, 20], "percent": 10}, {}]
    if "float" in hint:
        return [1.5, 0.0]
    if "bool" in hint:
        return [True, False]
    if "int" in hint:
        return [2, 0, 100]
    if "str" in hint or not hint:
        literals = [
            node.value
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and 0 < len(node.value) <= 40
            and "\n" not in node.value
        ]
        seen, ordered = set(), []
        for value in literals:
            if value not in seen:
                seen.add(value)
                ordered.append(value)
        # Plain values first, so a literal only wins when it genuinely
        # reaches further into the function. A test reading `shout("x")`
        # is easier to follow than one reading `shout("!")`.
        return ["x", "", *ordered[:12]]
    return [2, 0]


def _sample_values(
    path: Path, name: str, *, project: Path | None = None
) -> tuple[list[tuple[str, object]], object, str, str] | None:
    """Call the function with simple args. None when that is not safe."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    found = _find_callable(tree, name)
    if found is None:
        return None
    class_name, func = found
    if func.args.kwonlyargs or func.args.vararg or func.args.kwarg:
        return None
    source = path.read_text(encoding="utf-8")
    choices: list[tuple[str, list[object]]] = []
    for arg in func.args.args:
        if arg.arg in {"self", "cls"}:
            continue
        hint = ast.unparse(arg.annotation) if arg.annotation else ""
        choices.append((arg.arg, _candidates(hint, arg.arg, source)))
    args: list[tuple[str, object]] = [
        (name, values[0]) for name, values in choices
    ]
    token = name.replace(".", "_")
    module_name = f"_vibe_cover_{token}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    inserted = ""
    if project is not None:
        inserted = str(Path(project).resolve())
        sys.path.insert(0, inserted)
    try:
        spec.loader.exec_module(module)
        if class_name:
            cls = getattr(module, class_name, None)
            if cls is None:
                return None
            target = getattr(cls(), func.name)
        else:
            target = getattr(module, func.name, None)
            if target is None:
                return None
        first = func.lineno
        last = func.end_lineno or func.lineno
        best_reach, best_args, expected = -1, args, None
        # Try one argument at a time against the first working set, and
        # keep whichever call runs the most of the function.
        for index, (arg_name, values) in enumerate(choices):
            for value in values[:8]:
                trial = list(args)
                trial[index] = (arg_name, value)
                shot = tuple(v for _k, v in trial)
                try:
                    reach = _lines_reached(
                        lambda: target(*shot), path, first, last
                    )
                    outcome = target(*shot)
                except Exception:
                    continue
                if reach > best_reach:
                    best_reach, best_args, expected = reach, trial, outcome
            if best_reach > 0:
                args = list(best_args)
        if best_reach < max(1, int(_body_lines(func) * MIN_SHARE_REACHED)):
            # Every value tried returned on a guard, so a test built from
            # this would asserts the guard rather than the function. Say
            # nothing rather than write a test that proves nothing.
            return None
    except Exception:
        return None
    finally:
        sys.modules.pop(module_name, None)
        if inserted and sys.path and sys.path[0] == inserted:
            sys.path.pop(0)
    return list(best_args), expected, class_name, func.name


def _add_import_symbol(text: str, module: str, name: str) -> str:
    if re.search(
        rf"from\s+{re.escape(module)}\s+import\s+.*\b{re.escape(name)}\b", text
    ):
        return text
    pattern = re.compile(rf"^(from\s+{re.escape(module)}\s+import\s+)(.+)$", re.M)
    match = pattern.search(text)
    if match:
        imported = match.group(2)
        if re.search(rf"\b{re.escape(name)}\b", imported):
            return text
        return text.replace(
            match.group(0), f"{match.group(1)}{imported.rstrip()}, {name}", 1
        )
    line = f"from {module} import {name}\n"
    if "import " in text:
        last = 0
        for hit in re.finditer(r"^(?:from\s+\S+\s+)?import\s+.+$", text, re.M):
            last = hit.end()
        return text[:last] + "\n" + line + text[last:]
    return line + text


def _append_class_method(text: str, method: str) -> str:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return text
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    if not classes:
        return text.rstrip() + (
            "\n\nclass TestGenerated(unittest.TestCase):\n" + method + "\n"
        )
    last = classes[-1]
    methods = [node for node in last.body if isinstance(node, ast.FunctionDef)]
    end = methods[-1].end_lineno if methods else last.end_lineno
    lines = text.splitlines(keepends=True)
    insert = method if method.startswith("\n") else "\n" + method
    if not insert.endswith("\n"):
        insert += "\n"
    lines.insert(end, insert)
    return "".join(lines)
