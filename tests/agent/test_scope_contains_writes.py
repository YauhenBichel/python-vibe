"""`--scope` must fence the writes, not only the reads.

The flag is documented as "work only inside this folder". It was
threaded into locate, map, glob and grep — every read — and never
reached patch or edit. So the one flag a person uses to keep the tool
away from the rest of a project did not keep it away from the part that
changes files.

A real run showed the cost. Given `--scope scripts` on a 259-file
repository, it left scope at step five, appended nonsense to
`tests/whole/test_bench.py`, corrupted a working stdlib import, and
finished with the suite broken and the asked-for function never written.
It reported only "stopped after 20 steps".
"""

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.agent.dispatch import refuse_outside_scope, run_action  # noqa: E402


class WhatIsInsideAndWhatIsNotTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "scripts" / "measure").mkdir(parents=True)
        (self.root / "tests" / "whole").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_a_file_outside_the_scope_is_refused(self) -> None:
        said = refuse_outside_scope(self.root, "scripts", "tests/whole/test_bench.py")
        self.assertIn("outside this run's scope", said)
        self.assertIn("scripts", said)

    def test_a_file_inside_the_scope_is_allowed(self) -> None:
        self.assertEqual(
            refuse_outside_scope(self.root, "scripts", "scripts/measure/bench.py"), ""
        )

    def test_a_nested_folder_of_the_scope_is_inside(self) -> None:
        self.assertEqual(
            refuse_outside_scope(self.root, "scripts", "scripts/measure/deep/x.py"), ""
        )

    def test_no_scope_allows_anything(self) -> None:
        """A run given no scope is a run over the whole project."""
        self.assertEqual(
            refuse_outside_scope(self.root, "", "tests/whole/test_bench.py"), ""
        )

    def test_the_whole_project_as_scope_allows_anything(self) -> None:
        self.assertEqual(
            refuse_outside_scope(self.root, ".", "tests/whole/test_bench.py"), ""
        )

    def test_climbing_out_with_dot_dot_is_refused(self) -> None:
        said = refuse_outside_scope(self.root, "scripts", "scripts/../tests/x.py")
        self.assertIn("outside this run's scope", said)

    def test_a_scope_that_does_not_resolve_is_left_to_its_own_error(self) -> None:
        """A bad scope is reported where it is set, not here — this rule
        must not turn it into a confusing refusal on every write."""
        self.assertEqual(
            refuse_outside_scope(self.root, "no_such_folder", "scripts/a.py"), ""
        )

    def test_no_path_is_not_this_rule(self) -> None:
        self.assertEqual(refuse_outside_scope(self.root, "scripts", ""), "")


class TheActionsAreActuallyStoppedTest(unittest.TestCase):
    """The rule being right is not the same as patch and edit using it."""

    BODY = '"""Module."""\n\n\ndef existing(values: list[int]) -> int:\n    return sum(values)\n'

    def _attempt(self, action: str) -> tuple[str, bool]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "tests").mkdir()
            victim = root / "tests" / "test_important.py"
            victim.write_text(self.BODY, encoding="utf-8")
            before = victim.read_text(encoding="utf-8")
            turn = SimpleNamespace(
                action=action, path="tests/test_important.py", find="",
                replace="", append="import atexit\n", source="x = 1\n",
                argv=(), summary="", name="", query="", pattern="",
                scope="", number="", title="", body="",
            )
            result, _ = run_action(root, turn, "", "scripts", None, task="add a function")
            return result, victim.read_text(encoding="utf-8") != before

    def test_patch_outside_the_scope_changes_nothing(self) -> None:
        said, changed = self._attempt("patch")
        self.assertFalse(changed, "the file outside the scope was written to")
        self.assertIn("outside this run's scope", said)

    def test_edit_outside_the_scope_changes_nothing(self) -> None:
        said, changed = self._attempt("edit")
        self.assertFalse(changed, "the file outside the scope was written to")
        self.assertIn("outside this run's scope", said)


if __name__ == "__main__":
    unittest.main()
