import io
import sys
import tempfile
import unittest
from pathlib import Path

from harness.cli import _program_name, how_to, main, resolve_project_task


class HowToTest(unittest.TestCase):
    def test_no_args_prints_the_four_jobs(self) -> None:
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            code = main([])
        finally:
            sys.stdout = old
        self.assertEqual(code, 0)
        text = buf.getvalue()
        self.assertIn("brief", text)
        self.assertIn("ask", text)
        self.assertIn("write tests", text)
        self.assertIn("NameError", text)
        self.assertIn("harness demos", text)
        self.assertIn("no model", text)
        self.assertIn("demo/orders", text)
        self.assertIn("brief /path/to/project", text)
        self.assertIn("clone first", text)
        self.assertEqual(text, how_to())


    def test_it_names_the_command_this_machine_can_run(self) -> None:
        """The regression: the list must not send you to a missing command.

        `py-harness` is only on PATH after `pip install -e .`. Someone
        running the module form has no such command, so printing it is
        an instruction that fails on the first line. `python-vibe` stays
        as a console-script alias and must print that name when invoked.
        """
        old = sys.argv
        try:
            sys.argv = ["/usr/bin/python3.13", "-m", "harness"]
            self.assertIn("python -m harness brief", how_to())
            self.assertNotIn("python-vibe brief", how_to())
            self.assertNotIn("py-harness brief", how_to())
            sys.argv = ["/somewhere/bin/python-vibe"]
            self.assertIn("python-vibe brief", how_to())
            sys.argv = ["/somewhere/bin/py-harness"]
            self.assertIn("py-harness brief", how_to())
        finally:
            sys.argv = old


class ProjectTaskTest(unittest.TestCase):
    def test_one_argument_is_the_task_in_this_folder(self) -> None:
        project, task = resolve_project_task("what does add return?", None)
        self.assertEqual(project, Path(".").resolve())
        self.assertEqual(task, "what does add return?")

    def test_folder_then_task(self) -> None:
        here = Path(".").resolve()
        project, task = resolve_project_task(str(here), "write tests for add")
        self.assertEqual(project, here)
        self.assertEqual(task, "write tests for add")

    def test_folder_alone_is_not_a_task(self) -> None:
        here = Path(".").resolve()
        project, task = resolve_project_task(str(here), None)
        self.assertEqual(project, here)
        self.assertEqual(task, "")

    def test_brief_refuses_a_missing_folder(self) -> None:
        err = io.StringIO()
        old = sys.stderr
        sys.stderr = err
        try:
            code = main(["brief", "/tmp/py-harness-no-such-folder"])
        finally:
            sys.stderr = old
        self.assertEqual(code, 2)
        self.assertIn("not a directory", err.getvalue())
        self.assertNotIn("0 Python", err.getvalue())

    def test_brief_an_empty_folder_is_still_a_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            buf = io.StringIO()
            old = sys.stdout
            sys.stdout = buf
            try:
                code = main(["brief", tmp])
            finally:
                sys.stdout = old
            self.assertEqual(code, 0)
            self.assertIn("0 Python", buf.getvalue())

    def test_ask_without_a_question_fails(self) -> None:
        err = io.StringIO()
        old = sys.stderr
        sys.stderr = err
        try:
            code = main(["ask", str(Path(".").resolve())])
        finally:
            sys.stderr = old
        self.assertEqual(code, 2)
        self.assertIn("needs a question", err.getvalue())


class CommandTableTest(unittest.TestCase):
    """Every subcommand the parser offers must have somewhere to go.

    The dispatch was nine `if args.command ==` tests. Adding a
    subcommand meant remembering to add a branch in the middle of them,
    and forgetting produced a silent fall-through rather than an error.
    """

    def _parser_commands(self) -> set[str]:
        from harness.cli import build_parser

        for action in build_parser()._subparsers._group_actions:
            if getattr(action, "choices", None):
                return set(action.choices)
        return set()

    def test_the_table_and_the_parser_agree(self) -> None:
        from harness.cli import COMMANDS

        self.assertEqual(self._parser_commands(), set(COMMANDS))

    def test_every_entry_can_be_called(self) -> None:
        from harness.cli import COMMANDS

        for name, handler in COMMANDS.items():
            with self.subTest(command=name):
                self.assertTrue(callable(handler))

    def test_last_with_no_traces_is_not_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            buf = io.StringIO()
            old = sys.stdout
            sys.stdout = buf
            try:
                code = main(["last", tmp])
            finally:
                sys.stdout = old
        self.assertEqual(code, 0)
        self.assertIn("no traces", buf.getvalue())

    def test_the_missing_task_hint_names_a_command_that_exists(self) -> None:
        """The hint used to say `py-harness`, installed or not."""
        from harness.cli import _missing_task_message, _program_name

        old = sys.argv
        try:
            sys.argv = ["/usr/bin/python3.13", "-m", "harness"]
            self.assertIn(_program_name(), _missing_task_message("ask"))
            self.assertNotIn("python-vibe ask", _missing_task_message("ask"))
            self.assertNotIn("py-harness ask", _missing_task_message("ask"))
        finally:
            sys.argv = old


if __name__ == "__main__":
    unittest.main()
