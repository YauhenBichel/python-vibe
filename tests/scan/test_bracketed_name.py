"""The subject of a task is the name that was typed with brackets.

Asked to *"create a new module with a function word_count(text) that
counts words"*, the harness read left to right and answered `module` — a
noun out of the instruction, not the thing being asked for. A run then
wrote a function literally called `module`, and said so in its own
summary: "Added a new function `word_count`... and a function `module`
to count occurrences".

Eleven of the fifteen benchmark tasks spell the subject with brackets,
and it is the right answer every time, so preferring it is a rule rather
than a patch.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.task import question_symbol  # noqa: E402


class TheNameInBracketsWinsTest(unittest.TestCase):
    def test_it_beats_a_noun_from_the_instruction(self) -> None:
        self.assertEqual(
            question_symbol(
                "create a new module with a function word_count(text) that "
                "counts words"
            ),
            "word_count",
        )

    def test_the_same_for_a_one_word_name(self) -> None:
        self.assertEqual(
            question_symbol(
                "create a new module with a function slugify(text) that "
                "lowercases and joins with hyphens"
            ),
            "slugify",
        )

    def test_a_space_before_the_bracket_is_still_a_call(self) -> None:
        """Phrased so the fallback would answer `module`, not `tally`,
        which is what makes this a test of the space rather than of the
        rule that happens to agree with it."""
        self.assertEqual(
            question_symbol("create a new module with a function tally (rows)"),
            "tally",
        )

    def test_the_first_bracketed_name_wins(self) -> None:
        """The task names what to write before what to write it with."""
        self.assertEqual(
            question_symbol("add a function retry(action, times) that calls action()"),
            "retry",
        )


class WhatItMustNotBreakTest(unittest.TestCase):
    def test_a_task_with_no_brackets_is_unchanged(self) -> None:
        self.assertEqual(
            question_symbol("write a unit test for apply_discount in src/orders.py"),
            "apply_discount",
        )

    def test_a_question_still_reads_the_verb_form(self) -> None:
        self.assertEqual(question_symbol("what does apply_source refuse?"), "apply_source")
        self.assertEqual(question_symbol("what does add return?"), "add")

    def test_an_opening_verb_in_brackets_is_still_skipped(self) -> None:
        """`_SYMBOL_SKIP` applies to a bracketed name too, or `create(`
        would become the subject of every greenfield task."""
        self.assertEqual(
            question_symbol("create(a) new module with a function tally(rows)"),
            "tally",
        )

    def test_a_bug_fix_task_keeps_its_subject(self) -> None:
        self.assertEqual(
            question_symbol(
                "fix the bug in last_price in src/orders.py: it raises IndexError"
            ),
            "last_price",
        )


if __name__ == "__main__":
    unittest.main()
