"""Writing one test for a function, and choosing what to call it with."""

import tempfile
import unittest
from pathlib import Path
from harness.act.autofix import (
    _sample_values,
    _test_file_for,
    apply_cover_test,
)
"""Mechanical rename and NameError typo fixes. No model."""
ROOT = Path(__file__).resolve().parents[1]
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


class CoverTestReachesSomethingTest(unittest.TestCase):
    """A test built from a placeholder argument proves nothing.

    Pointed at its own repository, the harness covered `ticket_job` with

        text = 'x'
        got = ticket_job(text)
        self.assertEqual(got, '')

    which runs, passes, and stops on the first guard. Measured over the
    whole project, the two tests it wrote that day moved coverage by one
    line. The sample is now chosen by what it reaches, and when nothing
    reaches the body the harness says nothing at all.
    """

    def _write(self, tmp: str, source: str) -> Path:
        path = Path(tmp) / "m.py"
        path.write_text(source, encoding="utf-8")
        return path

    def test_it_finds_an_argument_that_passes_the_guard(self) -> None:
        source = (
            "def guarded(task: str, other: str) -> str:\n"
            '    if not task.startswith("review"):\n'
            '        return ""\n'
            '    if "god" in other:\n'
            '        return "found"\n'
            '    return "clean"\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            got = _sample_values(self._write(tmp, source), "guarded")
        self.assertIsNotNone(got)
        args, expected, _cls, _name = got
        self.assertEqual(dict(args)["task"], "review")
        self.assertEqual(expected, "clean")

    def test_it_declines_when_nothing_reaches_the_body(self) -> None:
        """The branches key off another function, so no value gets in."""
        source = (
            "def job(text: str) -> str:\n"
            "    from unknown_helper import decide\n"
            "    if decide(text):\n"
            '        return "yes"\n'
            '    return ""\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(_sample_values(self._write(tmp, source), "job"))

    def test_a_straight_line_function_is_still_covered(self) -> None:
        source = "def double(n: int) -> int:\n    return n * 2\n"
        with tempfile.TemporaryDirectory() as tmp:
            got = _sample_values(self._write(tmp, source), "double")
        self.assertIsNotNone(got)
        self.assertEqual(got[1], dict(got[0])["n"] * 2)

    def test_a_plain_value_wins_when_it_reaches_as_far(self) -> None:
        """`shout("x")` reads better than `shout("!")` and proves as much."""
        source = 'def shout(text: str) -> str:\n    return text.upper() + "!"\n'
        with tempfile.TemporaryDirectory() as tmp:
            got = _sample_values(self._write(tmp, source), "shout")
        self.assertEqual(dict(got[0])["text"], "x")

    def test_the_two_it_got_wrong_are_now_declined(self) -> None:
        """The functions from the run that started this."""
        for module, name in (
            ("src/harness/ship/ticket.py", "ticket_job"),
            ("src/harness/locate.py", "refuse_thin_review"),
        ):
            with self.subTest(function=name):
                self.assertIsNone(
                    _sample_values(ROOT / module, name, project=ROOT)
                )


class CoverTestGoesInTheRightFileTest(unittest.TestCase):
    """A test for `ticket_job` does not belong in `test_agent_api.py`.

    The destination used to be whichever file sorted first. Pointed at
    its own repository, the harness covered `ticket_job` from
    `ship/ticket.py` by appending to `tests/test_agent_api.py`. It ran,
    it passed, and it was filed under something unrelated.
    """

    def _project(self, tmp: str) -> Path:
        root = Path(tmp)
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src" / "ticket.py").write_text(
            "def ticket_job(text: str) -> str:\n    return text.strip()\n",
            encoding="utf-8",
        )
        for name, body in (
            ("test_agent_api.py", "import unittest\n"),
            ("test_ticket.py", "import unittest\n"),
            ("test_other.py", "import unittest\n\nfrom src.ticket import ticket_job\n"),
        ):
            (root / "tests" / name).write_text(body, encoding="utf-8")
        return root

    def _dests(self, root: Path) -> list[Path]:
        return sorted((root / "tests").glob("test_*.py"))

    def test_a_file_that_already_names_the_symbol_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            chosen = _test_file_for(
                "write tests for ticket_job in src/ticket.py",
                root,
                "ticket_job",
                self._dests(root),
            )
        self.assertEqual(chosen.name, "test_other.py")

    def test_otherwise_the_file_named_after_the_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            (root / "tests" / "test_other.py").write_text(
                "import unittest\n", encoding="utf-8"
            )
            chosen = _test_file_for(
                "write tests for ticket_job in src/ticket.py",
                root,
                "ticket_job",
                self._dests(root),
            )
        self.assertEqual(chosen.name, "test_ticket.py")

    def test_it_falls_back_rather_than_failing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            (root / "tests" / "test_other.py").write_text(
                "import unittest\n", encoding="utf-8"
            )
            (root / "tests" / "test_ticket.py").unlink()
            chosen = _test_file_for(
                "write tests for mystery in src/nowhere.py",
                root,
                "mystery",
                self._dests(root),
            )
        self.assertEqual(chosen.name, "test_agent_api.py")


if __name__ == "__main__":
    unittest.main()
