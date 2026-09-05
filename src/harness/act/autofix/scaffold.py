"""Write pkg/ + tests/ for a new-package task before the model starts.

A live 8B asked to design a GitHub PR CLI spent the step budget on
`locate Query: open-pr` and never created a file. The first Action has
to be a write to `pkg/<noun>.py`. The harness can create the empty
package itself — the same idea as binding a unique typo.
"""

from __future__ import annotations

from pathlib import Path

from harness.task import looks_like_new_package

INIT_BODY = '"""Public exports only. Implementation lives in sibling modules."""\n'


def apply_package_scaffold(
    project: Path, task: str, *, write: bool = True
) -> str:
    """Create pkg/__init__.py and tests/ when the task is a new package.

    Returns a short note when something was (or would be) written, else "".
    """
    if not looks_like_new_package(task):
        return ""
    root = Path(project)
    pkg = root / "pkg"
    init = pkg / "__init__.py"
    tests = root / "tests"
    tests_init = tests / "__init__.py"
    notes: list[str] = []
    if not init.is_file():
        notes.append("pkg/__init__.py")
        if write:
            pkg.mkdir(parents=True, exist_ok=True)
            init.write_text(INIT_BODY, encoding="utf-8")
    if not tests.is_dir() or not tests_init.is_file():
        notes.append("tests/")
        if write:
            tests.mkdir(parents=True, exist_ok=True)
            if not tests_init.is_file():
                tests_init.write_text("", encoding="utf-8")
    if not notes:
        return ""
    verb = "scaffolded" if write else "would scaffold"
    return f"Harness {verb} {', '.join(notes)} (no model)."
