"""Draft shapes a chat model writes, and the bare one local weights write.

Two faults this week had one shape: the harness had quietly specialised
to the single model it runs itself. Local weights write `Action: patch`
on a line of its own, so an anchored pattern was enough — until the
benchmark was pointed at a hosted model, which emboldens the label,
numbers its steps, and explains the verb in the same breath. Every one
of those parsed to nothing and spent the turn.

This is a table on purpose. The next model that writes something new
should be one row, not a new test.
"""

import ast
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.act.parse import parse_turn_smart  # noqa: E402

CODE = "def slugify(text):\n    return text.lower()"

# label -> the draft, exactly as a model would send it
SHAPES = {
    "bare, as local weights write it": (
        f"Action: patch\nPath: src/orders.py\nAppend:\n{CODE}\n"
    ),
    "the code in a fence": (
        f"Action: patch\nPath: src/orders.py\nAppend:\n```python\n{CODE}\n```\n"
    ),
    "labels in bold": (
        f"**Action:** patch\n**Path:** src/orders.py\n**Append:**\n{CODE}\n"
    ),
    "the verb explained in the same breath": (
        f"Action: patch to add slugify\nPath: src/orders.py\nAppend:\n{CODE}\n"
    ),
    "a comment after the verb": (
        f"Action: patch - add the helper\nPath: src/orders.py\nAppend:\n{CODE}\n"
    ),
    "the whole reply in one fence": (
        f"```\nAction: patch\nPath: src/orders.py\nAppend:\n{CODE}\n```\n"
    ),
    "a sentence of preamble": (
        f"Sure! Here is the change.\n\nAction: patch\nPath: src/orders.py\n"
        f"Append:\n{CODE}\n"
    ),
    "numbered steps": (
        f"1. Action: patch\n2. Path: src/orders.py\nAppend:\n{CODE}\n"
    ),
    "a blockquote": (
        f"> Action: patch\n> Path: src/orders.py\nAppend:\n{CODE}\n"
    ),
}


class EveryShapeParsesTest(unittest.TestCase):
    def test_the_verb_is_read(self) -> None:
        for label, draft in SHAPES.items():
            with self.subTest(label):
                turn = parse_turn_smart(draft)
                self.assertIsNotNone(turn, "no turn at all")
                self.assertEqual(turn.action, "patch")

    def test_the_path_is_read(self) -> None:
        for label, draft in SHAPES.items():
            with self.subTest(label):
                self.assertEqual(parse_turn_smart(draft).path, "src/orders.py")

    def test_what_reaches_the_file_is_python(self) -> None:
        """The only check that matters. Backticks in the body are a
        SyntaxError, and a run then reads back its own wreckage."""
        for label, draft in SHAPES.items():
            with self.subTest(label):
                body = parse_turn_smart(draft).append
                self.assertNotIn("```", body)
                ast.parse(body)
                self.assertIn("return text.lower()", body)


class ADanglingFenceIsNotPythonTest(unittest.TestCase):
    def _append(self, draft: str) -> str:
        return parse_turn_smart(draft).append

    def test_a_bare_closing_fence_is_trimmed(self) -> None:
        body = self._append(f"Action: patch\nPath: src/o.py\nAppend:\n{CODE}\n```\n")
        ast.parse(body)

    def test_a_fence_the_model_opened_and_never_filled_is_trimmed(self) -> None:
        body = self._append(
            f"Action: patch\nPath: src/o.py\nAppend:\n{CODE}\n```python\n"
        )
        ast.parse(body)
        self.assertNotIn("```", body)


class DecorationDoesNotEatContentTest(unittest.TestCase):
    """The prefix allows `*`, `#`, `>` and list numbering — never `_`,
    because a value may legitimately begin with one."""

    def test_a_leading_underscore_in_a_name_survives(self) -> None:
        turn = parse_turn_smart("Action: edit\nName: _helpers\nPath: src/o.py\n")
        self.assertEqual(turn.name, "_helpers")

    def test_a_path_keeps_its_underscores(self) -> None:
        turn = parse_turn_smart("Action: read\nPath: src/my_long_name_.py\n")
        self.assertEqual(turn.path, "src/my_long_name_.py")

    def test_a_hyphenated_skill_is_still_a_verb(self) -> None:
        self.assertEqual(
            parse_turn_smart("Action: write-tests\nPath: src/o.py\n").action,
            "write-tests",
        )

    def test_argv_keeps_its_dashes(self) -> None:
        turn = parse_turn_smart("Action: run\nArgv: -m unittest discover -s tests -q\n")
        self.assertEqual(turn.argv[0], "-m")


if __name__ == "__main__":
    unittest.main()
