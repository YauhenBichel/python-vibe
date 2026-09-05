"""A file too long to send whole keeps the part the task is about.

Asked to add a field to a dict two thirds of the way down a
13,476-character file, the model was handed the first 3,500 characters
and the last 800. The dict was in neither. It then invented a `Find:`
line that was not in the file, was refused, and sent the same line
again — which reads like a model failing and was a harness handing over
the wrong excerpt.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.act.code import read_project_file  # noqa: E402
from harness.locate import subject_of  # noqa: E402

HEAD = "# top of the file\n" + ("# padding\n" * 700)
MIDDLE = 'ROW = {"case": case.key, "tier": case.tier}\n'
TAIL = ("# more padding\n" * 700) + "# end of the file\n"


def _long_file(tmp: str) -> Path:
    path = Path(tmp) / "big.py"
    path.write_text(HEAD + MIDDLE + TAIL, encoding="utf-8")
    return path


class ReadingTheSubjectOutOfTheTaskTest(unittest.TestCase):
    def test_a_dotted_name_is_the_subject(self) -> None:
        self.assertEqual(
            subject_of("add the field stopped, taking its value from result.stopped"),
            "result.stopped",
        )

    def test_the_longest_dotted_name_wins(self) -> None:
        self.assertEqual(subject_of("copy a.b into some.longer.name"), "some.longer.name")

    def test_a_file_name_is_not_a_subject(self) -> None:
        """`scripts/bench.py` says which file, not which line in it."""
        self.assertEqual(subject_of("fix scripts/bench.py for Windows"), "")

    def test_prose_has_no_subject(self) -> None:
        self.assertEqual(subject_of("tidy the project"), "")


class KeepingTheMiddleTest(unittest.TestCase):
    def test_without_a_subject_the_middle_is_lost(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            excerpt = read_project_file(_long_file(tmp))
            self.assertIn("# top of the file", excerpt)
            self.assertIn("# end of the file", excerpt)
            self.assertNotIn('"case": case.key', excerpt)

    def test_with_a_subject_the_middle_arrives(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            excerpt = read_project_file(_long_file(tmp), about='"case": case.key')
            self.assertIn('"case": case.key', excerpt)
            self.assertIn("# top of the file", excerpt)
            self.assertIn("# end of the file", excerpt)

    def test_a_subject_already_in_the_head_adds_nothing(self) -> None:
        """No second copy, and no window claiming to skip backwards."""
        with tempfile.TemporaryDirectory() as tmp:
            excerpt = read_project_file(_long_file(tmp), about="# top of the file")
            self.assertEqual(excerpt.count("# top of the file"), 1)
            self.assertEqual(excerpt.count("truncated"), 1)

    def test_a_subject_that_is_not_in_the_file_changes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _long_file(tmp)
            self.assertEqual(
                read_project_file(path, about="nothing.like.this"),
                read_project_file(path),
            )

    def test_a_short_file_is_sent_whole_either_way(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "small.py"
            path.write_text("x = 1\n", encoding="utf-8")
            self.assertEqual(read_project_file(path, about="x"), "x = 1\n")


class TheOpeningTurnCarriesItTest(unittest.TestCase):
    """Centring the excerpt is no use if the opening turn does not ask for it."""

    def test_the_preamble_keeps_the_dict_the_task_names(self) -> None:
        from harness.agent.options import AgentOptions
        from harness.agent.prompt import build_preamble

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "big.py").write_text(
                HEAD + MIDDLE + TAIL, encoding="utf-8"
            )
            pre = build_preamble(
                AgentOptions(
                    project=root,
                    task="in src/big.py add a field to the dict, from case.key",
                    allow_writes=False,
                )
            )
        self.assertIn('"case": case.key', pre.prompt)


if __name__ == "__main__":
    unittest.main()
