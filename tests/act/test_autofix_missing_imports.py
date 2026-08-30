"""Adding the import line for a name used without one."""

import tempfile
import unittest
from pathlib import Path
"""Mechanical rename and NameError typo fixes. No model."""
ROOT = Path(__file__).resolve().parents[2]
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


if __name__ == "__main__":
    unittest.main()
