"""Whether a run may say it is finished.

A different question from whether a change is acceptable. These look
at the project after the work, not at the draft before it: is the
symbol actually there, did a test run, does a test call what it was
asked to cover.
"""

from __future__ import annotations

# The oracle reuses one draft rule: a half-finished rename is a
# reason to refuse a finish as well as a draft.
from harness.skillkit.draft_rules import refuse_rename_incomplete

"""SoC / readable-name guards. Deterministic. No model."""
import ast
import re
from pathlib import Path
from harness.task import (
    looks_like_add_feature,
    looks_like_bugfix,
    looks_like_design_loop,
    covered_symbol,
    looks_like_everyday_code,
    looks_like_fix_smell,
    looks_like_write_tests,
    looks_like_new_package,
    looks_like_refactor,
    question_symbol,
    rename_pair,
)


def _a_test_uses(body: str, symbol: str) -> bool:
    """True when some `def test_...` in `body` actually mentions `symbol`.

    Asking only whether the name appears anywhere in the test files
    accepted a file holding one import line and nothing else. On a real
    module the run wrote exactly that, reported `done`, and `unittest
    discover` found no tests at all. An import is not coverage.
    """
    if not body.strip() or not symbol:
        return False
    try:
        tree = ast.parse(body)
    except (SyntaxError, ValueError):
        # Unparsable here means several files concatenated. Fall back to
        # requiring the name somewhere after a test definition.
        return bool(re.search(rf"def test_\w*[\s\S]*?\b{re.escape(symbol)}\b", body))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test"):
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and child.id == symbol:
                return True
            if isinstance(child, ast.Attribute) and child.attr == symbol:
                return True
    return False


def refuse_done_oracle(task: str, project: Path, last_path: str) -> str:
    """Refuse done when the named file or last write still has an unbound name."""
    from harness.scan.names import undefined_in_file
    from harness.task import named_project_file, rename_pair

    paths: list[str] = []
    named = named_project_file(task, project)
    if named:
        paths.append(named)
    if last_path and last_path not in paths:
        paths.append(last_path)
    if looks_like_bugfix(task):
        for rel in paths:
            leftover = undefined_in_file(Path(project) / rel)
            if leftover:
                return (
                    f"undefined name {leftover[0]} in {rel}. "
                    f"Action: patch Path: {rel} Find: {leftover[0]} "
                    "Replace: the name you assigned."
                )
    if looks_like_add_feature(task):
        symbol = question_symbol(task)
        if symbol:
            found = False
            root = Path(project)
            from harness.scan.project_brief import iter_text_files

            for path, _size in iter_text_files(root):
                if path.suffix != ".py":
                    continue
                try:
                    body = path.read_text(encoding="utf-8")
                except OSError:
                    continue
                if re.search(rf"^def {re.escape(symbol)}\b", body, re.MULTILINE):
                    found = True
                    break
            if not found:
                from harness.skillkit.target import pick_module

                dest = pick_module(root, last_path, task)
                return (
                    f"def {symbol} is not in the project. "
                    f"Action: patch Path: {dest} Append: def {symbol}(...)."
                )
    if looks_like_write_tests(task):
        symbol = covered_symbol(task)
        if symbol:
            tests = Path(project) / "tests"
            body = ""
            if tests.is_dir():
                for path in sorted(tests.glob("test_*.py")):
                    try:
                        body += path.read_text(encoding="utf-8")
                    except OSError:
                        continue
            if not _a_test_uses(body, symbol):
                test_rel = "tests/test_module.py"
                if named:
                    test_rel = f"tests/test_{Path(named).stem}.py"
                return (
                    f"no test calls {symbol}. "
                    f"Action: patch Path: {test_rel} "
                    f"Append: one AAA test that calls {symbol}."
                )
    if looks_like_fix_smell(task) and named:
        old, new = rename_pair(task)
        try:
            body = (Path(project) / named).read_text(encoding="utf-8")
        except OSError:
            body = ""
        if old and new and body:
            missed = refuse_rename_incomplete(task, named, body)
            if missed:
                return missed
    return ""


def refuse_write_done(task: str, ran_tests: bool, *, wrote: bool = True) -> str:
    """Write tasks are not finished until a passing unittest has run.

    A task that has not written yet is handled by the empty-done refuse.
    New-package still needs a run even if the model claims it is done.
    """
    if ran_tests:
        return ""
    if looks_like_new_package(task):
        return "not done. Action: run Argv: -m unittest discover -s tests -q"
    if not wrote:
        return ""
    needs_run = (
        looks_like_add_feature(task)
        or looks_like_everyday_code(task)
        or looks_like_fix_smell(task)
        or looks_like_bugfix(task)
        or looks_like_refactor(task)
        or looks_like_design_loop(task)
    )
    if not needs_run:
        return ""
    return "not done. Action: run Argv: -m unittest discover -s tests -q"


def refuse_package_done(task: str, ran_tests: bool, wrote: bool = True) -> str:
    return refuse_write_done(task, ran_tests, wrote=wrote)
