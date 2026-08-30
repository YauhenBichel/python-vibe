"""Adding a small function, and appending rather than replacing a file."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock
from harness import Agent, AgentOptions
from harness.act.autofix import (
    append_instead_of_replacing,
    apply_add_function,
    usual_first_arg,
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
