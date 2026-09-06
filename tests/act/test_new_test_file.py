"""A test method with no class, appended to a file that does not exist.

Asked to write tests for a function, an 8B answers with the method and
not the class it belongs to — indented, because it knows the method goes
inside something, and it never writes the something:

    Action: patch
    Path: tests/test_apply_discount.py
    Append:
        def test_apply_discount_returns(self) -> None:
            ...

Appended to a file that is not there yet, that is `unexpected indent`
and no file written. The reply then advised using `Find:`, a field the
draft did not contain, so the model resent the identical draft. Four
runs of four spent every step that way and wrote nothing at all.

Supplying the class invents no behaviour. The assertions are the
model's; this is only the scaffolding `unittest` needs to collect them.
"""

import ast
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.act.gate import repair_unittest_append  # noqa: E402

METHOD = (
    "    def test_apply_discount_drops_the_percent(self) -> None:\n"
    "        got = apply_discount(100, 20)\n"
    "        self.assertEqual(got, 80.0)\n"
)


class WritingTheWholeModuleTest(unittest.TestCase):
    def test_a_bare_method_becomes_a_test_case(self) -> None:
        out = repair_unittest_append("", METHOD, "tests/test_pricing.py")
        self.assertIsNotNone(out)
        ast.parse(out)
        self.assertIn("import unittest", out)
        self.assertIn("class TestPricing(unittest.TestCase):", out)
        self.assertIn("def test_apply_discount_drops_the_percent", out)

    def test_the_class_is_named_after_the_file(self) -> None:
        """`tests/test_pricing.py` gives `TestPricing`, as this project's
        own test files are named."""
        out = repair_unittest_append("", METHOD, "tests/test_order_totals.py")
        self.assertIn("class TestOrderTotals(unittest.TestCase):", out)

    def test_an_unknown_file_still_gets_a_name(self) -> None:
        out = repair_unittest_append("", METHOD, "")
        self.assertIn("class Tests(unittest.TestCase):", out)

    def test_the_assertions_are_carried_over_unchanged(self) -> None:
        out = repair_unittest_append("", METHOD, "tests/test_pricing.py")
        self.assertIn("self.assertEqual(got, 80.0)", out)
        self.assertIn("apply_discount(100, 20)", out)


class WhatItMustNotDoTest(unittest.TestCase):
    def test_it_leaves_a_file_that_already_exists_alone(self) -> None:
        """That is the older repair's job, and it has its own tests."""
        self.assertIsNone(
            repair_unittest_append("x = 1\n", METHOD, "tests/test_pricing.py")
        )

    def test_a_draft_that_already_has_a_class_is_not_wrapped_twice(self) -> None:
        whole = (
            "import unittest\n\n\nclass TestPricing(unittest.TestCase):\n"
            "    def test_x(self) -> None:\n        self.assertTrue(True)\n"
        )
        self.assertIsNone(repair_unittest_append("", whole, "tests/test_pricing.py"))

    def test_a_body_that_does_not_parse_is_refused(self) -> None:
        self.assertIsNone(
            repair_unittest_append("", "    def test_x(self:\n", "tests/t.py")
        )

    def test_something_that_is_not_a_test_is_left_alone(self) -> None:
        self.assertIsNone(
            repair_unittest_append("", "    def helper(self):\n        pass\n", "t.py")
        )


class AndUnittestReallyCollectsItTest(unittest.TestCase):
    """The only check that matters: does the suite run the test."""

    def test_the_repaired_file_runs_one_test(self) -> None:
        out = repair_unittest_append("", METHOD, "tests/test_pricing.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tests").mkdir()
            (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
            body = out.replace(
                "        got = apply_discount(100, 20)",
                "        got = 80.0",
            )
            (root / "tests" / "test_pricing.py").write_text(body, encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
                cwd=root, capture_output=True, text=True, timeout=60, check=False,
            )
            output = proc.stdout + proc.stderr
            self.assertIn("Ran 1 test", output, output)


if __name__ == "__main__":
    unittest.main()
