"""Behaviour that differs between operating systems.

Windows renders relative paths with backslashes and puts a virtual
environment's interpreter in a different directory. The model is shown
paths and copies them back, and the skills and prompts are all written with
forward slashes, so the two styles must not mix.
"""

import tempfile
import unittest
from pathlib import Path

from harness.act.tools import glob_py, grep_py, map_py
from harness.paths import as_project_rel, rel_posix, venv_python
from harness.scan.project_brief import classify_project, render_brief

MODULE = "def compute_total(rows: list[int]) -> int:\n    return sum(rows)\n"


def _project(tmp: str) -> Path:
    root = Path(tmp)
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "src" / "app.py").write_text(MODULE, encoding="utf-8")
    (root / "tests" / "test_app.py").write_text("x = 1\n", encoding="utf-8")
    return root


class RelPosixTest(unittest.TestCase):
    def test_forward_slashes_on_any_platform(self) -> None:
        self.assertEqual(rel_posix(Path("/a/b/c.py"), Path("/a")), "b/c.py")

    def test_a_windows_style_path_is_accepted_as_input(self) -> None:
        self.assertEqual(as_project_rel("src\\app.py"), "src/app.py")

    def test_a_leading_dot_slash_is_removed(self) -> None:
        self.assertEqual(as_project_rel("./src/app.py"), "src/app.py")

    def test_a_plain_path_is_unchanged(self) -> None:
        self.assertEqual(as_project_rel("src/app.py"), "src/app.py")


class RenderedPathTest(unittest.TestCase):
    """Nothing the model reads may contain a backslash separator."""

    def _assert_posix(self, text: str) -> None:
        for line in text.splitlines():
            self.assertNotIn(
                "\\", line, f"backslash in output the model reads: {line!r}"
            )

    def test_brief_uses_forward_slashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = _project(tmp)
            self._assert_posix(render_brief(classify_project(project)))

    def test_map_uses_forward_slashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._assert_posix(map_py(_project(tmp)))

    def test_grep_uses_forward_slashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._assert_posix(grep_py(_project(tmp), "compute_total"))

    def test_glob_uses_forward_slashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._assert_posix(glob_py(_project(tmp), "**/*.py"))

    def test_a_listed_path_can_be_read_back(self) -> None:
        """A path the model is shown must work when it copies it into Path:."""
        from harness.act.tools import read_py

        with tempfile.TemporaryDirectory() as tmp:
            project = _project(tmp)
            for line in map_py(project).splitlines():
                candidate = line.strip().split("  ")[0]
                if candidate.endswith(".py"):
                    # Not a crash and not empty: the path round-tripped.
                    self.assertTrue(read_py(project, candidate).strip())


class VenvPythonTest(unittest.TestCase):
    def test_posix_layout(self) -> None:
        found = venv_python(Path("/p/.venv"), windows=False)
        self.assertEqual(found.name, "python")
        self.assertEqual(found.parent.name, "bin")

    def test_windows_layout(self) -> None:
        found = venv_python(Path("/p/.venv"), windows=True)
        self.assertEqual(found.name, "python.exe")
        self.assertEqual(found.parent.name, "Scripts")

    def test_the_default_follows_the_running_platform(self) -> None:
        import os as _os

        expected = "python.exe" if _os.name == "nt" else "python"
        self.assertEqual(venv_python(Path("/p/.venv")).name, expected)


class NamedFileTest(unittest.TestCase):
    """A task that names a file has already said which file to open."""

    TASK = (
        "in src/app.py the venv python path uses bin/python which only "
        "exists on macOS and Linux; fix it for Windows too"
    )

    def test_the_named_file_is_found(self) -> None:
        from harness.task import named_project_file

        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(named_project_file(self.TASK, _project(tmp)), "src/app.py")

    def test_a_backslash_path_in_the_task_is_understood(self) -> None:
        from harness.task import task_paths

        self.assertEqual(task_paths("fix src\\app.py please"), ("src/app.py",))

    def test_a_write_to_another_file_is_refused(self) -> None:
        from harness.agent.policy import refuse_wrong_file

        with tempfile.TemporaryDirectory() as tmp:
            project = _project(tmp)
            blocked = refuse_wrong_file(self.TASK, project, "patch", "src/other.py")
        self.assertIn("src/app.py", blocked)

    def test_a_write_to_the_named_file_is_allowed(self) -> None:
        from harness.agent.policy import refuse_wrong_file

        with tempfile.TemporaryDirectory() as tmp:
            project = _project(tmp)
            self.assertEqual(
                refuse_wrong_file(self.TASK, project, "patch", "src/app.py"), ""
            )

    def test_a_task_naming_no_file_is_not_restricted(self) -> None:
        from harness.agent.policy import refuse_wrong_file

        with tempfile.TemporaryDirectory() as tmp:
            project = _project(tmp)
            self.assertEqual(
                refuse_wrong_file("add multiply(a, b)", project, "patch", "src/app.py"),
                "",
            )

    def test_the_prelude_opens_the_named_file(self) -> None:
        from harness.locate import prelude

        with tempfile.TemporaryDirectory() as tmp:
            text, path = prelude(_project(tmp), self.TASK)
        self.assertEqual(path, "src/app.py")
        self.assertIn("compute_total", text)
        self.assertIn("Only src/app.py may be changed", text)
        self.assertIn("Next Action must be patch", text)


class DoneWithoutChangeTest(unittest.TestCase):
    """A change task that finishes having changed nothing is refused once."""

    def _state(self, project, task):
        from harness.agent.policy import LoopState

        return LoopState(task=task, project=project)

    def test_refused_when_nothing_was_written(self) -> None:
        from harness.agent.policy import refuse_done_without_change

        with tempfile.TemporaryDirectory() as tmp:
            project = _project(tmp)
            state = self._state(project, "fix src/app.py for Windows")
            self.assertIn("Nothing was changed", refuse_done_without_change(state, None))

    def test_allowed_after_a_write(self) -> None:
        from harness.agent.policy import refuse_done_without_change

        with tempfile.TemporaryDirectory() as tmp:
            state = self._state(_project(tmp), "fix src/app.py for Windows")
            state.wrote_something = True
            self.assertEqual(refuse_done_without_change(state, None), "")

    def test_refused_only_once(self) -> None:
        from harness.agent.policy import refuse_done_without_change

        with tempfile.TemporaryDirectory() as tmp:
            state = self._state(_project(tmp), "fix src/app.py for Windows")
            self.assertNotEqual(refuse_done_without_change(state, None), "")
            self.assertEqual(refuse_done_without_change(state, None), "")

    def test_a_question_is_never_refused_for_not_writing(self) -> None:
        from harness.agent.policy import refuse_done_without_change

        with tempfile.TemporaryDirectory() as tmp:
            state = self._state(_project(tmp), "what does compute_total return?")
            self.assertEqual(refuse_done_without_change(state, None), "")


if __name__ == "__main__":
    unittest.main()
