"""The benchmark must not report a broken import as a missing function.

`load()` skips a module that raises on import, which is right: a project
may hold a script that cannot run here. Skipping it silently was not. A
file that *defines* the wanted function and fails to import reported

    last_price not found in any module

and that sentence sends the reader looking for a missing function. It
did exactly that to me — I read three such failures as the run deleting
the function it was asked to fix, checked, and found it still there in
four runs of four. The message was wrong, not the agent.
"""

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]


def _bench():
    spec = importlib.util.spec_from_file_location(
        "python_vibe_bench_loader", ROOT / "scripts" / "measure" / "bench.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


DEFINED_BUT_BROKEN = '''"""Orders."""
from src.helpers import missing_thing


def last_price(prices: list[int]) -> int:
    return prices[-1]
'''
ABSENT = '"""Orders."""\n\n\ndef compute_total(prices):\n    return sum(prices)\n'
FINE = '"""Orders."""\n\n\ndef last_price(prices):\n    return prices[-1]\n'


class WhatTheLoaderSaysTest(unittest.TestCase):
    def setUp(self) -> None:
        self.loader = _bench().LOADER

    def _check(self, body: str) -> tuple[int, str]:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "orders.py").write_text(body, encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "-c",
                 self.loader + "assert load('last_price')([1, 2, 3]) == 3"],
                cwd=root, capture_output=True, text=True, timeout=60, check=False,
            )
            out = (proc.stderr or proc.stdout).strip()
            return proc.returncode, out.splitlines()[-1] if out else ""

    def test_a_broken_import_is_named_as_one(self) -> None:
        code, said = self._check(DEFINED_BUT_BROKEN)
        self.assertNotEqual(code, 0)
        self.assertIn("does not import", said)
        self.assertIn("src/orders.py", said)
        self.assertIn("ModuleNotFoundError", said)
        self.assertNotIn("not found in any module", said)

    def test_a_genuinely_missing_function_still_says_so(self) -> None:
        code, said = self._check(ABSENT)
        self.assertNotEqual(code, 0)
        self.assertIn("not found in any module", said)
        self.assertNotIn("does not import", said)

    def test_a_working_module_is_loaded(self) -> None:
        code, _ = self._check(FINE)
        self.assertEqual(code, 0)

    def test_a_broken_module_that_does_not_define_it_is_still_skipped(self) -> None:
        """An unrelated script that cannot import here is not the story."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "orders.py").write_text(FINE, encoding="utf-8")
            (root / "src" / "scratch.py").write_text(
                "import nonexistent_package\n", encoding="utf-8"
            )
            proc = subprocess.run(
                [sys.executable, "-c",
                 self.loader + "assert load('last_price')([1, 2, 3]) == 3"],
                cwd=root, capture_output=True, text=True, timeout=60, check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)


class TheReasonIsNotTruncatedAwayTest(unittest.TestCase):
    """60 characters cut the exception off the end of the one line that
    says why, leaving `src/orders.py defines last_price but does not
    import: Module` — the half naming the cause, gone."""

    SAID = (
        "Traceback (most recent call last):\n"
        "AssertionError: src/orders.py defines last_price but does not "
        "import: ModuleNotFoundError: No module named 'src.helpers'"
    )

    def setUp(self) -> None:
        self.bench = _bench()

    def test_the_whole_reason_survives(self) -> None:
        kept = self.bench.why_from(self.SAID)
        self.assertIn("does not import", kept)
        self.assertIn("ModuleNotFoundError", kept)
        self.assertIn("src.helpers", kept)

    def test_only_the_last_line_is_kept(self) -> None:
        self.assertNotIn("Traceback", self.bench.why_from(self.SAID))

    def test_something_enormous_is_still_cut(self) -> None:
        kept = self.bench.why_from("x" * 5000)
        self.assertEqual(len(kept), self.bench.WHY_LIMIT)

    def test_no_output_still_says_something(self) -> None:
        self.assertEqual(self.bench.why_from("   \n  "), "check failed")


class OnlyTheModuleThatDefinesItIsBlamedTest(unittest.TestCase):
    """A project may hold a script that cannot import here. That is not
    the story when the wanted function is genuinely absent."""

    def setUp(self) -> None:
        self.loader = _bench().LOADER

    def test_an_unrelated_broken_script_is_not_blamed(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            # Sorts before orders.py, so it is reached first.
            (root / "src" / "aaa_scratch.py").write_text(
                "import nonexistent_package\n", encoding="utf-8"
            )
            (root / "src" / "orders.py").write_text(ABSENT, encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "-c",
                 self.loader + "assert load('last_price')([1, 2, 3]) == 3"],
                cwd=root, capture_output=True, text=True, timeout=60, check=False,
            )
            said = (proc.stderr or proc.stdout).strip().splitlines()[-1]
            self.assertIn("not found in any module", said)
            self.assertNotIn("aaa_scratch", said)


if __name__ == "__main__":
    unittest.main()
