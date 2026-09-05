"""A named-file bugfix whose test already covers the symbol is impl-first.

Live 8B on the everyday-ready fixture rewrote tests/test_util_stats.py
and never patched compute_total. The loop must refuse that write and
point back at the named file.
"""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from harness.agent.policy import (
    LoopState,
    next_prompt,
    refuse_before,
    repair_after_failed_run,
)
from harness.locate import refuse_bugfix_explore, refuse_bugfix_tests_first

ROOT = Path(__file__).resolve().parents[2]
EVERYDAY = ROOT / "eval" / "fixtures" / "everyday_fix"
TASK = "fix compute_total in pkg/util_stats.py so it sums the rows"


class _Turn:
    def __init__(self, action: str, path: str = "") -> None:
        self.action = action
        self.path = path
        self.summary = ""
        self.find = ""


class BugfixImplFirstTest(unittest.TestCase):
    def test_existing_test_write_is_refused(self) -> None:
        blocked = refuse_bugfix_tests_first(
            TASK, EVERYDAY, "edit", "tests/test_util_stats.py"
        )
        self.assertIn("pkg/util_stats.py", blocked)
        self.assertIn("compute_total", blocked)

    def test_named_impl_write_is_allowed(self) -> None:
        self.assertEqual(
            refuse_bugfix_tests_first(TASK, EVERYDAY, "edit", "pkg/util_stats.py"),
            "",
        )

    def test_a_bugfix_without_a_covering_test_may_write_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pkg").mkdir()
            (root / "tests").mkdir()
            (root / "pkg" / "util_stats.py").write_text(
                "def compute_total(rows):\n    return 0.0\n",
                encoding="utf-8",
            )
            (root / "tests" / "test_other.py").write_text(
                "import unittest\nclass T(unittest.TestCase):\n"
                "    def test_ok(self) -> None:\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            self.assertEqual(
                refuse_bugfix_tests_first(
                    TASK, root, "edit", "tests/test_util_stats.py"
                ),
                "",
            )

    def test_refuse_before_blocks_the_everyday_test_path(self) -> None:
        state = LoopState(task=TASK, project=EVERYDAY)
        blocked = refuse_before(state, _Turn("edit", "tests/test_util_stats.py"))
        self.assertIn("pkg/util_stats.py", blocked)
        self.assertIn("compute_total", blocked)

    def test_after_read_the_next_step_is_the_named_impl(self) -> None:
        state = LoopState(task=TASK, project=EVERYDAY)
        got = next_prompt(
            state,
            SimpleNamespace(action="read", path="pkg/util_stats.py"),
            "ok",
        )
        self.assertIn("pkg/util_stats.py", got)
        self.assertIn("patch", got)
        self.assertNotIn("tests/test_util_stats.py", got)

    def test_repair_names_the_impl_not_the_test(self) -> None:
        state = LoopState(
            task=TASK,
            project=EVERYDAY,
            last_path="tests/test_util_stats.py",
            wrote_something=True,
        )
        got = repair_after_failed_run(state, "exit 1\nFAIL: compute_total")
        self.assertIn("pkg/util_stats.py", got)
        self.assertNotIn("tests/test_util_stats.py", got)

    def test_writing_the_test_still_nudges_the_impl(self) -> None:
        state = LoopState(task=TASK, project=EVERYDAY, wrote_something=True)
        got = next_prompt(
            state,
            SimpleNamespace(action="edit", path="tests/test_util_stats.py"),
            "wrote tests/test_util_stats.py",
        )
        self.assertIn("pkg/util_stats.py", got)
        self.assertIn("patch", got)

    def test_explore_is_refused_once_the_named_file_is_open(self) -> None:
        blocked = refuse_bugfix_explore(
            TASK, EVERYDAY, "grep", located_path="pkg/util_stats.py"
        )
        self.assertIn("pkg/util_stats.py", blocked)
        self.assertIn("patch", blocked)
        self.assertEqual(
            refuse_bugfix_explore(TASK, EVERYDAY, "read", located_path=""),
            "",
        )
        self.assertIn(
            "patch",
            refuse_bugfix_explore(
                TASK, EVERYDAY, "read", located_path="pkg/util_stats.py"
            ),
        )
        self.assertEqual(
            refuse_bugfix_explore(
                "add multiply(a, b) and a test",
                EVERYDAY,
                "grep",
                located_path="pkg/util_stats.py",
            ),
            "",
        )

    def test_refuse_before_blocks_grep_after_prelude(self) -> None:
        state = LoopState(
            task=TASK, project=EVERYDAY, located_path="pkg/util_stats.py"
        )
        blocked = refuse_before(state, _Turn("grep"))
        self.assertIn("pkg/util_stats.py", blocked)
        self.assertIn("patch", blocked)


if __name__ == "__main__":
    unittest.main()
