"""The design scan measures how long a function is.

The architecture test in this repository refuses a function over 80
lines, so the rule existed — but only as a merge gate. The scan the
model reads while working never mentioned length, so nothing told it
until CI refused the change.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.scan.design import (  # noqa: E402
    LONG_DEF,
    longest_def,
    render_design_review,
)


def _sprawling(lines: int) -> str:
    body = "\n".join(f"    x{n} = {n}" for n in range(lines))
    return f"def sprawl(rows):\n{body}\n    return rows\n"


def _project(tmp: str, source: str) -> Path:
    root = Path(tmp)
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "src" / "big.py").write_text(source, encoding="utf-8")
    (root / "tests" / "test_big.py").write_text("x = 1\n", encoding="utf-8")
    return root


class MeasuringOneFileTest(unittest.TestCase):
    def test_the_longest_function_is_found(self) -> None:
        source = "def short():\n    return 1\n\n\n" + _sprawling(50)
        found = longest_def(source)
        self.assertIsNotNone(found)
        self.assertEqual(found[0], "sprawl")
        self.assertGreater(found[1], LONG_DEF)

    def test_a_file_with_no_functions(self) -> None:
        self.assertIsNone(longest_def("x = 1\n"))

    def test_a_file_that_does_not_parse(self) -> None:
        """Half a file is not a reason to stop reviewing the rest."""
        self.assertIsNone(longest_def("def broken(:\n"))

    def test_a_long_class_is_not_a_long_function(self) -> None:
        """The message says function, so it has to be one.

        A long class may well be worth a finding, but it is a different
        finding with a different remedy, and calling it a function tells
        the model to do the wrong thing with it.
        """
        body = "\n".join(f"    field{n} = {n}" for n in range(60))
        source = f"class Wide:\n{body}\n\n\ndef tidy(rows):\n    return rows\n"
        found = longest_def(source)
        self.assertIsNotNone(found)
        self.assertEqual(found[0], "tidy")

    def test_a_nested_function_is_not_a_top_level_one(self) -> None:
        source = "def outer():\n    def inner():\n        return 1\n    return inner\n"
        self.assertEqual(longest_def(source)[0], "outer")


class WhatTheReviewSaysTest(unittest.TestCase):
    def test_a_long_function_is_reported_with_its_length(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = render_design_review(_project(tmp, _sprawling(60)))
            self.assertIn("long function", report)
            self.assertIn("src/big.py:sprawl", report)
            self.assertIn(f"over {LONG_DEF}", report)

    def test_a_short_function_is_left_alone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = render_design_review(
                _project(tmp, "def tidy(rows):\n    return sorted(rows)\n")
            )
            self.assertNotIn("long function", report)

    def test_one_finding_per_file_not_one_per_function(self) -> None:
        """Six long functions in a file are one problem, not six findings."""
        with tempfile.TemporaryDirectory() as tmp:
            many = "\n\n".join(
                _sprawling(50).replace("sprawl", f"sprawl{n}") for n in range(6)
            )
            report = render_design_review(_project(tmp, many))
            self.assertEqual(report.count("long function"), 1)

    def test_a_test_file_is_not_measured(self) -> None:
        """A test that sets up a lot of state is not a design problem."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "big.py").write_text(
                "def tidy(rows):\n    return sorted(rows)\n", encoding="utf-8"
            )
            (root / "tests" / "test_big.py").write_text(
                _sprawling(60), encoding="utf-8"
            )
            self.assertNotIn("long function", render_design_review(root))


class TheTwoNumbersTest(unittest.TestCase):
    def test_the_scan_warns_before_the_merge_gate_refuses(self) -> None:
        """40 is where a function stops being one thing; 80 is where it
        cannot be read. The scan must be the earlier of the two, or it
        only ever agrees with a refusal that already happened."""
        architecture = (
            Path(__file__).resolve().parents[1] / "whole" / "test_architecture.py"
        ).read_text(encoding="utf-8")
        self.assertIn("LIMIT = 80", architecture)
        self.assertLess(LONG_DEF, 80)



class OneNameOneMeaningTest(unittest.TestCase):
    """"god module" meant two different things in two different files.

    `scan.design` called a file with four or more top-level functions a
    god module. `scan.layout` called a file over 6 KB and three times
    the median one. They disagreed in both directions — a 300-byte file
    with four functions is one by the first rule and not the second; a
    7 KB file holding two long functions is one by the second and not
    the first — and both told the model "god module" with different
    remedies.

    The size rule is called `outsized` now, which is what it measures.
    Since the design review started reporting long functions, the case
    it used to catch has a better answer anyway.
    """

    def _source(self, name: str) -> str:
        root = Path(__file__).resolve().parents[2] / "src" / "harness" / "scan"
        return (root / name).read_text(encoding="utf-8")

    def test_only_the_design_review_reports_a_god_module(self) -> None:
        """What a finding says, not what a comment explains.

        The first version of this test read the whole file, so the
        comment in `layout.py` explaining why the two rules are
        different failed it — and the real bug it did catch was a clean
        report still promising "no god module" for a check that had
        stopped existing.
        """
        import tempfile

        from harness.scan.layout import render_layout

        self.assertIn("god module", self._source("design.py"))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for n in range(6):
                (root / f"m{n}.py").write_text("x = 1\n", encoding="utf-8")
            (root / "huge.py").write_text("# pad\n" * 3000, encoding="utf-8")
            report = render_layout(root)
        self.assertNotIn("god module", report)
        self.assertIn("far larger than its neighbours", report)

    def test_the_finding_is_kinded_by_what_it_measures(self) -> None:
        """The kind, not just the sentence.

        A mutation that renamed the kind back to "god" passed every
        test, because the kind never reaches the rendered report — and
        the kind is what another tool would switch on.
        """
        import tempfile

        from harness.scan.layout import review_layout

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for n in range(6):
                (root / f"m{n}.py").write_text("x = 1\n", encoding="utf-8")
            (root / "huge.py").write_text("# pad\n" * 3000, encoding="utf-8")
            kinds = {finding.kind for finding in review_layout(root)}
        self.assertIn("outsized", kinds)
        self.assertNotIn("god", kinds)

    def test_the_size_rule_says_what_it_measures(self) -> None:
        layout = self._source("layout.py")
        self.assertIn("outsized", layout)
        self.assertIn("far larger than its neighbours", layout)

    def test_the_two_rules_still_catch_different_things(self) -> None:
        """Renaming one is not the same as deleting it."""
        from harness.scan.layout import OUTSIZED_MIN_BYTES
        from harness.scan.design import GOD_DEFS

        self.assertGreater(OUTSIZED_MIN_BYTES, 0)
        self.assertGreater(GOD_DEFS, 0)


if __name__ == "__main__":
    unittest.main()
