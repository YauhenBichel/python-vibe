"""Moving one function out of a file, and taking its callers with it.

#156 moved a whole file. Moving part of one is the job people actually
reach for when a module has grown too big — it is what splitting
`act/tools.py` into tools and a gate was — and doing it by hand means
finding every caller by eye.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.act.autofix.moves import (  # noqa: E402
    apply_function_move,
    function_move_targets,
)

TASK = "move the function shout out of pkg/loud.py into pkg/quiet.py"


def _project(tmp: str, *, destination: str = "x = 1\n") -> Path:
    root = Path(tmp)
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "loud.py").write_text(
        "def shout(word):\n    return word.upper()\n\n\n"
        "def whisper(word):\n    return word.lower()\n",
        encoding="utf-8",
    )
    (root / "pkg" / "quiet.py").write_text(destination, encoding="utf-8")
    return root


class ReadingTheTaskTest(unittest.TestCase):
    def test_the_long_way_of_saying_it(self) -> None:
        self.assertEqual(
            function_move_targets("move the function shout out of a/b.py into a/c.py"),
            ("shout", "a/b.py", "a/c.py"),
        )

    def test_the_short_way(self) -> None:
        self.assertEqual(
            function_move_targets("move shout from a/b.py to a/c.py"),
            ("shout", "a/b.py", "a/c.py"),
        )

    def test_a_whole_file_move_is_not_this(self) -> None:
        """The file-move rule owns that sentence; both must not fire."""
        self.assertIsNone(function_move_targets("move src/x.py to src/y.py"))

    def test_one_file_named_twice_is_not_a_move(self) -> None:
        self.assertIsNone(function_move_targets("move shout from a/b.py to a/b.py"))


class MovingItTest(unittest.TestCase):
    def test_the_definition_changes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp)
            note = apply_function_move(root, TASK)
            self.assertIn("moved shout", note)
            loud = (root / "pkg" / "loud.py").read_text(encoding="utf-8")
            quiet = (root / "pkg" / "quiet.py").read_text(encoding="utf-8")
            self.assertNotIn("def shout", loud)
            self.assertIn("def whisper", loud)
            self.assertIn("def shout", quiet)

    def test_a_caller_follows_the_function(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp)
            user = root / "pkg" / "user.py"
            user.write_text(
                "from pkg.loud import shout\n\n\ndef run(word):\n"
                "    return shout(word)\n",
                encoding="utf-8",
            )
            note = apply_function_move(root, TASK)
            self.assertIn("repaired 1 import", note)
            self.assertIn("from pkg.quiet import shout", user.read_text(encoding="utf-8"))

    def test_the_project_still_runs_afterwards(self) -> None:
        """The only check that matters: does the code still work."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp)
            (root / "pkg" / "user.py").write_text(
                "from pkg.loud import shout\n\n\ndef run(word):\n"
                "    return shout(word)\n",
                encoding="utf-8",
            )
            apply_function_move(root, TASK)
            done = subprocess.run(
                [sys.executable, "-c", "from pkg.user import run; print(run('hi'))"],
                cwd=root, capture_output=True, text=True, timeout=30, check=False,
            )
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(done.stdout.strip(), "HI")

    def test_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp)
            before = (root / "pkg" / "loud.py").read_text(encoding="utf-8")
            note = apply_function_move(root, TASK, write=False)
            self.assertIn("would move shout", note)
            self.assertEqual((root / "pkg" / "loud.py").read_text(encoding="utf-8"), before)


class RefusingWholeTest(unittest.TestCase):
    """A half-applied move leaves a project that does not import."""

    def test_a_name_the_destination_already_has(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp, destination="def shout(word):\n    return word\n")
            self.assertEqual(apply_function_move(root, TASK), "")
            self.assertIn("def shout", (root / "pkg" / "loud.py").read_text(encoding="utf-8"))

    def test_a_function_that_is_not_there(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp)
            self.assertEqual(
                apply_function_move(root, "move bellow from pkg/loud.py to pkg/quiet.py"),
                "",
            )

    def test_a_definition_that_would_lose_what_it_reads(self) -> None:
        """Carrying a function away from the import it needs breaks it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp)
            (root / "pkg" / "loud.py").write_text(
                "import re\n\n\ndef shout(word):\n"
                "    return re.sub(r'\\\\s+', ' ', word).upper()\n",
                encoding="utf-8",
            )
            self.assertEqual(apply_function_move(root, TASK), "")
            self.assertIn("def shout", (root / "pkg" / "loud.py").read_text(encoding="utf-8"))

    def test_the_same_move_when_the_destination_has_the_import(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp, destination="import re\n\nx = 1\n")
            (root / "pkg" / "loud.py").write_text(
                "import re\n\n\ndef shout(word):\n"
                "    return re.sub(r'\\\\s+', ' ', word).upper()\n",
                encoding="utf-8",
            )
            self.assertIn("moved shout", apply_function_move(root, TASK))

    def test_a_builtin_is_not_something_the_destination_must_have(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp)
            (root / "pkg" / "loud.py").write_text(
                "def shout(words):\n    return len(sorted(words))\n", encoding="utf-8"
            )
            self.assertIn("moved shout", apply_function_move(root, TASK))


if __name__ == "__main__":
    unittest.main()
