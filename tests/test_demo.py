"""The demo runner, and the two harness rules the demo found.

The demo is only worth publishing if it reports what happened rather than
what the agent said happened, so the checks it runs are tested here without
calling a model.
"""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_PROJECT = ROOT / "demo" / "orders"


def _load_demo():
    spec = importlib.util.spec_from_file_location(
        "python_vibe_demo", ROOT / "scripts" / "demo.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # A dataclass resolves its annotations through sys.modules, so the
    # module has to be registered before it is executed.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


DEMO = _load_demo()


class DemoProjectTest(unittest.TestCase):
    """The planted problems must still be planted, or the demo shows nothing."""

    def test_the_project_exists(self) -> None:
        self.assertTrue((DEMO_PROJECT / "src" / "orders.py").is_file())

    def test_the_name_error_is_still_there(self) -> None:
        body = (DEMO_PROJECT / "src" / "orders.py").read_text(encoding="utf-8")
        self.assertIn("subtotl", body)

    def test_the_opaque_name_is_still_there(self) -> None:
        body = (DEMO_PROJECT / "src" / "util.py").read_text(encoding="utf-8")
        self.assertIn("def calc(", body)

    def test_the_import_cycle_is_still_there(self) -> None:
        from harness.scan.layout import find_cycles

        self.assertEqual(find_cycles(DEMO_PROJECT), [("render", "report")])

    def test_the_suite_passes_before_the_agent_touches_it(self) -> None:
        from harness.act.tools import run_python

        out = run_python(DEMO_PROJECT, ("-m", "unittest", "discover", "-s", "tests", "-q"))
        self.assertTrue(out.startswith("exit 0"), out)


class VerifyTest(unittest.TestCase):
    """A case passes on evidence from the files, not on the agent's word."""

    def _case(self, **kwargs):
        base = dict(key="k", title="t", task="x", shows="s")
        base.update(kwargs)
        return DEMO.Case(**base)

    def test_a_check_that_holds_passes(self) -> None:
        case = self._case(check="assert 1 + 1 == 2")
        with tempfile.TemporaryDirectory() as tmp:
            verdict, _why = DEMO.verify(case, Path(tmp), [])
        self.assertEqual(verdict, "passed")

    def test_a_check_that_fails_reports_why(self) -> None:
        case = self._case(check="assert False, 'the function is missing'")
        with tempfile.TemporaryDirectory() as tmp:
            verdict, why = DEMO.verify(case, Path(tmp), [])
        self.assertEqual(verdict, "failed")
        self.assertIn("missing", why)

    def test_a_case_expecting_no_writes_fails_when_a_file_changed(self) -> None:
        case = self._case(expect_no_writes=True)
        with tempfile.TemporaryDirectory() as tmp:
            verdict, why = DEMO.verify(case, Path(tmp), ["src/orders.py"])
        self.assertEqual(verdict, "failed")
        self.assertIn("src/orders.py", why)

    def test_a_case_expecting_no_writes_passes_when_nothing_changed(self) -> None:
        case = self._case(expect_no_writes=True)
        with tempfile.TemporaryDirectory() as tmp:
            verdict, _why = DEMO.verify(case, Path(tmp), [])
        self.assertEqual(verdict, "passed")

    def test_a_case_with_nothing_to_check_says_so(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            verdict, _why = DEMO.verify(self._case(), Path(tmp), [])
        self.assertEqual(verdict, "not checked")


class ReviewDoesNotEditTest(unittest.TestCase):
    """Found by the demo: a review of one file had edited that file."""

    def test_a_review_of_a_named_file_may_not_write(self) -> None:
        from harness.locate import refuse_question_write

        blocked = refuse_question_write("review src/orders.py for bugs", "patch")
        self.assertIn("Reviews do not edit", blocked)

    def test_a_named_file_review_is_told_to_report_not_patch(self) -> None:
        from harness.locate import prelude

        text, path = prelude(DEMO_PROJECT, "review src/orders.py for bugs")
        self.assertEqual(path, "src/orders.py")
        self.assertIn("must be done", text)
        self.assertIn("Do not patch", text)
        self.assertIn("subtotl", text)
        self.assertNotIn("must be patch Path:", text)

    def test_a_named_file_review_quotes_the_undefined_name(self) -> None:
        from harness.locate import named_file_review_summary

        summary = named_file_review_summary(
            DEMO_PROJECT, "review src/orders.py for bugs"
        )
        self.assertIn("subtotl", summary)
        self.assertIn("src/orders.py", summary)

    def test_a_named_file_review_finishes_without_a_model(self) -> None:
        from harness import Agent, AgentOptions

        with tempfile.TemporaryDirectory() as tmp:
            project = DEMO._fresh_copy(Path(tmp))
            result = Agent(
                AgentOptions(
                    project=project,
                    task="review src/orders.py for bugs",
                    allow_writes=True,
                )
            ).run()
        self.assertTrue(result.ok)
        self.assertEqual(result.stopped, "done")
        self.assertIn("subtotl", result.summary)
        self.assertEqual(result.writes, ())

    def test_a_structure_review_may_still_write(self) -> None:
        from harness.locate import refuse_question_write

        self.assertEqual(refuse_question_write("review the project structure", "patch"), "")

    def test_a_refactor_may_still_write(self) -> None:
        from harness.locate import refuse_question_write

        self.assertEqual(refuse_question_write("refactor the god module", "patch"), "")


class TestsMayBeWrittenForANamedSourceFileTest(unittest.TestCase):
    """Found by the demo: the test went into the source file."""

    TASK = "write tests for apply_discount in src/orders.py"

    def _project(self, tmp: str) -> Path:
        root = Path(tmp)
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src" / "orders.py").write_text("x = 1\n", encoding="utf-8")
        (root / "tests" / "test_orders.py").write_text("x = 1\n", encoding="utf-8")
        return root

    def test_the_test_file_is_an_allowed_destination(self) -> None:
        from harness.agent.policy import refuse_wrong_file

        with tempfile.TemporaryDirectory() as tmp:
            got = refuse_wrong_file(self.TASK, self._project(tmp), "patch", "tests/test_orders.py")
        self.assertEqual(got, "")

    def test_an_unrelated_file_is_still_refused(self) -> None:
        from harness.agent.policy import refuse_wrong_file

        with tempfile.TemporaryDirectory() as tmp:
            got = refuse_wrong_file(self.TASK, self._project(tmp), "patch", "src/util.py")
        # The wording is free to improve; what matters is that the write is
        # refused and the file it would have touched is named.
        self.assertTrue(got)
        self.assertIn("src/util.py", got)


class AddFeatureGoesInTheDomainFileTest(unittest.TestCase):
    """Live 8B appended total_lines to the controller, then said done."""

    TASK = "add a function total_lines(prices) that counts the prices, and a unit test"

    def test_the_controller_is_not_an_allowed_destination(self) -> None:
        from harness.agent.policy import refuse_wrong_file

        blocked = refuse_wrong_file(
            self.TASK, DEMO_PROJECT, "patch", "src/orders_controller.py"
        )
        self.assertIn("src/orders.py", blocked)
        self.assertIn("orders_controller.py", blocked)

    def test_done_is_refused_until_the_function_exists(self) -> None:
        from harness.skillkit.style import refuse_done_oracle

        blocked = refuse_done_oracle(self.TASK, DEMO_PROJECT, "src/orders_controller.py")
        self.assertIn("total_lines", blocked)

    def test_prelude_names_the_domain_file(self) -> None:
        from harness.locate import prelude

        text, _path = prelude(DEMO_PROJECT, self.TASK)
        self.assertIn("Path: src/orders.py", text)
        self.assertIn("def total_lines", text)

    def test_a_written_function_gets_a_cover_test(self) -> None:
        from harness.agent.loop import _cover_after_add

        with tempfile.TemporaryDirectory() as tmp:
            project = DEMO._fresh_copy(Path(tmp))
            dest = project / "src" / "orders.py"
            dest.write_text(
                dest.read_text(encoding="utf-8")
                + "\n\ndef total_lines(prices: list[int]) -> int:\n"
                "    return len(prices)\n",
                encoding="utf-8",
            )
            note = _cover_after_add(project, self.TASK, "src/orders.py")
            self.assertIn("total_lines", note)
            self.assertIn("tests/test_orders.py", note)
            body = (project / "tests" / "test_orders.py").read_text(encoding="utf-8")
            self.assertIn("total_lines", body)


if __name__ == "__main__":
    unittest.main()
