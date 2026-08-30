"""The benchmark's repeat mode, which is the point of the benchmark.

One pass of these cases is a sample, not a score: ten of the fifteen
changed verdict between identical runs on unchanged code. The runner has
to make repeating easy and has to say so when it has not been done.
"""

import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _bench():
    spec = importlib.util.spec_from_file_location(
        "python_vibe_bench", ROOT / "scripts" / "bench.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _rows(verdicts: dict[str, str]) -> list[dict]:
    """verdicts: case -> a string like 'YnY', one letter per pass."""
    rows = []
    for case, marks in verdicts.items():
        for number, mark in enumerate(marks, 1):
            rows.append(
                {
                    "case": case,
                    "tier": 1,
                    "worked": "yes" if mark == "Y" else "no",
                    "pass": number,
                }
            )
    return rows


class RepeatReportTest(unittest.TestCase):
    def _report(self, rows, passes) -> str:
        buffer = io.StringIO()
        with redirect_stderr(buffer):
            _bench().report(rows, passes)
        return buffer.getvalue()

    def test_a_single_pass_says_it_cannot_settle_a_comparison(self) -> None:
        text = self._report(_rows({"a": "Y", "b": "n"}), 1)
        self.assertIn("Only one pass", text)
        self.assertIn("--repeat", text)

    def test_repeats_show_a_rate_for_every_case(self) -> None:
        text = self._report(_rows({"steady": "YYY", "flaky": "YnY"}), 3)
        self.assertIn("steady", text)
        self.assertIn("3/3", text)
        self.assertIn("2/3", text)
        self.assertNotIn("Only one pass", text)

    def test_it_counts_what_held_still_and_what_moved(self) -> None:
        text = self._report(_rows({"a": "YYY", "b": "YnY", "c": "nnn"}), 3)
        self.assertIn("passed every pass: 1", text)
        self.assertIn("changed verdict: 1", text)

    def test_it_names_the_spread_when_anything_moved(self) -> None:
        text = self._report(_rows({"a": "YYY", "b": "Ynn"}), 3)
        self.assertIn("totals per pass: [2, 1, 1]", text)
        self.assertIn("noise", text)

    def test_a_steady_set_is_not_called_noisy(self) -> None:
        text = self._report(_rows({"a": "YY", "b": "YY"}), 2)
        self.assertIn("changed verdict: 0", text)
        self.assertNotIn("noise", text)


class RepeatFlagTest(unittest.TestCase):
    def test_the_flag_exists_and_defaults_to_one(self) -> None:
        source = (ROOT / "scripts" / "bench.py").read_text(encoding="utf-8")
        self.assertIn('"--repeat"', source)
        self.assertIn('row["pass"] = number', source)

    def test_zero_repeats_is_refused(self) -> None:
        module = _bench()
        old = sys.argv
        try:
            sys.argv = ["bench.py", "--repeat", "0"]
            with redirect_stderr(io.StringIO()):
                self.assertEqual(module.main(), 2)
        finally:
            sys.argv = old


if __name__ == "__main__":
    unittest.main()
