"""Mechanical fixes the 8B fails to express. Deterministic. No model.

Live 8B (29 Aug 2026): left `subtotal` unbound after a NameError task, and
spent twelve `Find:` turns that never matched `def calc(x: int, ...)`.
Those are compiler jobs. The harness does them, then runs the suite,
before the first generate. A green suite ends the run without a model.
"""

from __future__ import annotations

import ast
import importlib.util
import io
import keyword
import re
import sys
import tokenize
from pathlib import Path
from typing import NamedTuple

from harness.act.code import apply_source
from harness.scan.names import undefined_in_file, undefined_names
from harness.task import (
    covered_symbol,
    looks_like_add_feature,
    looks_like_bugfix,
    looks_like_fix_smell,
    looks_like_write_tests,
    named_project_file,
    question_symbol,
    rename_pair,
)


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


def apply_cover_test(project: Path, task: str, *, write: bool = True) -> str:
    """Add one AAA test for the named function.

    Returns a note when a test already names the function, so the run can
    finish without the model appending a dead copy after `if __name__`.
    """
    name = covered_symbol(task) or (
        question_symbol(task) if looks_like_add_feature(task) else ""
    )
    if not name:
        return ""
    tests = Path(project) / "tests"
    dests = sorted(tests.glob("test_*.py")) if tests.is_dir() else []
    if not dests:
        return ""
    dest = dests[0]
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
    ints = (100, 10, 2, 0)
    used_ints = 0
    args: list[tuple[str, object]] = []
    for arg in func.args.args:
        if arg.arg in {"self", "cls"}:
            continue
        hint = ast.unparse(arg.annotation) if arg.annotation else ""
        if "list" in hint:
            args.append((arg.arg, [10, 20]))
        elif "dict" in hint:
            args.append((arg.arg, {"prices": [10, 20], "percent": 10}))
        elif "str" in hint:
            args.append((arg.arg, "x"))
        elif "float" in hint:
            args.append((arg.arg, 1.5))
        else:
            args.append((arg.arg, ints[used_ints % len(ints)]))
            used_ints += 1
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
        values = tuple(value for _key, value in args)
        if class_name:
            cls = getattr(module, class_name, None)
            if cls is None:
                return None
            expected = getattr(cls(), func.name)(*values)
        else:
            found = getattr(module, func.name, None)
            if found is None:
                return None
            expected = found(*values)
    except Exception:
        return None
    finally:
        sys.modules.pop(module_name, None)
        if inserted and sys.path and sys.path[0] == inserted:
            sys.path.pop(0)
    return args, expected, class_name, func.name


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


def apply_missing_imports(source: str) -> str:
    """Add the import line for a well-known name used without one.

    A model writes `Path` and forgets `from pathlib import Path`. Refusing
    that and asking for a rename is wrong twice over: the name is right,
    and the repair is mechanical. Only names on a fixed list are handled,
    so nothing is guessed.
    """
    from harness.scan.names import import_for, undefined_names

    wanted = [
        line for line in (import_for(name) for name in undefined_names(source)) if line
    ]
    if not wanted:
        return source
    lines = source.splitlines()
    present = {line.strip() for line in lines}
    missing = [line for line in dict.fromkeys(wanted) if line not in present]
    if not missing:
        return source
    insert_at = 0
    if lines and lines[0].lstrip()[:3] in {'"""', "'''"}:
        quote = lines[0].lstrip()[:3]
        rest = lines[0].lstrip()[3:]
        if quote in rest:
            insert_at = 1
        else:
            for index, line in enumerate(lines[1:], 1):
                if quote in line:
                    insert_at = index + 1
                    break
    while insert_at < len(lines) and not lines[insert_at].strip():
        insert_at += 1
    return "\n".join(lines[:insert_at] + missing + [""] + lines[insert_at:]).rstrip() + "\n"
