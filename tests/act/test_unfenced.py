"""A model that answers in chat wraps its code in a fence.

Local weights happen not to. Every hosted one does — so the harness had
a fault that only appeared the moment it was pointed at a model it does
not run itself. A hosted 32B scored one of ten because its `Append:`
bodies reached the file with the backticks still on them, and by its
third turn it was reporting an unterminated string literal in a file it
had broken itself.
"""

import ast
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.act.parse import parse_turn_smart, unfenced  # noqa: E402

CODE = "def slugify(text):\n    return text.lower()"


class TakingTheFenceOffTest(unittest.TestCase):
    def test_a_fence_with_a_language(self) -> None:
        self.assertEqual(unfenced(f"```python\n{CODE}\n```"), CODE)

    def test_a_fence_without_one(self) -> None:
        self.assertEqual(unfenced(f"```\n{CODE}\n```"), CODE)

    def test_code_with_no_fence_is_untouched(self) -> None:
        self.assertEqual(unfenced(CODE), CODE)

    def test_an_empty_body_stays_empty(self) -> None:
        self.assertEqual(unfenced(""), "")

    def test_backticks_inside_the_code_are_not_a_fence(self) -> None:
        """A docstring may mention them; only a wrapper counts."""
        body = 'def show():\n    """Use ```python for a block."""\n    return 1'
        self.assertEqual(unfenced(body), body)

    def test_a_lone_opening_fence_is_not_a_wrapper(self) -> None:
        half = f"```python\n{CODE}"
        self.assertEqual(unfenced(half), half)

    def test_a_sign_off_after_the_fence_is_dropped(self) -> None:
        """The sentence after the fence breaks the file as surely as
        the backticks do, so the closing fence ends the code."""
        self.assertEqual(
            unfenced(f"```python\n{CODE}\n```\nThat should do it."), CODE
        )

    def test_an_indented_fence_is_still_a_fence(self) -> None:
        self.assertEqual(unfenced(f"  ```python\n{CODE}\n  ```"), CODE)

    def test_the_first_closing_fence_ends_the_code(self) -> None:
        """A model that shows two blocks means the first one.

        Reading to the last fence instead swallows the prose between
        them, and the prose is not Python.
        """
        two = (
            f"```python\n{CODE}\n```\n"
            "And here is how you would call it:\n"
            "```python\nslugify('Hi')\n```"
        )
        self.assertEqual(unfenced(two), CODE)


class WhatReachesTheFileTest(unittest.TestCase):
    """The only check that matters: does what lands parse as Python."""

    def _append(self, draft: str) -> str:
        turn = parse_turn_smart(draft)
        return (turn.append or "") if turn else ""

    def test_a_fenced_append_lands_as_python(self) -> None:
        body = self._append(
            f"Action: patch\nPath: src/orders.py\nAppend:\n```python\n{CODE}\n```\n"
        )
        ast.parse(body)
        self.assertNotIn("```", body)

    def test_a_plain_append_still_lands(self) -> None:
        body = self._append(f"Action: patch\nPath: src/orders.py\nAppend:\n{CODE}\n")
        ast.parse(body)

    def test_an_append_with_a_sign_off_lands_as_python(self) -> None:
        """The shape that cost a hosted 32B nine runs of ten."""
        body = self._append(
            "Action: patch\nPath: src/orders.py\nAppend:\n"
            f"```python\n{CODE}\n```\nThat should do it.\n"
        )
        ast.parse(body)
        self.assertNotIn("That should do it", body)

    def test_a_fenced_find_and_replace_land_too(self) -> None:
        turn = parse_turn_smart(
            "Action: patch\nPath: src/orders.py\n"
            "Find:\n```python\n    return 0\n```\n"
            "Replace:\n```python\n    return sum(rows)\n```\n"
        )
        self.assertNotIn("```", turn.find)
        self.assertNotIn("```", turn.replace)
        self.assertIn("return sum(rows)", turn.replace)


if __name__ == "__main__":
    unittest.main()
