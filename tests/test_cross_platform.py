"""Behaviour that differs between operating systems.

Windows renders relative paths with backslashes and puts a virtual
environment's interpreter in a different directory. The model is shown
paths and copies them back, and the skills and prompts are all written with
forward slashes, so the two styles must not mix.
"""

import re
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from harness.act.tools import glob_py, grep_py, map_py
from harness.paths import as_project_rel, rel_posix, venv_python
from harness.scan.project_brief import classify_project, render_brief

@dataclass
class _Turn:
    """The one field these rules read off a model turn."""

    summary: str


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

    def test_saying_it_is_already_correct_is_not_enough(self) -> None:
        """The escape hatch was a sentence the refusal handed the model.

        A real run, refused once for changing nothing, came back with
        "The line is already correct." That names no line. It was
        accepted, and the run reported success having written nothing.
        """
        from harness.agent.policy import refuse_done_without_change

        with tempfile.TemporaryDirectory() as tmp:
            state = self._state(_project(tmp), "fix src/app.py for Windows")
            self.assertIn("Nothing was changed",
                          refuse_done_without_change(state, None))
            second = refuse_done_without_change(state, _Turn("The line is already correct."))
            self.assertIn("copies no line", second)

    def test_quoting_a_line_from_the_file_is_enough(self) -> None:
        """A file that needs no change is a real answer, shown not asserted."""
        from harness.agent.policy import refuse_done_without_change

        with tempfile.TemporaryDirectory() as tmp:
            state = self._state(_project(tmp), "fix src/app.py for Windows")
            refuse_done_without_change(state, None)
            turn = _Turn("Already correct: def compute_total(rows: list[int]) -> int:")
            self.assertEqual(refuse_done_without_change(state, turn), "")

    def test_the_run_stops_claiming_success_when_it_cannot_show_a_line(self) -> None:
        from harness.agent.policy import done_without_proof, refuse_done_without_change

        with tempfile.TemporaryDirectory() as tmp:
            state = self._state(_project(tmp), "fix src/app.py for Windows")
            unproven = _Turn("The line is already correct.")
            refuse_done_without_change(state, unproven)
            self.assertIn("unfinished", done_without_proof(state, unproven))

    def test_a_shown_line_still_finishes_as_done(self) -> None:
        from harness.agent.policy import done_without_proof, refuse_done_without_change

        with tempfile.TemporaryDirectory() as tmp:
            state = self._state(_project(tmp), "fix src/app.py for Windows")
            refuse_done_without_change(state, None)
            turn = _Turn("Already correct: def compute_total(rows: list[int]) -> int:")
            self.assertEqual(done_without_proof(state, turn), "")

    def test_a_line_short_enough_to_be_a_coincidence_is_not_proof(self) -> None:
        """`x = 1` and `return` are in half the files in any project.

        Without a minimum length, a summary that happens to contain one
        counts as having read the file, which is the whole thing this is
        meant to establish.
        """
        from harness.agent.policy import quotes_a_line_from

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "m.py").write_text(
                "x = 1\ndef total(rows: list[int]) -> int:\n", encoding="utf-8"
            )
            self.assertFalse(quotes_a_line_from("already correct: x = 1", root, "m.py"))
            self.assertTrue(
                quotes_a_line_from(
                    "already correct: def total(rows: list[int]) -> int:",
                    root,
                    "m.py",
                )
            )

    def test_a_name_the_task_is_about_that_is_not_in_the_file(self) -> None:
        """Quoting a line proves reading. It does not prove reading the right one.

        A run asked to add `result.stopped` cleared the quote bar with
        `if __name__ == "__main__":`, which is in every script ever
        written. Nothing can be already correct about adding a name that
        is not there.
        """
        from harness.agent.policy import missing_from_file

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "m.py").write_text(
                'result = go()\nif __name__ == "__main__":\n    main()\n',
                encoding="utf-8",
            )
            self.assertEqual(
                missing_from_file("add result.stopped to m.py", root, "m.py"),
                "result.stopped",
            )
            self.assertEqual(
                missing_from_file("add result.stopped to m.py", root, "gone.py"), ""
            )

    def test_prose_is_not_treated_as_a_name(self) -> None:
        """Only dotted or underscored words are things a file can lack."""
        from harness.agent.policy import missing_from_file

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "m.py").write_text("x = 1\n", encoding="utf-8")
            self.assertEqual(missing_from_file("fix m.py for Windows", root, "m.py"), "")

    def test_an_absent_name_beats_a_quoted_line(self) -> None:
        from harness.agent.policy import refuse_done_without_change

        with tempfile.TemporaryDirectory() as tmp:
            project = _project(tmp)
            state = self._state(project, "add compute_total.cached to src/app.py")
            refuse_done_without_change(state, None)
            quoted = _Turn("already correct: def compute_total(rows: list[int]) -> int:")
            self.assertIn("copies no line", refuse_done_without_change(state, quoted))

    def test_a_file_that_is_not_there_proves_nothing(self) -> None:
        from harness.agent.policy import quotes_a_line_from

        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(quotes_a_line_from("anything", Path(tmp), "gone.py"))

    def test_a_write_is_never_second_guessed(self) -> None:
        from harness.agent.policy import done_without_proof

        with tempfile.TemporaryDirectory() as tmp:
            state = self._state(_project(tmp), "fix src/app.py for Windows")
            state.wrote_something = True
            self.assertEqual(done_without_proof(state, _Turn("changed it")), "")

    def test_a_question_is_never_refused_for_not_writing(self) -> None:
        from harness.agent.policy import refuse_done_without_change

        with tempfile.TemporaryDirectory() as tmp:
            state = self._state(_project(tmp), "what does compute_total return?")
            self.assertEqual(refuse_done_without_change(state, None), "")


