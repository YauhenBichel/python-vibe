"""Greenfield GitHub CLI loop: scaffold, refuse locate/ask, next gap."""

import os
import tempfile
import unittest
from pathlib import Path

from harness.act.autofix.scaffold import apply_cli_mock_test, apply_package_scaffold
from harness.agent.policy import (
    LoopState,
    next_prompt,
    refuse_before,
    refuse_done,
    should_run_suite_after_write,
)
from harness.locate import (
    prelude,
    refuse_app_ask,
    refuse_app_overflow_explore,
    refuse_app_wrong_path,
    refuse_redundant_locate,
)
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

    def test_overflow_locate_and_ask_are_refused(self) -> None:
        overflow = "add the comment subcommand and a mocked test"
        self.assertIn(
            "comment",
            refuse_redundant_locate(overflow, "locate", False),
        )
        self.assertIn("Do not ask", refuse_app_ask(overflow, "ask"))
        self.assertIn("comment", refuse_app_ask(overflow, "ask"))

    def test_pagination_hint_names_page_not_comment(self) -> None:
        overflow = "add pagination to the GitHub PR CLI"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            apply_package_scaffold(root, CLI)
            hint = start_hint(classify_project(root), overflow)
            text, dest = prelude(root, overflow)
        self.assertIn("page=", hint)
        self.assertNotIn("comment", hint)
        self.assertIn("page=", text)
        self.assertNotIn("comment", text)
        self.assertEqual(dest, "pkg/pr_review.py")
        self.assertIn("page=", refuse_app_overflow_explore(overflow, "grep"))
        self.assertNotIn("comment", refuse_app_overflow_explore(overflow, "grep"))

    def test_config_hint_names_path_home(self) -> None:
        overflow = "add a config file via Path.home"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text, dest = prelude(root, overflow)
            hint = start_hint(classify_project(root), overflow)
        self.assertIn("Path.home()", hint)
        self.assertIn("pkg/config.py", text)
        self.assertEqual(dest, "pkg/config.py")

    def test_hint_names_the_module_not_weekday(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            apply_package_scaffold(root, CLI)
            hint = start_hint(classify_project(root), CLI)
        self.assertIn("pkg/pr_review.py", hint)
        self.assertNotIn("weekday_name", hint)
        self.assertIn("Do not locate", hint)

    def test_a_second_module_is_refused(self) -> None:
        self.assertIn(
            "pkg/pr_review.py",
            refuse_app_wrong_path(CLI, "edit", "pkg/pull_viewer.py"),
        )
        self.assertIn(
            "pkg/pr_review.py",
            refuse_app_wrong_path(CLI, "edit", "pkg.py"),
        )
        self.assertEqual(
            refuse_app_wrong_path(CLI, "edit", "pkg/pr_review.py"),
            "",
        )

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
            self.assertTrue(
                should_run_suite_after_write(
                    state, "wrote tests/test_pr_review.py", "tests/test_pr_review.py"
                )
            )
        self.assertEqual(got, RUN_SUITE)

    def test_an_incomplete_app_write_does_not_run_the_suite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            apply_package_scaffold(root, CLI)
            state = LoopState(task=CLI, project=root, last_path="pkg/__init__.py")
            self.assertFalse(
                should_run_suite_after_write(
                    state, "wrote pkg/__init__.py", "pkg/__init__.py"
                )
            )

    def test_a_green_suite_asks_for_done(self) -> None:
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
            state = LoopState(task=CLI, project=root, wrote_something=True)
            got = next_prompt(state, _Turn("run"), "exit 0\n.")
        self.assertIn("done", got.lower())
        self.assertIn("list and show", got.lower())

    def test_mechanical_mock_test_is_green(self) -> None:
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            apply_package_scaffold(root, CLI)
            (root / "pkg" / "pr_review.py").write_text(
                "import json\n"
                "import os\n"
                "import urllib.request\n"
                "\n"
                "def list_pulls(owner, repository):\n"
                "    token = os.environ['GITHUB_TOKEN']\n"
                "    req = urllib.request.Request('https://example')\n"
                "    req.add_header('authorization', token)\n"
                "    with urllib.request.urlopen(req) as response:\n"
                "        return json.loads(response.read().decode())\n"
                "def show_pull(owner, repository, number):\n"
                "    return {}\n",
                encoding="utf-8",
            )
            note = apply_cli_mock_test(root, CLI)
            self.assertIn("tests/test_pr_review.py", note)
            dest = root / "tests" / "test_pr_review.py"
            self.assertIn("GITHUB_TOKEN", dest.read_text(encoding="utf-8"))
            self.assertEqual(apply_cli_mock_test(root, CLI), "")
            ran = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
                cwd=root,
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(root)},
            )
        self.assertEqual(ran.returncode, 0, ran.stderr + ran.stdout)

    def test_mechanical_mock_test_binds_list_prs(self) -> None:
        """Remasure #214: list/show existed under 8B names; mock test never wrote."""
        import subprocess
        import sys

        from harness.scan.app_spec import required_gaps

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            apply_package_scaffold(root, CLI)
            (root / "pkg" / "pr_review.py").write_text(
                "import json\n"
                "import os\n"
                "import urllib.request\n"
                "\n"
                "def list_prs(owner, repository):\n"
                "    token = os.environ['GITHUB_TOKEN']\n"
                "    req = urllib.request.Request('https://example')\n"
                "    req.add_header('authorization', token)\n"
                "    with urllib.request.urlopen(req) as response:\n"
                "        return json.loads(response.read().decode())\n"
                "def show_pr(owner, repository, number):\n"
                "    return {}\n",
                encoding="utf-8",
            )
            self.assertEqual(
                {gap.key for gap in required_gaps(root, CLI)},
                {"mocked_tests"},
            )
            note = apply_cli_mock_test(root, CLI)
            self.assertIn("tests/test_pr_review.py", note)
            dest = root / "tests" / "test_pr_review.py"
            body = dest.read_text(encoding="utf-8")
            self.assertIn("list_prs", body)
            self.assertIn("GITHUB_TOKEN", body)
            self.assertEqual(required_gaps(root, CLI), [])
            self.assertEqual(apply_cli_mock_test(root, CLI), "")
            ran = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
                cwd=root,
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(root)},
            )
        self.assertEqual(ran.returncode, 0, ran.stderr + ran.stdout)

    def test_mechanical_mock_test_finds_list_prs_via_add_parser(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            apply_package_scaffold(root, CLI)
            (root / "pkg" / "pr_review.py").write_text(
                "import os\n"
                "import urllib.request\n"
                "TOKEN = os.environ['GITHUB_TOKEN']\n"
                "def list_prs(owner, repository):\n"
                "    urllib.request.urlopen('https://example')\n"
                "    return []\n"
                "parser.add_parser('list')\n"
                "parser.add_parser('show')\n",
                encoding="utf-8",
            )
            note = apply_cli_mock_test(root, CLI)
            dest = root / "tests" / "test_pr_review.py"
            self.assertIn("tests/test_pr_review.py", note)
            self.assertIn("list_prs", dest.read_text(encoding="utf-8"))

    def test_mechanical_mock_test_waits_for_show(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            apply_package_scaffold(root, CLI)
            (root / "pkg" / "pr_review.py").write_text(
                "import os\n"
                "import urllib.request\n"
                "TOKEN = os.environ['GITHUB_TOKEN']\n"
                "def list_prs(owner, repository):\n"
                "    urllib.request.urlopen('https://example')\n"
                "    return []\n",
                encoding="utf-8",
            )
            self.assertEqual(apply_cli_mock_test(root, CLI), "")

    def test_overflow_done_is_refused_until_comment(self) -> None:
        overflow = "add the comment subcommand and a mocked test"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            apply_package_scaffold(root, CLI)
            (root / "pkg" / "pr_review.py").write_text(
                "import os\n"
                "import urllib.request\n"
                "TOKEN = os.environ['GITHUB_TOKEN']\n"
                "def list_pulls(owner, repository):\n"
                "    urllib.request.urlopen('https://example')\n"
                "    return []\n"
                "def show_pull(owner, repository, number):\n"
                "    return {}\n"
                "parser.add_parser('list')\n"
                "parser.add_parser('show')\n",
                encoding="utf-8",
            )
            state = LoopState(
                task=overflow, project=root, wrote_something=True, ran_tests=True
            )
            blocked = refuse_done(state, _Turn("done", summary="added comment"))
            got = next_prompt(
                state, _Turn("edit", path="pkg/pr_review.py"), "wrote pkg/pr_review.py"
            )
        self.assertIn("comment", blocked)
        self.assertIn("pkg/pr_review.py", got)


if __name__ == "__main__":
    unittest.main()
