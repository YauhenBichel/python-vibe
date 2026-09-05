"""Checklist for a greenfield GitHub PR-review CLI. Deterministic. No model.

A new-package loop used to stop after one function and a test. A typed
"design a CLI for reviewing GitHub PRs" job is not done then: list and
show still have to exist, HTTP has to be urllib with a token from the
environment, and the suite has to mock the network.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from harness.scan.project_scan import SKIP_DIR
from harness.task import package_noun

CLEAN_PHRASE = "app checklist clean"
REQUIRED_KEYS = ("init", "http", "list", "show", "mocked_tests")
OVERFLOW_KEYS = ("comment", "pagination", "config")


@dataclass(frozen=True)
class Gap:
    """One missing piece of the CLI, and the Action that closes it."""

    key: str
    next_action: str


def _skip(path: Path) -> bool:
    return any(part in SKIP_DIR or part.startswith(".") for part in path.parts)


def _read_tree(project: Path) -> tuple[str, str]:
    """Concatenate impl and test sources. Missing files are empty strings."""
    impl_parts: list[str] = []
    test_parts: list[str] = []
    root = Path(project)
    if not root.is_dir():
        return "", ""
    for path in sorted(root.rglob("*.py")):
        if _skip(path) or path.name.endswith(".bak"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = path.relative_to(root).as_posix()
        if "tests" in path.parts or path.name.startswith("test_"):
            test_parts.append(text)
        elif rel.endswith("__init__.py"):
            continue
        else:
            impl_parts.append(text)
    return "\n".join(impl_parts), "\n".join(test_parts)


def _has_list_command(impl: str) -> bool:
    return bool(
        re.search(r'add_parser\(\s*["\']list["\']', impl)
        or re.search(r"\bdef list_pulls\b", impl)
    )


def _has_show_command(impl: str) -> bool:
    return bool(
        re.search(r'add_parser\(\s*["\']show["\']', impl)
        or re.search(r"\bdef show_pull\b", impl)
    )


def _has_comment_command(impl: str) -> bool:
    return bool(
        re.search(r'add_parser\(\s*["\']comment["\']', impl)
        or re.search(r"\bdef comment_on\b", impl)
    )


def _uses_urllib(impl: str) -> bool:
    return "urllib.request" in impl


def _token_from_env(impl: str) -> bool:
    if not re.search(r"\b(os\.environ|os\.getenv)\b", impl):
        return False
    return bool(re.search(r"TOKEN|token", impl))


def _mocks_http(tests: str) -> bool:
    return bool(
        re.search(r"\b(urlopen|urllib\.request)\b", tests)
        and re.search(r"\b(patch|MagicMock|mock)\b", tests)
    )


def _tests_call_list_or_show(tests: str) -> bool:
    return bool(re.search(r"\b(list_pulls|show_pull)\b", tests))


def _has_pagination(impl: str) -> bool:
    return bool(re.search(r"\b(page=|rel=[\"']next|Link)\b", impl))


def _has_home_config(impl: str) -> bool:
    return "Path.home()" in impl


def app_gaps(project: Path, task: str, *, include_overflow: bool = True) -> list[Gap]:
    """Missing pieces, in the order the 8B should write them."""
    noun = package_noun(task)
    module = f"pkg/{noun}.py"
    test = f"tests/test_{noun}.py"
    impl, tests = _read_tree(project)
    init = Path(project) / "pkg" / "__init__.py"
    gaps: list[Gap] = []
    if not init.is_file():
        gaps.append(
            Gap(
                "init",
                "Next Action must be edit Path: pkg/__init__.py "
                "(exports only). No logic.",
            )
        )
    if not _uses_urllib(impl) or not _token_from_env(impl):
        gaps.append(
            Gap(
                "http",
                f"Next Action must be edit Path: {module} with urllib.request "
                "and a token from os.environ. No curl. No inline secrets.",
            )
        )
    if not _has_list_command(impl):
        gaps.append(
            Gap(
                "list",
                f"Next Action must be edit Path: {module} with argparse "
                "subcommand list and def list_pulls(...).",
            )
        )
    if not _has_show_command(impl):
        gaps.append(
            Gap(
                "show",
                f"Next Action must be edit Path: {module} with argparse "
                "subcommand show and def show_pull(...).",
            )
        )
    if not _mocks_http(tests) or not _tests_call_list_or_show(tests):
        gaps.append(
            Gap(
                "mocked_tests",
                f"Next Action must be edit Path: {test} as a unittest.TestCase. "
                "patch urllib.request.urlopen. AAA: got = list_pulls(...). "
                "Do not call the network.",
            )
        )
    if include_overflow:
        if not _has_comment_command(impl):
            gaps.append(
                Gap(
                    "comment",
                    f"Next Action must be edit Path: {module} with argparse "
                    "subcommand comment and def comment_on(...).",
                )
            )
        if not _has_pagination(impl):
            gaps.append(
                Gap(
                    "pagination",
                    f"Next Action must be patch Path: {module} to follow a "
                    "Link next header or page= .",
                )
            )
        if not _has_home_config(impl):
            gaps.append(
                Gap(
                    "config",
                    f"Next Action must be edit Path: pkg/config.py with "
                    "Path.home() for the config file. No hardcoded home.",
                )
            )
    return gaps


def required_gaps(project: Path, task: str) -> list[Gap]:
    """Gaps that block done on the first run: list, show, mocked suite."""
    return [gap for gap in app_gaps(project, task, include_overflow=False)]


def overflow_gaps(project: Path, task: str) -> list[Gap]:
    """comment / pagination / config — a later typed run, not --steps."""
    return [gap for gap in app_gaps(project, task) if gap.key in OVERFLOW_KEYS]


def render_app_review(project: Path, task: str) -> str:
    gaps = required_gaps(project, task)
    extra = overflow_gaps(project, task)
    if not gaps:
        if extra:
            leftover = ", ".join(gap.key for gap in extra)
            return (
                f"{CLEAN_PHRASE} for list and show. "
                f"Later run can add {leftover}."
            )
        return f"{CLEAN_PHRASE} — list, show, comment, pagination, config, mocked tests"
    lines = ["app checklist (deterministic, not a model opinion):"]
    lines.extend(f"- {gap.key}: {gap.next_action}" for gap in gaps)
    return "\n".join(lines)


def app_is_clean(report: str) -> bool:
    """True when the required list/show checklist is satisfied."""
    return CLEAN_PHRASE in (report or "")


def next_app_action(project: Path, task: str, *, required_only: bool = True) -> str:
    """The single next Action line, or empty when that tier is clean."""
    gaps = required_gaps(project, task) if required_only else app_gaps(project, task)
    if not gaps:
        return ""
    return gaps[0].next_action + "\n"


def http_test_nudge(task: str) -> str:
    """AAA mock example the 8B can copy. Not the weekday write-tests skill."""
    noun = package_noun(task)
    return (
        f"Next Action must be edit Path: tests/test_{noun}.py\n"
        "```python\n"
        "import json\n"
        "import unittest\n"
        "from unittest.mock import patch\n"
        f"from pkg.{noun} import list_pulls\n\n\n"
        f"class Test{noun.title().replace('_', '')}(unittest.TestCase):\n"
        "    def test_list_pulls_returns_titles(self) -> None:\n"
        '        payload = [{"title": "Fix login", "number": 1}]\n'
        '        with patch("urllib.request.urlopen") as fake:\n'
        "            fake.return_value.__enter__.return_value.read.return_value = (\n"
        "                json.dumps(payload).encode()\n"
        "            )\n"
        '            got = list_pulls("owner", "repo")\n'
        "        self.assertEqual(got, payload)\n"
        "```\n"
        "Do not call the network. Do not copy weekday or multiply.\n"
    )
