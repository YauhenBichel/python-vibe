"""The seven things the agent can do to a project.

Look for a file, search inside files, read one, run one, change one, and
draw the shape of the whole. Nothing here decides whether a change is
allowed — `act.gate` answers that, and `patch_py` and `edit_py` ask it
before they write.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import re
import subprocess
import sys
from pathlib import Path

from harness.act.autofix import (
    append_instead_of_replacing,
    apply_function_rename,
    apply_missing_imports,
    apply_typo_fixes,
)
from harness.act.code import apply_source, read_project_file, resolve_project_file
from harness.act.gate import (
    already_defined,
    refuse_duplicate_module,
    refuse_missing_import_target,
    repair_unittest_append,
    first_refusal,
)
from harness.paths import is_secret_name, rel_posix, suffix_globs
from harness.act.patch_fix import align_indent, find_match, miss_message
from harness.skillkit.refuse_change import (
    refuse_add_opens_file,
    refuse_layout,
    refuse_ops_draft,
    refuse_platform_draft,
    refuse_rename_incomplete,
    refuse_shell_fetch,
    refuse_stdlib_shadow,
    refuse_stub_body,
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
        wanted = re.compile(query)
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
                if wanted.search(line):
                    rel = rel_posix(path, root)
                    lines.append(f"{rel}:{i}:{line.strip()[:160]}")
                    if len(lines) >= MAX_HITS:
                        return "\n".join(lines) + _TRUNC
    return "\n".join(lines) or "(no hits)"


def map_py(project: Path, scope: str = "") -> str:
    """File list plus a signature outline. Sizes do not tell it where to look."""
    return f"{render_map(project, scope)}\n\n{render_outline(project, scope)}"


def read_py(project: Path, rel: str, about: str = "") -> str:
    """The file. `about` names what the read is for, so that a file too
    long to send whole keeps the part being asked about."""
    path = resolve_project_file(project, rel)
    return read_project_file(path, about=about)


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
        already = already_defined(original, append, rel)
        if already:
            return already
        repaired = repair_unittest_append(text, append, rel)
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
        blocked = first_refusal(task, rel, original, text, fragment=append or replace)
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
        blocked = first_refusal(task, rel, original, source)
    if blocked:
        return blocked
    # A short draft of only-new definitions is an addition, not a rewrite.
    merged = append_instead_of_replacing(original, source)
    if merged:
        apply_source(path, merged, original=original)
        return (
            f"appended to {rel_posix(path, project.resolve())} "
            f"(backup {path.name}.bak) — the draft added new definitions "
            "rather than replacing the file"
        )
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
