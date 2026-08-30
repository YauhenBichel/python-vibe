"""Moving a file, and repairing what pointed at it."""

import tempfile
import unittest
from pathlib import Path

from harness.act.autofix import apply_file_move, move_targets


class MoveTargetsTest(unittest.TestCase):
    def test_it_reads_both_paths(self) -> None:
        self.assertEqual(
            move_targets("move src/a.py to src/b.py"), ("src/a.py", "src/b.py")
        )
        self.assertEqual(
            move_targets("rename src/old.py to src/new.py"),
            ("src/old.py", "src/new.py"),
        )

    def test_a_task_naming_one_path_is_not_a_move(self) -> None:
        self.assertIsNone(move_targets("delete src/a.py"))
        self.assertIsNone(move_targets("add a function total_lines"))

    def test_moving_a_file_onto_itself_is_not_a_move(self) -> None:
        self.assertIsNone(move_targets("move src/a.py to src/a.py"))


class ApplyMoveTest(unittest.TestCase):
    """Whoever asked has already decided; the work is mechanical.

    Asked to move a file, the harness used to spend twenty steps and
    change nothing. The part worth care is the imports: a moved module
    leaves every `from pkg.old import name` pointing at nothing.
    """

    def _project(self, tmp: str) -> Path:
        root = Path(tmp)
        (root / "pkg").mkdir()
        (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
        (root / "pkg" / "old.py").write_text(
            "def helper(x):\n    return x * 2\n", encoding="utf-8"
        )
        (root / "pkg" / "user.py").write_text(
            "from pkg.old import helper\n\n\ndef run(x):\n    return helper(x)\n",
            encoding="utf-8",
        )
        return root

    def test_the_file_moves_and_the_import_follows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            note = apply_file_move(root, "move pkg/old.py to pkg/new.py")
            moved = (root / "pkg" / "new.py").is_file()
            gone = not (root / "pkg" / "old.py").exists()
            user = (root / "pkg" / "user.py").read_text(encoding="utf-8")
        self.assertIn("moved", note)
        self.assertTrue(moved)
        self.assertTrue(gone, "the original was left behind")
        self.assertIn("from pkg.new import helper", user)
        self.assertNotIn("pkg.old", user)

    def test_the_project_still_runs_afterwards(self) -> None:
        """The point of repairing the imports."""
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            apply_file_move(root, "move pkg/old.py to pkg/new.py")
            done = subprocess.run(
                [sys.executable, "-c", "from pkg.user import run; print(run(21))"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.strip(), "42")

    def test_it_refuses_to_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            (root / "pkg" / "new.py").write_text("x = 1\n", encoding="utf-8")
            note = apply_file_move(root, "move pkg/old.py to pkg/new.py")
            kept = (root / "pkg" / "new.py").read_text(encoding="utf-8")
        self.assertEqual(note, "")
        self.assertEqual(kept, "x = 1\n", "an existing file was overwritten")

    def test_a_missing_source_is_not_a_move(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            self.assertEqual(
                apply_file_move(root, "move pkg/nothing.py to pkg/new.py"), ""
            )

    def test_it_stays_inside_the_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            note = apply_file_move(root, "move pkg/old.py to ../escaped.py")
            self.assertEqual(note, "")
            self.assertTrue((root / "pkg" / "old.py").is_file())

    def test_read_only_says_what_it_would_do(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            note = apply_file_move(root, "move pkg/old.py to pkg/new.py", write=False)
            self.assertIn("would move", note)
            self.assertTrue((root / "pkg" / "old.py").is_file())
            self.assertFalse((root / "pkg" / "new.py").exists())


if __name__ == "__main__":
    unittest.main()
