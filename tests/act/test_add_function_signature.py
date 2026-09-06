"""The mechanical adder must not invent a signature the task already gave.

`apply_add_function` writes a counter with zero model steps by copying
the argument its neighbours use. In an orders module that is `prices`,
and for `add a function total_lines` it is right.

Given *"create a new module with a function word_count(text) that counts
words"* it wrote:

    def word_count(prices: list[int]) -> int:
        return len(prices)

a word counter that counts list items. This path writes the test too, so
the suite agreed with it and the run reported "Tests passed" having done
the wrong thing without consulting the model once. Ten runs of ten.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.act.autofix.additions import apply_add_function  # noqa: E402

ORDERS = (
    '"""Order arithmetic."""\n\n\n'
    "def compute_total(prices: list[int]) -> int:\n"
    "    return sum(prices)\n"
)


class TheTaskOutranksTheNeighboursTest(unittest.TestCase):
    def _run(self, task: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "orders.py").write_text(ORDERS, encoding="utf-8")
            return apply_add_function(root, task, write=False)

    def test_it_refuses_when_the_task_spells_another_argument(self) -> None:
        self.assertEqual(
            self._run(
                "create a new module with a function word_count(text) that "
                "counts words, and a unit test for it"
            ),
            "",
        )

    def test_it_still_adds_when_the_task_spells_no_signature(self) -> None:
        """The case it was built for."""
        self.assertIn(
            "total_lines", self._run("add a function total_lines and a unit test")
        )

    def test_it_still_adds_when_the_spelled_argument_agrees(self) -> None:
        self.assertIn(
            "count_items",
            self._run("add a function count_items(prices) and a unit test"),
        )

    def test_an_annotated_argument_is_read_by_name(self) -> None:
        self.assertIn(
            "count_items",
            self._run("add a function count_items(prices: list[int]) and a test"),
        )

    def test_an_empty_bracket_pair_is_not_a_disagreement(self) -> None:
        """`total_lines()` names no argument, so there is nothing to
        contradict and the neighbour guess still stands."""
        self.assertIn(
            "total_lines", self._run("add a function total_lines() and a unit test")
        )


if __name__ == "__main__":
    unittest.main()
