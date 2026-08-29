"""Mechanical rename and NameError typo fixes. No model."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from harness import Agent, AgentOptions
from harness.act.autofix import (
    apply_cover_test,
    apply_function_rename,
    apply_mechanical,
    apply_typo_fixes,
    levenshtein,
    typo_pairs,
)
from harness.agent.prompt import build_preamble

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


if __name__ == "__main__":
    unittest.main()
