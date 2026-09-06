"""A draft must not delete the function the task is about.

Asked to *"fix the bug in last_price in src/orders.py"*, one run in five
rewrote the file without `last_price` in it. Nothing then failed: the
file still imported and the suite still passed, because there was no
longer anything to fail. The benchmark reported the function missing.

Deleting the subject is never the fix for "fix the bug in X", so the
rule is narrow on purpose — only the one name the task names, and never
when the task asks for a rename, a move or a removal, where the old name
is supposed to go.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.skillkit.refuse_change import refuse_dropped_definition  # noqa: E402

ORIGINAL = (
    '"""Order arithmetic."""\n\n\n'
    "def compute_total(prices: list[int]) -> int:\n"
    "    return sum(prices)\n\n\n"
    "def last_price(prices: list[int]) -> int:\n"
    "    return prices[len(prices)]\n"
)
WITHOUT_IT = (
    '"""Order arithmetic."""\n\n\n'
    "def compute_total(prices: list[int]) -> int:\n"
    "    return sum(prices)\n"
)
FIXED = ORIGINAL.replace("prices[len(prices)]", "prices[-1]")
BUGFIX = "fix the bug in last_price in src/orders.py: it raises IndexError on a full list"


class DroppingTheSubjectIsRefusedTest(unittest.TestCase):
    def test_a_draft_without_the_function_is_refused(self) -> None:
        said = refuse_dropped_definition(BUGFIX, "src/orders.py", ORIGINAL, WITHOUT_IT)
        self.assertIn("last_price", said)
        self.assertIn("src/orders.py", said)

    def test_the_refusal_says_what_to_do_instead(self) -> None:
        said = refuse_dropped_definition(BUGFIX, "src/orders.py", ORIGINAL, WITHOUT_IT)
        self.assertIn("Find:", said)
        self.assertIn("Replace:", said)

    def test_an_actual_fix_is_allowed(self) -> None:
        self.assertEqual(
            refuse_dropped_definition(BUGFIX, "src/orders.py", ORIGINAL, FIXED), ""
        )

    def test_a_lowercase_class_counts_too(self) -> None:
        original = "class ledger:\n    pass\n"
        task = "fix the bug in ledger in src/ledger.py"
        self.assertIn(
            "ledger",
            refuse_dropped_definition(task, "src/ledger.py", original, "x = 1\n"),
        )

    def test_a_camel_case_subject_is_not_covered(self) -> None:
        """Not a decision of this rule. `question_symbol` lower-cases,
        so it answers `ledger` for a class called `Ledger` and there is
        nothing here to match. Matching case-insensitively would refuse
        honest edits to a differently-cased name, so this rule covers
        what the harness can actually name, and no more."""
        original = "class Ledger:\n    pass\n"
        task = "fix the bug in Ledger in src/ledger.py"
        self.assertEqual(
            refuse_dropped_definition(task, "src/ledger.py", original, "x = 1\n"), ""
        )


class WhereTheNameIsMeantToGoTest(unittest.TestCase):
    """A rename, a move and a removal all take the old name away."""

    def _allows(self, task: str) -> bool:
        return not refuse_dropped_definition(
            task, "src/orders.py", ORIGINAL, WITHOUT_IT
        )

    def test_a_rename_may_drop_it(self) -> None:
        self.assertTrue(self._allows("rename last_price to final_price in src/orders.py"))

    def test_a_move_may_drop_it(self) -> None:
        self.assertTrue(self._allows("move last_price into src/prices.py"))

    def test_a_removal_may_drop_it(self) -> None:
        self.assertTrue(self._allows("remove last_price from src/orders.py"))


class WhatItLeavesAloneTest(unittest.TestCase):
    def test_a_function_that_was_never_there(self) -> None:
        self.assertEqual(
            refuse_dropped_definition(BUGFIX, "src/orders.py", WITHOUT_IT, WITHOUT_IT),
            "",
        )

    def test_a_task_that_names_no_symbol(self) -> None:
        self.assertEqual(
            refuse_dropped_definition("tidy up", "src/orders.py", ORIGINAL, WITHOUT_IT),
            "",
        )

    def test_a_file_that_is_not_python(self) -> None:
        self.assertEqual(
            refuse_dropped_definition(BUGFIX, "README.md", ORIGINAL, WITHOUT_IT), ""
        )

    def test_another_function_going_is_not_this_rule(self) -> None:
        """Only the subject. `compute_total` leaving is somebody else's
        rule, and pretending otherwise would refuse honest edits."""
        without_other = ORIGINAL.replace(
            "def compute_total(prices: list[int]) -> int:\n    return sum(prices)\n\n\n",
            "",
        )
        self.assertEqual(
            refuse_dropped_definition(BUGFIX, "src/orders.py", ORIGINAL, without_other),
            "",
        )


if __name__ == "__main__":
    unittest.main()
