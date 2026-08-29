"""Project tools for the agent loop. Jail + no shell."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from harness.act.autofix import (
    apply_function_rename,
    apply_missing_imports,
    apply_typo_fixes,
)
from harness.act.code import apply_source, read_project_file, resolve_project_file
from harness.paths import is_secret_name, rel_posix, suffix_globs
from harness.act.patch_fix import align_indent, find_match, miss_message
from harness.skillkit.style import (
    refuse_layout,
    refuse_stdlib_shadow,
    refuse_ops_draft,
    refuse_platform_draft,
    refuse_rename_incomplete,
    refuse_shell_fetch,
    refuse_test_in_impl,
    refuse_undefined_draft,
    refuse_weak_test,
)
from harness.task import looks_like_bugfix, looks_like_fix_smell, rename_pair
from harness.scan.project_brief import render_map, resolve_scope
from harness.scan.project_scan import SKIP_DIR
from harness.scan.repo_map import render_outline

MAX_HITS = 30
_TRUNC = "\n# … truncated. Narrow Query or pass --scope"


def glob_py(project: Path, pattern: str, scope: str = "") -> str:
    root = project.resolve()
    base = resolve_scope(project, scope) if scope else root
    hits: list[str] = []
    for path in base.glob(pattern):
        if any(part in SKIP_DIR for part in path.parts):
            continue
        if is_secret_name(path.name):
            continue
        if path.is_file():
            hits.append(rel_posix(path, root))
        if len(hits) >= MAX_HITS:
            return "\n".join(hits) + _TRUNC
    if not hits:
        # rglob if user passed **/...
        for path in base.rglob(pattern.removeprefix("**/")):
            if any(part in SKIP_DIR for part in path.parts):
                continue
            if is_secret_name(path.name):
                continue
            if path.is_file():
                hits.append(rel_posix(path, root))
            if len(hits) >= MAX_HITS:
                return "\n".join(hits) + _TRUNC
    return "\n".join(hits) or "(no files)"


def grep_py(project: Path, query: str, scope: str = "") -> str:
    root = project.resolve()
    base = resolve_scope(project, scope) if scope else root
    try:
        rx = re.compile(query)
    except re.error as exc:
        return f"bad regex: {exc}"
    lines: list[str] = []
    for pattern in suffix_globs():
        for path in base.rglob(pattern):
            if any(part in SKIP_DIR for part in path.parts):
                continue
            if is_secret_name(path.name):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    rel = rel_posix(path, root)
                    lines.append(f"{rel}:{i}:{line.strip()[:160]}")
                    if len(lines) >= MAX_HITS:
                        return "\n".join(lines) + _TRUNC
    return "\n".join(lines) or "(no hits)"


def map_py(project: Path, scope: str = "") -> str:
    """File list plus a signature outline. Sizes do not tell it where to look."""
    return f"{render_map(project, scope)}\n\n{render_outline(project, scope)}"


def read_py(project: Path, rel: str) -> str:
    path = resolve_project_file(project, rel)
    return read_project_file(path)


_TEST_METH = re.compile(r"def\s+(test_\w+)\s*\(")
_ASSERT_CALL = re.compile(r"assertEqual\s*\(\s*([A-Za-z_]\w+)\s*\(")
_IMPORT_LINE = re.compile(r"^(from\s+\S+\s+import\s+)(.+)$")


def _add_import_symbol(text: str, name: str) -> str:
    if not name or name in {"self", "True", "False", "None"}:
        return text
    for line in text.splitlines():
        match = _IMPORT_LINE.match(line)
        if not match:
            continue
        imported = {part.strip() for part in match.group(2).split(",")}
        if name in imported:
            return text
        if any(skip in line for skip in ("unittest", "pathlib", "typing")):
            continue
        return text.replace(line, f"{match.group(1)}{match.group(2).rstrip()}, {name}", 1)
    return text


def _called_name(original: str, append: str) -> str:
    """The function the new test needs imported.

    It used to be read out of `assertEqual(multiply(...))`. The style rules
    ask for the opposite shape — `got = multiply(...)`, then assert `got` —
    so following them meant the import was never added and the suite broke.
    Reading the names the new test leaves unbound covers both shapes.
    """
    from harness.scan.names import new_undefined

    for name in new_undefined(original, original.rstrip() + "\n\n" + append):
        return name
    match = _ASSERT_CALL.search(append)
    return match.group(1) if match else ""


def repair_unittest_append(original: str, append: str) -> str | None:
    """8B Append: often lands after if __name__ and skips the import."""
    if "def test_" not in append:
        return None
    if "TestCase" not in original and "unittest" not in original:
        return None
    meth = _TEST_METH.search(append)
    if not meth or re.search(rf"def\s+{re.escape(meth.group(1))}\s*\(", original):
        return None
    lines = append.strip("\n").splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return None
    base = len(lines[0]) - len(lines[0].lstrip())
    dedented = "\n".join(
        line[base:] if len(line) >= base else line.lstrip() for line in lines
    )
    method = "    " + dedented.replace("\n", "\n    ")
    text = _add_import_symbol(original, _called_name(original, append))
    marker = "\nif __name__"
    if marker in text:
        return text.replace(marker, "\n" + method + "\n" + marker, 1)
    return text.rstrip() + "\n\n" + method + "\n"


def refuse_duplicate_module(project: Path, rel: str, original: str) -> str:
    """Refuse a new file that repeats a module this project already has.

    Watched a run write the same function to `pkg/orders.py` and then
    `src/orders.py`. Two modules with one name is worse than either: an
    import finds whichever comes first on the path, and the other rots.
    """
    if original.strip():
        return ""
    from harness.paths import as_project_rel, rel_posix

    wanted = Path(as_project_rel(rel))
    if wanted.name.startswith("test_") or "tests" in wanted.parts:
        return ""
    root = Path(project).resolve()
    for existing in sorted(root.rglob(f"{wanted.stem}.py")):
        if any(part in {".git", ".venv", "__pycache__"} for part in existing.parts):
            continue
        found = rel_posix(existing, root)
        if found != wanted.as_posix():
            return (
                f"{found} is already this project's {wanted.stem} module. "
                f"Action: patch Path: {found} Append: the new function"
            )
    return ""


def refuse_missing_import_target(project: Path, rel: str, draft: str) -> str:
    """Refuse a file importing a name this project has not defined yet.

    Asked to create a module and a test for it, the model wrote only the
    test, importing a function nobody had written. That reads as valid
    Python — the import binds the name — and fails when the suite runs. The
    function has to exist first.
    """
    from harness.scan.names import missing_import_targets

    missing = missing_import_targets(project, draft)
    if not missing:
        return ""
    module, name = missing[0]
    return (
        f"{module} does not define {name} yet. Write the function first: "
        f"Action: patch Path: {module.replace('.', '/')}.py Append: def {name}(...)"
    )


def _style_blocks(
    task: str, rel: str, original: str, draft: str, fragment: str = ""
) -> str:
    blocked = refuse_stdlib_shadow(rel, original)
    if blocked:
        return blocked
    blocked = refuse_layout(rel, original, draft)
    if blocked:
        return blocked
    blocked = refuse_shell_fetch(rel, draft)
    if blocked:
        return blocked
    blocked = refuse_platform_draft(rel, draft)
    if blocked:
        return blocked
    blocked = refuse_ops_draft(rel, draft)
    if blocked:
        return blocked
    blocked = refuse_test_in_impl(rel, draft)
    if blocked:
        return blocked
    blocked = refuse_undefined_draft(task, rel, original, draft)
    if blocked:
        return blocked
    blocked = refuse_rename_incomplete(task, rel, draft)
    if blocked:
        return blocked
    return refuse_weak_test(rel, fragment or draft)


def patch_py(
    project: Path,
    rel: str,
    find: str,
    replace: str,
    append: str = "",
    task: str = "",
) -> str:
    path = resolve_project_file(project, rel)
    original = path.read_text(encoding="utf-8") if path.is_file() else ""
    text = original
    note = ""
    if looks_like_fix_smell(task):
        old, new = rename_pair(task)
        renamed = apply_function_rename(original, old, new)
        if renamed != original:
            text = renamed
            note = " (harness renamed the def)"
            find = ""
    if find:
        if len(find) < 8:
            return (
                "Find: must be at least 8 characters. "
                "Use a unique full line such as: Find: return tota"
            )
        hits = text.count(find)
        if hits > 1:
            return f"Find: matches {hits} times — use a longer unique snippet"
        match = find_match(text, find)
        if match is None:
            return miss_message(text, find)
        text = text.replace(
            match.text,
            replace if match.exact else align_indent(match.text, replace),
            1,
        )
        if not match.exact:
            note = " (Find: matched after whitespace normalisation)"
        else:
            note = ""
    elif text == original and not append:
        return "patch needs Find: or Append:"
    if append:
        repaired = repair_unittest_append(text, append)
        text = (
            repaired
            if repaired is not None
            else text.rstrip() + "\n\n" + append.rstrip() + "\n"
        )
    if looks_like_bugfix(task):
        bound = apply_typo_fixes(text)
        if bound != text:
            text = bound
            note = (note + " (harness bound unique NameError typo)").strip()
    repaired = apply_missing_imports(text)
    if repaired != text:
        text = repaired
        note = (note + " (harness added the missing import)").strip()
    blocked = refuse_duplicate_module(project, rel, original)
    if not blocked:
        blocked = refuse_missing_import_target(project, rel, text)
    if not blocked:
        blocked = _style_blocks(task, rel, original, text, fragment=append or replace)
    if blocked:
        return blocked
    apply_source(path, text, original=original)
    return (
        f"patched {rel_posix(path, project.resolve())} "
        f"(backup {path.name}.bak){note}"
    )


def edit_py(project: Path, rel: str, source: str, task: str = "") -> str:
    path = resolve_project_file(project, rel)
    original = path.read_text(encoding="utf-8") if path.is_file() else ""
    source = apply_missing_imports(source)
    blocked = refuse_duplicate_module(project, rel, original)
    if not blocked:
        blocked = refuse_missing_import_target(project, rel, source)
    if not blocked:
        blocked = _style_blocks(task, rel, original, source)
    if blocked:
        return blocked
    apply_source(path, source, original=original)
    return f"wrote {rel_posix(path, project.resolve())} (backup {path.name}.bak)"


def run_python(project: Path, argv: tuple[str, ...]) -> str:
    if not argv:
        return "Argv required, e.g. -m unittest discover -s tests -q"
    blocked = {"-c", "-m pip", "http.server"}
    joined = " ".join(argv)
    if any(tok in joined for tok in blocked) or "|" in joined or ";" in joined:
        return "refusing that argv"
    if "unittest" in joined and "tests" in joined and not (project / "tests").is_dir():
        return "no tests/ directory in this project — add tests/test_*.py first"
    try:
        proc = subprocess.run(
            [sys.executable, *argv],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "timed out (60s)"
    out = (proc.stdout or "") + (proc.stderr or "")
    return f"exit {proc.returncode}\n{out[-4000:]}"
