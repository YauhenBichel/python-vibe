"""Greenfield GitHub CLI loop: scaffold, refuse locate/ask, next gap."""

import tempfile
import unittest
from pathlib import Path

from harness.act.autofix.scaffold import apply_package_scaffold
from harness.agent.policy import LoopState, next_prompt, refuse_before, refuse_done
from harness.locate import refuse_app_ask, refuse_redundant_locate
from harness.scan.project_brief import classify_project, start_hint
from harness.task import looks_like_app_loop

CLI = "design and develop a small cli app for reviewing github PRs"


class _Turn:
    def __init__(self, action: str, path: str = "", summary: str = "") -> None:
        self.action = action
        self.path = path
        self.summary = summary
        self.find = ""


class AppLoopTest(unittest.TestCase):
    def test_scaffold_writes_pkg_and_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            note = apply_package_scaffold(root, CLI)
            self.assertIn("pkg/__init__.py", note)
            self.assertTrue((root / "pkg" / "__init__.py").is_file())
            self.assertTrue((root / "tests" / "__init__.py").is_file())
            self.assertEqual(apply_package_scaffold(root, CLI), "")

    def test_scaffold_skips_add_feature(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                apply_package_scaffold(Path(tmp), "add a function multiply"),
                "",
            )

    def test_locate_and_ask_are_refused(self) -> None:
        self.assertIn("pkg/pr_review.py", refuse_redundant_locate(CLI, "locate", False))
        self.assertIn("Do not ask", refuse_app_ask(CLI, "ask"))
        self.assertTrue(looks_like_app_loop(CLI))

    def test_hint_names_the_module_not_weekday(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            apply_package_scaffold(root, CLI)
            hint = start_hint(classify_project(root), CLI)
        self.assertIn("pkg/pr_review.py", hint)
        self.assertNotIn("weekday_name", hint)
        self.assertIn("Do not locate", hint)

    def test_tests_before_impl_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            apply_package_scaffold(root, CLI)
            state = LoopState(task=CLI, project=root, prelude_ran=True)
            blocked = refuse_before(
                state, _Turn("patch", path="tests/test_pr_review.py")
            )
        self.assertIn("Implementation first", blocked)
        self.assertIn("pkg/pr_review.py", blocked)

    def test_done_is_refused_until_list_and_show(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            apply_package_scaffold(root, CLI)
            state = LoopState(
                task=CLI, project=root, wrote_something=True, ran_tests=True
            )
            blocked = refuse_done(state, _Turn("done", summary="shipped a cli"))
        self.assertIn("not done", blocked)
        self.assertIn("urllib", blocked)

    def test_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            note = apply_package_scaffold(root, CLI, write=False)
        self.assertIn("would scaffold", note)
        self.assertFalse((root / "pkg" / "__init__.py").is_file())

    def test_preamble_mentions_the_scaffold(self) -> None:
        from harness.agent.options import AgentOptions
        from harness.agent.prompt import build_preamble

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pre = build_preamble(AgentOptions(project=root, task=CLI))
            self.assertIn("scaffolded", pre.pre_text)
            self.assertTrue((root / "pkg" / "__init__.py").is_file())

    def test_a_plain_package_locate_does_not_demand_urllib(self) -> None:
        blocked = refuse_redundant_locate(
            "create a package for total_price", "locate", False
        )
        self.assertIn("pkg/total_price.py", blocked)
        self.assertNotIn("urllib", blocked)

    def test_next_prompt_after_init_asks_for_http(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            apply_package_scaffold(root, CLI)
            state = LoopState(task=CLI, project=root, last_path="pkg/__init__.py")
            got = next_prompt(
                state,
                _Turn("edit", path="pkg/__init__.py"),
                "wrote pkg/__init__.py",
            )
        self.assertIn("pkg/pr_review.py", got)
        self.assertIn("urllib", got)

    def test_list_and_show_with_mocks_asks_to_run(self) -> None:
        from harness.agent.policy import RUN_SUITE

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "pkg"
            tests = root / "tests"
            pkg.mkdir()
            tests.mkdir()
            (pkg / "__init__.py").write_text('"""exports"""\n', encoding="utf-8")
            (pkg / "pr_review.py").write_text(
                "import os\n"
                "import urllib.request\n"
                "TOKEN = os.environ['GITHUB_TOKEN']\n"
                "def list_pulls(owner, repository):\n"
                "    urllib.request.urlopen('https://example')\n"
                "    return []\n"
                "def show_pull(owner, repository, number):\n"
                "    return {}\n",
                encoding="utf-8",
            )
            (tests / "test_pr_review.py").write_text(
                "from unittest.mock import patch\n"
                "from pkg.pr_review import list_pulls\n"
                "def test_list_pulls_returns_titles():\n"
                "    with patch('urllib.request.urlopen'):\n"
                "        list_pulls('o', 'r')\n",
                encoding="utf-8",
            )
            state = LoopState(
                task=CLI, project=root, last_path="tests/test_pr_review.py"
            )
            got = next_prompt(
                state,
                _Turn("edit", path="tests/test_pr_review.py"),
                "wrote tests/test_pr_review.py",
            )
        self.assertEqual(got, RUN_SUITE)


if __name__ == "__main__":
    unittest.main()
