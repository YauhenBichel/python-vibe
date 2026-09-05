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


if __name__ == "__main__":
    unittest.main()
