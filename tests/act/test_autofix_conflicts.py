"""Resolving a merge conflict where keeping both sides is safe."""

import unittest
from pathlib import Path
from harness.act.autofix import conflict_blocks, resolve_keeping_both
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


class ResolveConflictTest(unittest.TestCase):
    """Two branches that each added something is the safe case.

    Given a real conflict, a live 8B spent twenty steps and left all
    three markers in the file. Given a file with no conflict at all, it
    reported the conflict resolved. Neither of those needed a model.
    """

    CONFLICT = (
        "import unittest\n"
        "<<<<<<< HEAD\n"
        "from a import one\n"
        "=======\n"
        "from b import two\n"
        ">>>>>>> origin/main\n"
    )

    def test_both_sides_are_kept(self) -> None:
        merged = resolve_keeping_both(self.CONFLICT)
        self.assertIn("from a import one", merged)
        self.assertIn("from b import two", merged)
        self.assertNotIn("<<<<<<<", merged)

    def test_a_deletion_against_an_edit_is_left_alone(self) -> None:
        """Which side is wanted there is not something to guess."""
        source = "x = 1\n<<<<<<< HEAD\n=======\ny = 2\n>>>>>>> main\n"
        self.assertEqual(resolve_keeping_both(source), "")

    def test_a_merge_that_would_not_parse_is_refused(self) -> None:
        source = (
            "<<<<<<< HEAD\n"
            "def f():\n    return 1\n"
            "=======\n"
            "    else:\n        pass\n"
            ">>>>>>> main\n"
        )
        self.assertEqual(resolve_keeping_both(source), "")

    def test_a_file_with_no_conflict_says_so(self) -> None:
        self.assertEqual(resolve_keeping_both("x = 1\n"), "")
        self.assertEqual(conflict_blocks("x = 1\n"), [])

    def test_definitions_get_air_between_them(self) -> None:
        source = (
            "<<<<<<< HEAD\n"
            "def one():\n    return 1\n"
            "=======\n"
            "def two():\n    return 2\n"
            ">>>>>>> main\n"
        )
        merged = resolve_keeping_both(source)
        self.assertIn("return 1\n\n\ndef two", merged)


if __name__ == "__main__":
    unittest.main()
