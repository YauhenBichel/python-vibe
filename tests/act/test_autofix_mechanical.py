"""The repairs that run before any model turn, and when they stop."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock
from harness import Agent, AgentOptions
from harness.act.autofix import apply_mechanical
from harness.agent.prompt import build_preamble
"""Mechanical rename and NameError typo fixes. No model."""
ROOT = Path(__file__).resolve().parents[2]
ORDERS = '''TAX_RATE = 0.2

def compute_total(prices: list[int]) -> int:
    return sum(prices)

def total_with_tax(prices: list[int]) -> float:
    subtotal = compute_total(prices)
    return subtotl + (subtotl * TAX_RATE)
'''
UTIL = """def calc(x: int, y: int) -> int:
    return x * y
"""
def _scripted_done(summary: str):
    """Stand in for the model: say done straight away."""

    def generate(_prompt: str) -> str:
        return f"Action: done\nSummary: {summary}"

    return lambda *a, **k: ("scripted", generate)


class MechanicalPreludeTest(unittest.TestCase):
    def test_bugfix_is_applied_before_the_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "orders.py").write_text(ORDERS, encoding="utf-8")
            (root / "tests" / "test_orders.py").write_text("x = 1\n", encoding="utf-8")
            note = apply_mechanical(
                root,
                "find a real NameError in src/orders.py and fix it",
                "src/orders.py",
            )
            body = (root / "src" / "orders.py").read_text(encoding="utf-8")
        self.assertIn("subtotl → subtotal", note)
        self.assertNotIn("subtotl", body)
        self.assertIn("subtotal = compute_total", body)

    def test_rename_is_applied_before_the_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "util.py").write_text(UTIL, encoding="utf-8")
            note = apply_mechanical(
                root,
                "rename calc to multiply in src/util.py",
                "src/util.py",
            )
            body = (root / "src" / "util.py").read_text(encoding="utf-8")
        self.assertIn("def calc → def multiply", note)
        self.assertIn("def multiply(x: int, y: int) -> int:", body)

    def test_preamble_records_the_autofix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "orders.py").write_text(ORDERS, encoding="utf-8")
            pre = build_preamble(
                AgentOptions(
                    project=root,
                    task="find a real NameError in src/orders.py and fix it",
                )
            )
        self.assertIn("mechanical fix", pre.autofix)
        self.assertIn("subtotl", pre.autofix)


class MechanicalFinishTest(unittest.TestCase):
    """A unique typo plus a green suite does not need the model."""

    def test_the_run_ends_before_the_engine_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "orders.py").write_text(ORDERS, encoding="utf-8")
            (root / "tests" / "test_orders.py").write_text(
                "import unittest\n\n\nclass OrdersTest(unittest.TestCase):\n"
                "    def test_placeholder(self) -> None:\n"
                "        self.assertEqual(1, 1)\n",
                encoding="utf-8",
            )
            options = AgentOptions(
                project=root,
                task="find a real NameError in src/orders.py and fix it",
            )
            with mock.patch(
                "harness.agent.loop.make_generate",
                side_effect=AssertionError("model must not load after a mechanical pass"),
            ):
                result = Agent(options).run()
            body = (root / "src" / "orders.py").read_text(encoding="utf-8")
        self.assertTrue(result.ok)
        self.assertEqual(result.stopped, "done")
        self.assertEqual(result.writes, ("src/orders.py",))
        self.assertIn("Tests passed", result.summary)
        self.assertNotIn("subtotl", body)

    def test_a_read_only_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "orders.py").write_text(ORDERS, encoding="utf-8")
            options = AgentOptions(
                project=root,
                task="find a real NameError in src/orders.py and fix it",
                allow_writes=False,
            )
            with mock.patch(
                "harness.agent.loop.make_generate",
                side_effect=AssertionError("model must not load for a dry run fix"),
            ):
                result = Agent(options).run()
            body = (root / "src" / "orders.py").read_text(encoding="utf-8")
        self.assertTrue(result.ok)
        self.assertEqual(result.writes, ())
        self.assertIn("subtotl", body)
        self.assertIn("Read-only", result.summary)

    def test_pagination_overflow_ends_before_the_engine_loads(self) -> None:
        """0/3 after #228: the 8B wrote nothing. page= is a compiler job."""
        overflow = "add pagination to the GitHub PR CLI"
        impl = (
            "import json\n"
            "import os\n"
            "import urllib.request\n"
            "\n"
            "def list_pulls(owner, repository):\n"
            "    token = os.environ['GITHUB_TOKEN']\n"
            "    req = urllib.request.Request(\n"
            "        f'https://api.github.com/repos/{owner}/{repository}/pulls'\n"
            "    )\n"
            "    with urllib.request.urlopen(req) as response:\n"
            "        return json.loads(response.read().decode())\n"
            "\n"
            "def show_pull(owner, repository, number):\n"
            "    return {}\n"
            "\n"
            "def comment_on(owner, repository, number, body):\n"
            "    return None\n"
        )
        test = (
            "import json\n"
            "import os\n"
            "import unittest\n"
            "from unittest.mock import patch\n"
            "\n"
            "from pkg.pr_review import list_pulls\n"
            "\n"
            "class TestListPulls(unittest.TestCase):\n"
            "    def test_list_pulls_returns_titles(self) -> None:\n"
            "        payload = [{'title': 'Fix login', 'number': 1}]\n"
            "        with patch.dict(os.environ, {'GITHUB_TOKEN': 'test-token'}):\n"
            "            with patch('urllib.request.urlopen') as fake:\n"
            "                fake.return_value.__enter__.return_value.read"
            ".return_value = json.dumps(payload).encode()\n"
            "                got = list_pulls('owner', 'repo')\n"
            "        self.assertEqual(got, payload)\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "pkg"
            tests = root / "tests"
            pkg.mkdir()
            tests.mkdir()
            (pkg / "__init__.py").write_text('"""exports"""\n', encoding="utf-8")
            (pkg / "pr_review.py").write_text(impl, encoding="utf-8")
            (tests / "test_pr_review.py").write_text(test, encoding="utf-8")
            options = AgentOptions(project=root, task=overflow)
            with mock.patch(
                "harness.agent.loop.make_generate",
                side_effect=AssertionError("model must not load after a page= pass"),
            ):
                result = Agent(options).run()
            body = (pkg / "pr_review.py").read_text(encoding="utf-8")
        self.assertTrue(result.ok)
        self.assertEqual(result.stopped, "done")
        self.assertIn("pkg/pr_review.py", result.writes)
        self.assertIn("/pulls?page=1'", body)
        self.assertIn("Tests passed", result.summary)


class MechanicalFastPathTest(unittest.TestCase):
    """A fix the harness can make itself should not need the model at all.

    It must also stay inside the promises the rest of the harness makes: a
    read-only run changes nothing, and a project without tests has not
    failed anything.
    """

    TASK = "find a real NameError in src/orders.py and fix it"
    BROKEN = (
        "def total_with_tax(prices: list[int]) -> float:\n"
        "    subtotal = sum(prices)\n"
        "    return subtotl * 1.2\n"
    )

    def _project(self, tmp: str, *, with_tests: bool) -> Path:
        root = Path(tmp)
        (root / "src").mkdir()
        (root / "src" / "orders.py").write_text(self.BROKEN, encoding="utf-8")
        if with_tests:
            (root / "tests").mkdir()
            (root / "tests" / "test_smoke.py").write_text(
                "import unittest\n\n\nclass TestSmoke(unittest.TestCase):\n"
                "    def test_smoke_passes(self) -> None:\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )
        return root

    def _run(self, project: Path, **options):
        from unittest import mock

        from harness import Agent, AgentOptions

        calls: list[int] = []

        def generate(_prompt: str) -> str:
            calls.append(1)
            return "Action: done\nSummary: stub"

        with mock.patch(
            "harness.agent.loop.make_generate", lambda *a, **k: ("stub", generate)
        ):
            result = Agent(
                AgentOptions(project=project, task=self.TASK, steps=2, **options)
            ).run()
        return result, len(calls)

    def test_a_green_suite_finishes_without_the_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project(tmp, with_tests=True)
            result, calls = self._run(project)
            fixed = (project / "src" / "orders.py").read_text(encoding="utf-8")
        self.assertTrue(result.ok)
        self.assertEqual(calls, 0)
        self.assertIn("return subtotal", fixed)

    def test_a_project_without_tests_is_not_treated_as_a_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result, calls = self._run(self._project(tmp, with_tests=False))
        self.assertTrue(result.ok)
        self.assertEqual(calls, 0)
        self.assertIn("no tests", result.summary)

    def test_the_summary_does_not_claim_the_fix_is_covered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result, _calls = self._run(self._project(tmp, with_tests=False))
        self.assertNotIn("Tests passed", result.summary)

    def test_a_read_only_run_changes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project(tmp, with_tests=True)
            before = (project / "src" / "orders.py").read_text(encoding="utf-8")
            result, _calls = self._run(project, allow_writes=False)
            after = (project / "src" / "orders.py").read_text(encoding="utf-8")
        self.assertEqual(before, after)
        self.assertEqual(result.writes, ())


if __name__ == "__main__":
    unittest.main()