class AstNodesExistOnTheOldestPythonTest(unittest.TestCase):
    """`ast` grew node types after 3.11, and pyproject supports 3.11.

    `ast.TypeAlias` is 3.12. Naming it in an isinstance check raised
    AttributeError on every 3.11 job while passing locally on 3.13, so
    the break was invisible until CI ran. Look such names up with
    getattr and skip the check when the attribute is missing.
    """

    # Added in 3.12 (PEP 695) and 3.13. Anything here is unavailable on 3.11.
    TOO_NEW = ("TypeAlias", "TypeVar", "ParamSpec", "TypeVarTuple", "TypeIs")

    def test_no_module_names_a_node_type_newer_than_3_11(self) -> None:
        pattern = re.compile(r"\bast\.(" + "|".join(self.TOO_NEW) + r")\b")
        offenders = []
        for path in sorted((ROOT / "src").rglob("*.py")):
            for number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            ):
                if pattern.search(line) and "getattr(ast" not in line:
                    offenders.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()}")
        self.assertEqual(offenders, [], offenders)

    def test_the_checker_still_works_without_the_3_12_node(self) -> None:
        """Simulate 3.11: the module must import and behave."""
        import ast as ast_module
        import importlib

        from harness.scan import names as names_module

        saved = getattr(ast_module, "TypeAlias", None)
        try:
            if saved is not None:
                del ast_module.TypeAlias
            reloaded = importlib.reload(names_module)
            self.assertIsNone(reloaded._TYPE_ALIAS)
            source = (
                "from typing import TYPE_CHECKING\n\n"
                "if TYPE_CHECKING:\n"
                "    from rich.markdown import Markdown\n\n\n"
                "def build(text: str) -> 'Markdown':\n"
                "    return text\n"
            )
            self.assertEqual(reloaded.undefined_names(source), [])
        finally:
            if saved is not None:
                ast_module.TypeAlias = saved
            importlib.reload(names_module)


if __name__ == "__main__":
    unittest.main()
