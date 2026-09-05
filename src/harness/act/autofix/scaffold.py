"""Write pkg/ + tests/ for a new-package task before the model starts.

A live 8B asked to design a GitHub PR CLI spent the step budget on
`locate Query: open-pr` and never created a file. The first Action has
to be a write to `pkg/<noun>.py`. The harness can create the empty
package itself — the same idea as binding a unique typo.
"""

from __future__ import annotations

from pathlib import Path

from harness.scan.app_spec import required_gaps
from harness.task import looks_like_app_loop, looks_like_new_package, package_noun

INIT_BODY = '"""Public exports only. Implementation lives in sibling modules."""\n'
_GETTERS = ("list_pulls", "get_prs")
_MOCK_TEST = """\
import json
import os
import unittest
from unittest.mock import patch

from pkg.{mod} import {fn}


class Test{cls}(unittest.TestCase):
    def test_{fn}_returns_titles(self) -> None:
        payload = [{{"title": "Fix login", "number": 1}}]
        with patch.dict(os.environ, {{"GITHUB_TOKEN": "test-token"}}):
            with patch("urllib.request.urlopen") as fake:
                fake.return_value.__enter__.return_value.read.return_value = (
                    json.dumps(payload).encode()
                )
                got = {fn}("owner", "repo")
        self.assertEqual(got, payload)
"""


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


def _list_getter(project: Path) -> tuple[str, str]:
    """Module stem and list/GET function the 8B actually wrote."""
    pkg = Path(project) / "pkg"
    if not pkg.is_dir():
        return "", ""
    for path in sorted(pkg.glob("*.py")):
        if path.name.startswith("_") or path.name.endswith(".bak"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for name in _GETTERS:
            if f"def {name}" in text:
                return path.stem, name
    return "", ""


def apply_cli_mock_test(project: Path, task: str, *, write: bool = True) -> str:
    """Write a mocked urlopen test once list/show exist. No weekday copy."""
    if not looks_like_app_loop(task):
        return ""
    leftover = {gap.key for gap in required_gaps(project, task)}
    if leftover & {"http", "list", "show"}:
        return ""
    mod, fn = _list_getter(project)
    if not fn:
        return ""
    dest = Path(project) / "tests" / f"test_{package_noun(task)}.py"
    try:
        existing = dest.read_text(encoding="utf-8") if dest.is_file() else ""
    except OSError:
        existing = ""
    if "urlopen" in existing and "GITHUB_TOKEN" in existing and fn in existing:
        return ""
    body = _MOCK_TEST.format(mod=mod, fn=fn, cls=fn.title().replace("_", ""))
    rel = dest.relative_to(Path(project)).as_posix()
    if write:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8")
    return f"wrote mocked urlopen test in {rel}"
