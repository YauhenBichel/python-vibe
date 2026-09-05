"""Checklist for a greenfield GitHub PR CLI. No model."""

import json
import tempfile
import unittest
from pathlib import Path

from harness.scan.app_spec import (
    app_is_clean,
    list_getter_name,
    next_app_action,
    next_overflow_action,
    overflow_gaps,
    render_app_review,
    required_gaps,
    requested_overflow,
)
from harness.task import looks_like_app_loop, package_noun

CLI = "design and develop a small cli app for reviewing github PRs"


class AppSpecTest(unittest.TestCase):
    def test_empty_tree_needs_http_then_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pkg").mkdir()
            (root / "pkg" / "__init__.py").write_text(
                '"""Public exports only."""\n', encoding="utf-8"
            )
            keys = [gap.key for gap in required_gaps(root, CLI)]
        self.assertEqual(keys[0], "http")
        self.assertIn("list", keys)
        self.assertIn("show", keys)
        self.assertIn("mocked_tests", keys)
        self.assertFalse(app_is_clean(render_app_review(root, CLI)))

    def test_list_and_show_with_mocked_tests_are_enough_for_done(self) -> None:
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
                "from pkg.pr_review import list_pulls, show_pull\n"
                "def test_list_pulls_returns_titles():\n"
                "    with patch('urllib.request.urlopen'):\n"
                "        list_pulls('o', 'r')\n",
                encoding="utf-8",
            )
            self.assertEqual(required_gaps(root, CLI), [])
            self.assertTrue(app_is_clean(render_app_review(root, CLI)))
            extra = [gap.key for gap in overflow_gaps(root, CLI)]
        self.assertIn("comment", extra)
        self.assertIn("pagination", extra)
        self.assertIn("config", extra)

    def test_get_prs_and_main_count_as_mocked_tests(self) -> None:
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
                "def get_prs(owner, repository):\n"
                "    urllib.request.urlopen('https://example')\n"
                "    return []\n"
                "def show_pull(number):\n"
                "    return {}\n"
                "parser.add_parser('list')\n"
                "parser.add_parser('show')\n",
                encoding="utf-8",
            )
            (tests / "test_pr_review.py").write_text(
                "from unittest.mock import patch\n"
                "from pkg.pr_review import get_prs, main\n"
                "def test_main_list():\n"
                "    with patch('urllib.request.urlopen'):\n"
                "        get_prs('o', 'r')\n"
                "        main()\n",
                encoding="utf-8",
            )
            self.assertEqual(required_gaps(root, CLI), [])

    def test_list_prs_and_show_pr_count_without_add_parser(self) -> None:
        impl = (
            "import os\n"
            "import urllib.request\n"
            "TOKEN = os.environ['GITHUB_TOKEN']\n"
            "def list_prs(owner, repository):\n"
            "    urllib.request.urlopen('https://example')\n"
            "    return []\n"
            "def show_pr(owner, repository, number):\n"
            "    return {}\n"
        )
        self.assertEqual(list_getter_name(impl), "list_prs")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "pkg"
            tests = root / "tests"
            pkg.mkdir()
            tests.mkdir()
            (pkg / "__init__.py").write_text('"""exports"""\n', encoding="utf-8")
            (pkg / "pr_review.py").write_text(impl, encoding="utf-8")
            (tests / "test_pr_review.py").write_text(
                "from unittest.mock import patch\n"
                "from pkg.pr_review import list_prs\n"
                "def test_list_prs_returns_titles():\n"
                "    with patch('urllib.request.urlopen'):\n"
                "        list_prs('o', 'r')\n",
                encoding="utf-8",
            )
            self.assertEqual(required_gaps(root, CLI), [])

    def test_get_pr_is_show_not_list(self) -> None:
        impl = (
            "def get_pr(owner, repository, number):\n"
            "    return {}\n"
        )
        self.assertEqual(list_getter_name(impl), "")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "pkg"
            pkg.mkdir()
            (pkg / "__init__.py").write_text('"""exports"""\n', encoding="utf-8")
            (pkg / "pr_review.py").write_text(
                "import os\n"
                "import urllib.request\n"
                "TOKEN = os.environ['GITHUB_TOKEN']\n" + impl,
                encoding="utf-8",
            )
            keys = [gap.key for gap in required_gaps(root, CLI)]
        self.assertIn("list", keys)
        self.assertNotIn("show", keys)

    def test_gold_fixture_noun_and_keys(self) -> None:
        from harness.scan.app_spec import OVERFLOW_KEYS, REQUIRED_KEYS

        gold = Path(__file__).resolve().parents[2] / (
            "eval/fixtures/daily_cli_app/gold.json"
        )
        data = json.loads(gold.read_text(encoding="utf-8"))
        self.assertEqual(package_noun(data["task"]), data["package_noun"])
        self.assertEqual(REQUIRED_KEYS, tuple(data["required"]))
        self.assertEqual(OVERFLOW_KEYS, tuple(data["overflow"]))
        fixture = gold.parent
        self.assertEqual(
            [gap.key for gap in required_gaps(fixture, data["task"])],
            ["http", "list", "show", "mocked_tests"],
        )

    def test_next_action_names_the_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pkg").mkdir()
            (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            line = next_app_action(root, CLI)
        self.assertIn("pkg/pr_review.py", line)
        self.assertEqual(package_noun(CLI), "pr_review")
        self.assertTrue(looks_like_app_loop(CLI))

    def test_comment_run_names_only_comment(self) -> None:
        overflow = "add the comment subcommand and a mocked test"
        self.assertEqual(requested_overflow(overflow), ("comment",))
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
                "    return {}\n"
                "parser.add_parser('list')\n"
                "parser.add_parser('show')\n",
                encoding="utf-8",
            )
            (tests / "test_pr_review.py").write_text(
                "from unittest.mock import patch\n"
                "from pkg.pr_review import list_pulls\n"
                "with patch('urllib.request.urlopen'):\n"
                "    list_pulls('o', 'r')\n",
                encoding="utf-8",
            )
            line = next_overflow_action(root, overflow)
        self.assertIn("comment", line)
        self.assertIn("pkg/pr_review.py", line)

    def test_pagination_run_names_page_not_comment(self) -> None:
        overflow = "add pagination to the GitHub PR CLI"
        self.assertEqual(requested_overflow(overflow), ("pagination",))
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
                "    return {}\n"
                "parser.add_parser('list')\n"
                "parser.add_parser('show')\n",
                encoding="utf-8",
            )
            (tests / "test_pr_review.py").write_text(
                "from unittest.mock import patch\n"
                "from pkg.pr_review import list_pulls\n"
                "with patch('urllib.request.urlopen'):\n"
                "    list_pulls('o', 'r')\n",
                encoding="utf-8",
            )
            line = next_overflow_action(root, overflow)
        self.assertIn("page=", line)
        self.assertNotIn("comment", line)

    def test_def_comment_closes_the_comment_gap(self) -> None:
        overflow = "add the comment subcommand and a mocked test"
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
                "def list_pulls(o, r):\n"
                "    urllib.request.urlopen('https://example')\n"
                "def show_pull(o, r, n):\n"
                "    return {}\n"
                "def comment(o, r, n):\n"
                "    return None\n"
                "parser.add_parser('list')\n"
                "parser.add_parser('show')\n",
                encoding="utf-8",
            )
            (tests / "test_pr_review.py").write_text(
                "from unittest.mock import patch\n"
                "from pkg.pr_review import list_pulls\n"
                "with patch('urllib.request.urlopen'):\n"
                "    list_pulls('o', 'r')\n",
                encoding="utf-8",
            )
            extra = [gap.key for gap in overflow_gaps(root, overflow)]
            leftover = next_overflow_action(root, overflow)
        self.assertNotIn("comment", extra)
        self.assertEqual(leftover, "")

    def test_query_page_closes_the_pagination_gap(self) -> None:
        overflow = "add pagination to the GitHub PR CLI"
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
                "    urllib.request.urlopen(\n"
                "        f'https://api.github.com/repos/{owner}/{repository}"
                "/pulls?page='\n"
                "    )\n"
                "def show_pull(o, r, n):\n"
                "    return {}\n"
                "def comment_on(o, r, n):\n"
                "    return None\n"
                "parser.add_parser('list')\n"
                "parser.add_parser('show')\n",
                encoding="utf-8",
            )
            (tests / "test_pr_review.py").write_text(
                "from unittest.mock import patch\n"
                "from pkg.pr_review import list_pulls\n"
                "with patch('urllib.request.urlopen'):\n"
                "    list_pulls('o', 'r')\n",
                encoding="utf-8",
            )
            extra = [gap.key for gap in overflow_gaps(root, overflow)]
            leftover = next_overflow_action(root, overflow)
        self.assertNotIn("pagination", extra)
        self.assertEqual(leftover, "")


if __name__ == "__main__":
    unittest.main()
