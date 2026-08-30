"""Mechanical rename and NameError typo fixes. No model."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from harness import Agent, AgentOptions
from harness.act.autofix import (
    append_instead_of_replacing,
    apply_add_function,
    apply_cover_test,
    apply_function_rename,
    apply_mechanical,
    apply_person_bind,
    apply_typo_fixes,
    levenshtein,
    replacement_from_answer,
    typo_pairs,
    usual_first_arg,
)
from harness.agent.loop import leftover_bind_question
from harness.agent.prompt import build_preamble
from harness.scan.names import undefined_in_file

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


class TypoFixTest(unittest.TestCase):
    def test_subtotl_is_one_edit_from_subtotal(self) -> None:
        self.assertEqual(levenshtein("subtotl", "subtotal"), 1)
        self.assertEqual(typo_pairs(ORDERS), [("subtotl", "subtotal")])

    def test_the_typo_is_rewritten(self) -> None:
        fixed = apply_typo_fixes(ORDERS)
        self.assertNotIn("subtotl", fixed)
        self.assertIn("return subtotal + (subtotal * TAX_RATE)", fixed)
        self.assertIn("subtotal = compute_total", fixed)

    def test_two_equally_close_names_are_left_alone(self) -> None:
        source = (
            "def pick(prices: list[int]) -> int:\n"
            "    foo_bar = 1\n"
            "    foo_baz = 2\n"
            "    return foo_bat\n"
        )
        self.assertEqual(apply_typo_fixes(source), source)


class RenameFixTest(unittest.TestCase):
    def test_the_def_line_keeps_its_types(self) -> None:
        out = apply_function_rename(UTIL, "calc", "multiply")
        self.assertIn("def multiply(x: int, y: int) -> int:", out)
        self.assertNotIn("def calc", out)

    def test_calls_in_the_same_file_are_renamed(self) -> None:
        source = UTIL + "\n\ndef twice() -> int:\n    return calc(2, 2)\n"
        out = apply_function_rename(source, "calc", "multiply")
        self.assertIn("return multiply(2, 2)", out)


class MechanicalPreludeTest(unittest.TestCase):
    def test_bugfix_is_applied_before_the_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "orders.py").write_text(ORDERS, encoding="utf-8")
            (root / "tests" / "test_orders.py").write_text("x = 1\n", encoding="utf-8")
            note = apply_mechanical(
                root,
                "find a real NameError in src/orders.py and fix it",
                "src/orders.py",
            )
            body = (root / "src" / "orders.py").read_text(encoding="utf-8")
        self.assertIn("subtotl → subtotal", note)
        self.assertNotIn("subtotl", body)
        self.assertIn("subtotal = compute_total", body)

    def test_rename_is_applied_before_the_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "util.py").write_text(UTIL, encoding="utf-8")
            note = apply_mechanical(
                root,
                "rename calc to multiply in src/util.py",
                "src/util.py",
            )
            body = (root / "src" / "util.py").read_text(encoding="utf-8")
        self.assertIn("def calc → def multiply", note)
        self.assertIn("def multiply(x: int, y: int) -> int:", body)

    def test_preamble_records_the_autofix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "orders.py").write_text(ORDERS, encoding="utf-8")
            pre = build_preamble(
                AgentOptions(
                    project=root,
                    task="find a real NameError in src/orders.py and fix it",
                )
            )
        self.assertIn("mechanical fix", pre.autofix)
        self.assertIn("subtotl", pre.autofix)


class MechanicalFinishTest(unittest.TestCase):
    """A unique typo plus a green suite does not need the model."""

    def test_the_run_ends_before_the_engine_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "orders.py").write_text(ORDERS, encoding="utf-8")
            (root / "tests" / "test_orders.py").write_text(
                "import unittest\n\n\nclass OrdersTest(unittest.TestCase):\n"
                "    def test_placeholder(self) -> None:\n"
                "        self.assertEqual(1, 1)\n",
                encoding="utf-8",
            )
            options = AgentOptions(
                project=root,
                task="find a real NameError in src/orders.py and fix it",
            )
            with mock.patch(
                "harness.agent.loop.make_generate",
                side_effect=AssertionError("model must not load after a mechanical pass"),
            ):
                result = Agent(options).run()
            body = (root / "src" / "orders.py").read_text(encoding="utf-8")
        self.assertTrue(result.ok)
        self.assertEqual(result.stopped, "done")
        self.assertEqual(result.writes, ("src/orders.py",))
        self.assertIn("Tests passed", result.summary)
        self.assertNotIn("subtotl", body)

    def test_a_read_only_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "orders.py").write_text(ORDERS, encoding="utf-8")
            options = AgentOptions(
                project=root,
                task="find a real NameError in src/orders.py and fix it",
                allow_writes=False,
            )
            with mock.patch(
                "harness.agent.loop.make_generate",
                side_effect=AssertionError("model must not load for a dry run fix"),
            ):
                result = Agent(options).run()
            body = (root / "src" / "orders.py").read_text(encoding="utf-8")
        self.assertTrue(result.ok)
        self.assertEqual(result.writes, ())
        self.assertIn("subtotl", body)
        self.assertIn("Read-only", result.summary)


class CoverTestTest(unittest.TestCase):
    """A named function with no test gets one AAA method. No model."""

    IMPL = (
        "def apply_discount(total: int, percent: int) -> int:\n"
        "    return total - (total * percent) // 100\n"
    )
    TEST = (
        "import unittest\n\n"
        "from src.orders import compute_total\n\n\n"
        "class TestComputeTotal(unittest.TestCase):\n"
        "    def test_compute_total_sums_the_line_prices(self) -> None:\n"
        "        prices = [10, 20, 30]\n"
        "        got = compute_total(prices)\n"
        "        self.assertEqual(got, 60)\n"
    )

    def test_the_method_names_the_function(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "orders.py").write_text(self.IMPL, encoding="utf-8")
            dest = root / "tests" / "test_orders.py"
            dest.write_text(self.TEST, encoding="utf-8")
            note = apply_cover_test(
                root, "write tests for apply_discount in src/orders.py"
            )
            body = dest.read_text(encoding="utf-8")
        self.assertIn("tests/test_orders.py", note)
        self.assertIn("apply_discount", body)
        self.assertIn("got = apply_discount", body)
        self.assertIn("from src.orders import compute_total, apply_discount", body)

    def test_already_covered_is_a_note_not_a_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "orders.py").write_text(self.IMPL, encoding="utf-8")
            dest = root / "tests" / "test_orders.py"
            dest.write_text(
                self.TEST + "\n    def test_apply_discount_ok(self) -> None:\n"
                "        self.assertEqual(apply_discount(100, 10), 90)\n",
                encoding="utf-8",
            )
            before = dest.read_text(encoding="utf-8")
            note = apply_cover_test(root, "write tests for apply_discount")
            after = dest.read_text(encoding="utf-8")
        self.assertIn("already has a test for apply_discount", note)
        self.assertEqual(before, after)


class AddCountFunctionTest(unittest.TestCase):
    """`add a function total_lines` next to prices is len(prices), not open()."""

    def test_usual_first_arg_is_prices(self) -> None:
        name, hint = usual_first_arg(ORDERS)
        self.assertEqual(name, "prices")
        self.assertIn("list", hint)

    def test_total_lines_counts_prices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "orders.py").write_text(ORDERS, encoding="utf-8")
            (root / "tests" / "test_orders.py").write_text(
                "import unittest\n\nfrom src.orders import compute_total\n\n\n"
                "class T(unittest.TestCase):\n"
                "    def test_ok(self) -> None:\n"
                "        self.assertEqual(1, 1)\n",
                encoding="utf-8",
            )
            note = apply_add_function(root, "add a function total_lines and a test")
            body = (root / "src" / "orders.py").read_text(encoding="utf-8")
        self.assertIn("src/orders.py", note)
        self.assertIn("def total_lines(prices", body)
        self.assertIn("return len(prices)", body)
        self.assertNotIn("open(", body)

    def test_the_run_ends_before_the_engine_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "orders.py").write_text(ORDERS, encoding="utf-8")
            (root / "tests" / "test_orders.py").write_text(
                "import unittest\n\nfrom src.orders import compute_total\n\n\n"
                "class T(unittest.TestCase):\n"
                "    def test_ok(self) -> None:\n"
                "        self.assertEqual(1, 1)\n",
                encoding="utf-8",
            )
            options = AgentOptions(
                project=root,
                task="add a function total_lines and a test",
            )
            with mock.patch(
                "harness.agent.loop.make_generate",
                side_effect=AssertionError("model must not load after a mechanical add"),
            ):
                result = Agent(options).run()
            body = (root / "src" / "orders.py").read_text(encoding="utf-8")
        self.assertTrue(result.ok)
        self.assertEqual(result.stopped, "done")
        self.assertIn("total_lines", body)
        self.assertIn("Tests passed", result.summary)

    def test_open_is_refused_on_an_add(self) -> None:
        from harness.skillkit.style import refuse_add_opens_file

        blocked = refuse_add_opens_file(
            "add a function total_lines and a test",
            "src/orders.py",
            "def total_lines(file_path: str) -> int:\n    return len(open(file_path).read())\n",
        )
        self.assertIn("not what total_lines was asked for", blocked)
        self.assertEqual(
            refuse_add_opens_file(
                "what does compute_total return?",
                "src/orders.py",
                "open('x')",
            ),
            "",
        )

    def test_a_function_whose_job_is_a_file_may_open_one(self) -> None:
        """The rule cost more than it saved when it judged every add.

        `read_env_file(path)` has to open a file. Refusing it left a
        function returning an int where the caller wanted a dict, and the
        run spent its whole step budget being told to write something
        else. A task that talks about files, or that names its own
        arguments, is not the case this rule was written for.
        """
        from harness.skillkit.style import refuse_add_opens_file

        for task in (
            "add a function read_env_file(path) that reads KEY=VALUE lines "
            "into a dict, skipping blank lines and comments",
            "add a function load_config that reads the config file",
            "add a function venv_python(venv, windows) that returns the "
            "interpreter path inside a virtual environment",
        ):
            with self.subTest(task=task[:40]):
                self.assertEqual(
                    refuse_add_opens_file(
                        task,
                        "src/orders.py",
                        "def f(p):\n    return open(p).read()\n",
                    ),
                    "",
                )


class UnnamedNameErrorTest(unittest.TestCase):
    """`find the NameError and fix it` names no file. Scan the tree."""

    def test_the_unique_typo_is_fixed_without_a_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "orders.py").write_text(ORDERS, encoding="utf-8")
            (root / "src" / "ctrl.py").write_text(
                "class C:\n    def status(self) -> str:\n        return stauts\n",
                encoding="utf-8",
            )
            (root / "tests" / "test_orders.py").write_text(
                "import unittest\n\nclass T(unittest.TestCase):\n"
                "    def test_ok(self) -> None:\n        self.assertEqual(1, 1)\n",
                encoding="utf-8",
            )
            note = apply_mechanical(root, "find the NameError and fix it", "")
            orders = (root / "src" / "orders.py").read_text(encoding="utf-8")
            ctrl = (root / "src" / "ctrl.py").read_text(encoding="utf-8")
        self.assertIn("subtotl → subtotal", note)
        self.assertNotIn("subtotl", orders)
        self.assertIn("stauts", ctrl)


class OnlyCodeIsRewrittenTest(unittest.TestCase):
    """A mechanical fix must not edit words the person wrote.

    The typo fix runs during a bug fix, where an error message may well
    mention the misspelling on purpose. Rewriting it would change the
    program's output without being asked.
    """

    SOURCE = (
        "def total(prices: list[int]) -> int:\n"
        "    subtotal = sum(prices)\n"
        "    if not prices:\n"
        '        raise ValueError("subtotl must be set")  # note: subtotl\n'
        "    return subtotl\n"
    )

    def test_the_code_is_fixed(self) -> None:
        got = apply_typo_fixes(self.SOURCE)
        self.assertIn("return subtotal", got)

    def test_a_string_keeps_the_word(self) -> None:
        got = apply_typo_fixes(self.SOURCE)
        self.assertIn('"subtotl must be set"', got)

    def test_a_comment_keeps_the_word(self) -> None:
        got = apply_typo_fixes(self.SOURCE)
        self.assertIn("# note: subtotl", got)

    def test_the_result_is_still_valid_python(self) -> None:
        import ast

        ast.parse(apply_typo_fixes(self.SOURCE))

    def test_unparsable_source_is_returned_unchanged(self) -> None:
        broken = "def f(\n"
        self.assertEqual(apply_typo_fixes(broken), broken)


class RenameScopeTest(unittest.TestCase):
    """The rename needs a call shape, so prose is left alone."""

    SOURCE = (
        "def calc(x: int, y: int) -> int:\n"
        '    """Return calc of x and y."""\n'
        "    return x * y\n"
    )

    def test_the_definition_is_renamed(self) -> None:
        got = apply_function_rename(self.SOURCE, "calc", "multiply")
        self.assertIn("def multiply(x: int, y: int) -> int:", got)

    def test_prose_mentioning_the_name_is_left_alone(self) -> None:
        got = apply_function_rename(self.SOURCE, "calc", "multiply")
        self.assertIn("Return calc of x and y.", got)

    def test_nothing_happens_when_the_new_name_already_exists(self) -> None:
        source = self.SOURCE + "\n\ndef multiply(a, b):\n    return a * b\n"
        self.assertEqual(apply_function_rename(source, "calc", "multiply"), source)

    def test_nothing_happens_when_the_old_name_is_absent(self) -> None:
        self.assertEqual(apply_function_rename(self.SOURCE, "nope", "x"), self.SOURCE)


class MechanicalFastPathTest(unittest.TestCase):
    """A fix the harness can make itself should not need the model at all.

    It must also stay inside the promises the rest of the harness makes: a
    read-only run changes nothing, and a project without tests has not
    failed anything.
    """

    TASK = "find a real NameError in src/orders.py and fix it"
    BROKEN = (
        "def total_with_tax(prices: list[int]) -> float:\n"
        "    subtotal = sum(prices)\n"
        "    return subtotl * 1.2\n"
    )

    def _project(self, tmp: str, *, with_tests: bool) -> Path:
        root = Path(tmp)
        (root / "src").mkdir()
        (root / "src" / "orders.py").write_text(self.BROKEN, encoding="utf-8")
        if with_tests:
            (root / "tests").mkdir()
            (root / "tests" / "test_smoke.py").write_text(
                "import unittest\n\n\nclass TestSmoke(unittest.TestCase):\n"
                "    def test_smoke_passes(self) -> None:\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )
        return root

    def _run(self, project: Path, **options):
        from unittest import mock

        from harness import Agent, AgentOptions

        calls: list[int] = []

        def generate(_prompt: str) -> str:
            calls.append(1)
            return "Action: done\nSummary: stub"

        with mock.patch(
            "harness.agent.loop.make_generate", lambda *a, **k: ("stub", generate)
        ):
            result = Agent(
                AgentOptions(project=project, task=self.TASK, steps=2, **options)
            ).run()
        return result, len(calls)

    def test_a_green_suite_finishes_without_the_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project(tmp, with_tests=True)
            result, calls = self._run(project)
            fixed = (project / "src" / "orders.py").read_text(encoding="utf-8")
        self.assertTrue(result.ok)
        self.assertEqual(calls, 0)
        self.assertIn("return subtotal", fixed)

    def test_a_project_without_tests_is_not_treated_as_a_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result, calls = self._run(self._project(tmp, with_tests=False))
        self.assertTrue(result.ok)
        self.assertEqual(calls, 0)
        self.assertIn("no tests", result.summary)

    def test_the_summary_does_not_claim_the_fix_is_covered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result, _calls = self._run(self._project(tmp, with_tests=False))
        self.assertNotIn("Tests passed", result.summary)

    def test_a_read_only_run_changes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project(tmp, with_tests=True)
            before = (project / "src" / "orders.py").read_text(encoding="utf-8")
            result, _calls = self._run(project, allow_writes=False)
            after = (project / "src" / "orders.py").read_text(encoding="utf-8")
        self.assertEqual(before, after)
        self.assertEqual(result.writes, ())


class MissingImportTest(unittest.TestCase):
    """A well-known name used without its import is a mechanical repair.

    A model writes `Path` and forgets `from pathlib import Path`. Refusing
    that and asking for a rename is wrong twice over: the name is right,
    and the fix does not need a model. Watched a run spend its first turn
    being told "Find: Path Replace: the name you assigned".
    """

    SOURCE = (
        "def venv_python(venv: Path, windows: bool) -> Path:\n"
        "    if windows:\n"
        "        return venv / 'Scripts'\n"
        "    return venv / 'bin'\n"
    )

    def test_the_import_is_added(self) -> None:
        from harness.act.autofix import apply_missing_imports

        self.assertIn("from pathlib import Path", apply_missing_imports(self.SOURCE))

    def test_nothing_is_left_unbound(self) -> None:
        from harness.act.autofix import apply_missing_imports
        from harness.scan.names import undefined_names

        self.assertEqual(undefined_names(apply_missing_imports(self.SOURCE)), [])

    def test_the_result_still_parses(self) -> None:
        import ast

        from harness.act.autofix import apply_missing_imports

        ast.parse(apply_missing_imports(self.SOURCE))

    def test_an_import_already_there_is_not_repeated(self) -> None:
        from harness.act.autofix import apply_missing_imports

        source = "from pathlib import Path\n\n\ndef f(p: Path) -> Path:\n    return p\n"
        self.assertEqual(apply_missing_imports(source), source)

    def test_it_goes_below_a_module_docstring(self) -> None:
        from harness.act.autofix import apply_missing_imports

        out = apply_missing_imports('"""Paths."""\n\n\ndef f(p: Path) -> Path:\n    return p\n')
        self.assertTrue(out.startswith('"""Paths."""'))
        self.assertIn("from pathlib import Path", out)

    def test_a_name_that_is_not_on_the_list_is_left_alone(self) -> None:
        from harness.act.autofix import apply_missing_imports

        source = "def f():\n    return mystery_helper()\n"
        self.assertEqual(apply_missing_imports(source), source)

    def test_the_write_succeeds_instead_of_being_refused(self) -> None:
        from harness.act.tools import edit_py

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "pkg").mkdir()
            out = edit_py(project, "pkg/paths.py", self.SOURCE, task="add venv_python")
            body = (project / "pkg" / "paths.py").read_text(encoding="utf-8")
        self.assertTrue(out.startswith("wrote"), out)
        self.assertIn("from pathlib import Path", body)


class MethodNameIsNotInScopeTest(unittest.TestCase):
    """A method name cannot repair a typo inside that method's body.

    `def status(self): return stauts` looks like an easy bind: `status`
    is one letter away, and it was the only candidate, so the binder
    took it and wrote `return status` — which still raises NameError.
    The run then reported "Tests passed", because no test covered the
    method. A wrong deterministic repair is worse than none: it is
    silent, instant, and reported as success.
    """

    SOURCE = (
        "class OrdersController:\n"
        "    def status(self) -> str:\n"
        "        return stauts\n"
    )

    def test_no_pair_is_offered(self) -> None:
        self.assertEqual(typo_pairs(self.SOURCE), [])

    def test_the_file_is_left_alone(self) -> None:
        self.assertEqual(apply_typo_fixes(self.SOURCE), self.SOURCE)

    def test_a_class_attribute_is_not_in_scope_either(self) -> None:
        source = (
            "class Config:\n"
            "    timeout = 30\n"
            "\n"
            "    def wait(self) -> int:\n"
            "        return timeoutt\n"
        )
        self.assertEqual(typo_pairs(source), [])

    def test_a_module_level_name_still_repairs(self) -> None:
        """The fix must not switch the working case off."""
        source = (
            "def compute_total(prices):\n"
            "    return sum(prices)\n"
            "\n"
            "def total_with_tax(prices):\n"
            "    subtotal = compute_total(prices)\n"
            "    return subtotl\n"
        )
        self.assertEqual(typo_pairs(source), [("subtotl", "subtotal")])

    def test_a_parameter_still_repairs_inside_a_method(self) -> None:
        source = (
            "class Cart:\n"
            "    def total(self, prices):\n"
            "        return sum(pricess)\n"
        )
        self.assertEqual(typo_pairs(source), [("pricess", "prices")])

    def test_the_run_asks_instead_of_loading_the_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            dest = root / "src" / "orders_controller.py"
            dest.write_text(self.SOURCE, encoding="utf-8")
            options = AgentOptions(
                project=root,
                task="find the NameError in src/orders_controller.py and fix it",
            )
            with mock.patch(
                "harness.agent.loop.make_generate",
                side_effect=AssertionError(
                    "model must not load when the bind is not unique"
                ),
            ):
                result = Agent(options).run()
            body = dest.read_text(encoding="utf-8")
        self.assertEqual(result.stopped, "question")
        self.assertFalse(result.ok)
        self.assertIn("stauts", result.summary)
        self.assertIn("looks like `status`", result.summary)
        self.assertIn("none of those is in scope", result.summary)
        self.assertEqual(body, self.SOURCE)
        self.assertNotIn("return status", body)

    def test_the_persons_literal_is_bound_without_a_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            dest = root / "src" / "orders_controller.py"
            dest.write_text(self.SOURCE, encoding="utf-8")
            options = AgentOptions(
                project=root,
                task="find the NameError in src/orders_controller.py and fix it",
                on_question=lambda q: "ok",
            )
            with mock.patch(
                "harness.agent.loop.make_generate",
                side_effect=AssertionError(
                    "model must not load after the person answered"
                ),
            ):
                result = Agent(options).run()
            body = dest.read_text(encoding="utf-8")
        self.assertEqual(result.stopped, "done")
        self.assertTrue(result.ok)
        self.assertRegex(body, r"""return ['"]ok['"]""")
        self.assertNotIn("stauts", body)
        self.assertNotIn("return status", body)

    def test_the_method_name_is_still_refused_as_an_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            dest = root / "src" / "orders_controller.py"
            dest.write_text(self.SOURCE, encoding="utf-8")
            options = AgentOptions(
                project=root,
                task="find the NameError in src/orders_controller.py and fix it",
                on_question=lambda q: "status",
            )
            with mock.patch(
                "harness.agent.loop.make_generate",
                side_effect=AssertionError(
                    "model must not load when the answer is the method name"
                ),
            ):
                result = Agent(options).run()
            body = dest.read_text(encoding="utf-8")
        self.assertEqual(result.stopped, "question")
        self.assertFalse(result.ok)
        self.assertIn("still not something this method can return", result.summary)
        self.assertEqual(body, self.SOURCE)

    def test_a_quoted_return_is_the_same_as_the_bare_word(self) -> None:
        self.assertEqual(
            replacement_from_answer('return "ok"', set(), {"status"}),
            replacement_from_answer("ok", set(), {"status"}),
        )
        self.assertIsNone(replacement_from_answer("status", set(), {"status"}))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            dest = root / "src" / "orders_controller.py"
            dest.write_text(self.SOURCE, encoding="utf-8")
            note = apply_person_bind(
                root,
                "find the NameError in src/orders_controller.py and fix it",
                "ok",
                write=False,
            )
            self.assertIn("`stauts`", note)
            self.assertEqual(dest.read_text(encoding="utf-8"), self.SOURCE)

    def test_a_read_only_run_says_what_it_would_do_and_writes_nothing(self) -> None:
        """`ask` and `--dry-run` promise the folder is left alone.

        Asking is not writing, so a read-only run may still put the
        question. Acting on the answer is writing. Applying it regardless
        of `allow_writes` changed the file and left a `.bak` behind under
        both `--dry-run` and `ask`, which the CLI runs with writes off.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            target = root / "src" / "ctl.py"
            target.write_text(self.SOURCE, encoding="utf-8")
            before = target.read_text(encoding="utf-8")
            result = Agent(
                AgentOptions(
                    project=root,
                    task="find the NameError in src/ctl.py and fix it",
                    model="no-such-model:0",
                    steps=2,
                    allow_writes=False,
                    on_question=lambda question: "ok",
                )
            ).run()
            self.assertEqual(target.read_text(encoding="utf-8"), before)
            self.assertEqual(list((root / "src").glob("*.bak")), [])
        self.assertTrue(result.ok)
        self.assertIn("Read-only", result.summary)
        self.assertIn("Nothing written", result.summary)
        self.assertEqual(result.writes, ())

    def test_a_red_suite_is_never_a_finished_run(self) -> None:
        """The answer went in, but the project is not green.

        Reporting `ok` here meant exit code 0 with a failing suite, the
        only place in the project that did. The mechanical pass hands the
        real failure to the model instead, and so does this.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "__init__.py").write_text("", encoding="utf-8")
            (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
            (root / "src" / "ctl.py").write_text(self.SOURCE, encoding="utf-8")
            (root / "tests" / "test_ctl.py").write_text(
                "import unittest\n\n"
                "from src.ctl import Controller\n\n\n"
                "class TestController(unittest.TestCase):\n"
                "    def test_status_says_ready(self) -> None:\n"
                "        self.assertEqual(Controller().status(), 'ready')\n",
                encoding="utf-8",
            )
            with mock.patch(
                "harness.agent.loop.make_generate",
                _scripted_done("nothing more to do"),
            ):
                result = Agent(
                    AgentOptions(
                        project=root,
                        task="find the NameError in src/ctl.py and fix it",
                        steps=2,
                        on_question=lambda question: "ok",
                    )
                ).run()
            body = (root / "src" / "ctl.py").read_text(encoding="utf-8")
        # The answer is applied either way; what must not happen is a
        # green verdict over a red suite.
        self.assertIn("'ok'", body)
        self.assertFalse(result.ok, result.summary)

    def test_a_name_that_is_not_a_typo_goes_to_the_model(self) -> None:
        """Asking is for a misspelling nobody can safely bind.

        Any other undefined name is work the model can do: a missing
        import, or something the task is asking to be written. The first
        version asked about all of them, so a file using a name defined
        under `if TYPE_CHECKING:` stopped the run with a question about
        a type annotation instead of fixing the bug it was given.
        """
        source = (
            "def total(prices: list[int]) -> int:\n"
            "    return sum(prices) + offset\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "money.py").write_text(source, encoding="utf-8")
            self.assertEqual(
                leftover_bind_question(
                    "fix the off by one in src/money.py", root
                ),
                None,
            )

    def test_a_type_checking_import_does_not_stop_the_run(self) -> None:
        source = (
            "from __future__ import annotations\n\n"
            "from typing import TYPE_CHECKING\n\n"
            "if TYPE_CHECKING:\n"
            "    from rich.markdown import Markdown\n\n\n"
            "def build(text: str) -> Markdown:\n"
            "    return text\n\n\n"
            "def total(prices: list[int]) -> int:\n"
            "    return sum(prices) + 1\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "renderer.py").write_text(source, encoding="utf-8")
            self.assertEqual(undefined_in_file(root / "src" / "renderer.py"), [])
            self.assertEqual(
                leftover_bind_question(
                    "fix the off by one in src/renderer.py", root
                ),
                None,
            )

    def test_a_unique_bind_is_repaired_rather_than_asked_about(self) -> None:
        source = (
            "def compute_total(prices):\n"
            "    return sum(prices)\n\n\n"
            "def total_with_tax(prices):\n"
            "    subtotal = compute_total(prices)\n"
            "    return subtotl\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "orders.py").write_text(source, encoding="utf-8")
            self.assertEqual(
                leftover_bind_question(
                    "fix the NameError in src/orders.py", root
                ),
                None,
            )

class ShortDraftIsAnAdditionTest(unittest.TestCase):
    """A correct new function must not be thrown away for being short.

    `edit` replaces a whole file, so a new function sent on its own is
    shorter than what it would replace and was refused for that. A live
    8B wrote a working `slugify`, had it rejected twice — once for a
    missing fence, then for being 89 characters against 276 — and spent
    the rest of its budget sending the same correct code back.
    """

    ORIGINAL = (
        '"""Order arithmetic."""\n\n\n'
        "def compute_total(prices: list[int]) -> int:\n"
        "    return sum(prices)\n\n\n"
        "def apply_discount(total: int, percent: int) -> int:\n"
        "    return total - (total * percent) // 100\n"
    )
    DRAFT = (
        "def slugify(text: str) -> str:\n"
        "    return '-'.join(word.lower() for word in text.split())\n"
    )

    def test_the_new_function_is_appended_and_the_file_kept(self) -> None:
        merged = append_instead_of_replacing(self.ORIGINAL, self.DRAFT)
        self.assertIn("def compute_total", merged)
        self.assertIn("def apply_discount", merged)
        self.assertIn("def slugify", merged)
        namespace: dict = {}
        exec(compile(merged, "m", "exec"), namespace)
        self.assertEqual(namespace["slugify"]("Hello There"), "hello-there")

    def test_a_real_rewrite_is_left_alone(self) -> None:
        """Only an addition. A shorter rewrite is still the caller's problem."""
        rewrite = self.ORIGINAL.replace("sum(prices)", "sum(p for p in prices)")
        self.assertEqual(append_instead_of_replacing(self.ORIGINAL, rewrite), "")

    def test_redefining_an_existing_name_is_not_an_addition(self) -> None:
        same = "def compute_total(prices):\n    return 0\n"
        self.assertEqual(append_instead_of_replacing(self.ORIGINAL, same), "")

    def test_a_bare_statement_is_not_an_addition(self) -> None:
        self.assertEqual(
            append_instead_of_replacing(self.ORIGINAL, "print('hi')\n"), ""
        )

    def test_an_empty_file_is_left_to_the_normal_path(self) -> None:
        self.assertEqual(append_instead_of_replacing("", self.DRAFT), "")



if __name__ == "__main__":
    unittest.main()
