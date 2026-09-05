"""Saying what the project already has, before the model writes another.

A run asked to check a prompt for a leaked credential wrote its own
worse copy of a check that was three files away. The words the task used
were in the tree already; the twelve-thousand-character preamble named
neither the file nor the function, so the model had no way to know.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.scan.existing import already_covers, existing_files, phrases  # noqa: E402


def _project(tmp: str) -> Path:
    root = Path(tmp)
    (root / "src").mkdir()
    (root / "tests").mkdir()
    return root


class ReadingTheTaskTest(unittest.TestCase):
    def test_filler_makes_no_phrase(self) -> None:
        """"add a function" matches everything and points at nothing."""
        self.assertEqual(phrases("add a function and a test for it"), [])

    def test_a_subject_makes_a_phrase(self) -> None:
        self.assertIn("access key", phrases("refuse an access key in the prompt"))

    def test_single_letters_are_not_a_phrase(self) -> None:
        self.assertEqual(phrases("map a to b"), [])


class SayingWhereItIsTest(unittest.TestCase):
    def test_a_rare_phrase_is_reported_with_its_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp)
            (root / "src" / "keys.py").write_text(
                '# shapes\nSHAPES = [("an access key", "AKIA")]\n', encoding="utf-8"
            )
            found = already_covers(root, "refuse an access key in the prompt")
            self.assertIn("access key", found)
            self.assertIn("src/keys.py:2", found)
            self.assertEqual(
                existing_files(root, "refuse an access key in the prompt"),
                ("src/keys.py",),
            )

    def test_a_phrase_in_no_file_says_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp)
            (root / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
            self.assertEqual(already_covers(root, "refuse an access key"), "")

    def test_a_phrase_in_many_files_is_common_vocabulary(self) -> None:
        """Everywhere is the same as nowhere, for a pointer."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp)
            for name in ("a", "b", "c", "d", "e"):
                (root / "src" / f"{name}.py").write_text(
                    "# order total here\n", encoding="utf-8"
                )
            self.assertEqual(already_covers(root, "work out the order total"), "")

    def test_the_file_being_changed_is_not_news(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp)
            (root / "src" / "keys.py").write_text(
                'SHAPES = ["an access key"]\n', encoding="utf-8"
            )
            self.assertEqual(
                already_covers(root, "refuse an access key", skip="src/keys.py"), ""
            )

    def test_a_test_file_is_not_a_capability(self) -> None:
        """Tests name every subject in a project, so they point at nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp)
            (root / "tests" / "test_keys.py").write_text(
                '"""an access key is refused."""\n', encoding="utf-8"
            )
            self.assertEqual(already_covers(root, "refuse an access key"), "")

    def test_it_does_not_find_itself(self) -> None:
        """A search that matches its own source reports itself.

        The first version of this module quoted the words the real case
        turned on, which made it a hit for its own search and pushed the
        right answer out of the ranking.
        """
        root = Path(__file__).resolve().parents[2]
        source = (root / "src" / "harness" / "scan" / "existing.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("github token", source.lower())



class TheModelIsActuallyToldTest(unittest.TestCase):
    """Finding the pointer is no use if the preamble leaves it out."""

    def test_the_preamble_carries_the_pointer(self) -> None:
        from harness.agent.options import AgentOptions
        from harness.agent.prompt import build_preamble

        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp)
            (root / "src" / "keys.py").write_text(
                'SHAPES = ["an access key"]\n', encoding="utf-8"
            )
            (root / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
            pre = build_preamble(
                AgentOptions(
                    project=root,
                    task="refuse an access key in src/app.py",
                    allow_writes=False,
                )
            )
        # Not "access key" — that is in the task, and not `src/keys.py`
        # either, which the project map lists anyway. The first version
        # of this test asserted both and passed with the pointer removed.
        self.assertIn("already has something for what the task names", pre.prompt)
        self.assertIn('"access key" is already in src/keys.py', pre.prompt)


if __name__ == "__main__":
    unittest.main()
