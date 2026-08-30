import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.agent.policy import refuse_wrong_file
from harness.locate import (
    def_hit_path,
    locate_py,
    prelude,
    refuse_early_done,
    refuse_design_dirty,
    refuse_question_write,
    refuse_redundant_explore,
    refuse_redundant_locate,
    refuse_invented_review,
    refuse_shallow_done,
    refuse_thin_review,
    refuse_write_tests_ask,
    return_annotation,
    signature_line,
)


class SmartHarnessTest(unittest.TestCase):
    def test_def_hit_prefers_definition(self) -> None:
        grep = (
            "src/a.py:1:from harness.act.code import apply_source\n"
            "src/harness/code.py:84:def apply_source(path, source, *, original):\n"
        )
        self.assertEqual(def_hit_path(grep, "apply_source"), "src/harness/code.py")

    def test_locate_reads_defining_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "pkg"
            src.mkdir()
            (src / "code.py").write_text(
                "def apply_source(path, source, *, original):\n"
                "    if not source.strip():\n"
                "        raise ValueError('empty draft')\n",
                encoding="utf-8",
            )
            (src / "other.py").write_text(
                "from pkg.code import apply_source\n",
                encoding="utf-8",
            )
            text, path = locate_py(root, "apply_source")
            self.assertEqual(path, "pkg/code.py")
            self.assertIn("empty draft", text)
            self.assertIn("# auto-read", text)

    def test_prelude_write_tests_opens_the_symbol(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "pkg"
            pkg.mkdir()
            (pkg / "cron.py").write_text(
                "def validate_cron_and_timezone(cron_expr: str, timezone: str) -> None:\n"
                "    return None\n",
                encoding="utf-8",
            )
            text, path = prelude(root, "write unit tests for validate_cron_and_timezone")
            self.assertEqual(path, "pkg/cron.py")
            self.assertIn("write-tests", text)
            self.assertIn("tests/test_validate_cron_and_timezone.py", text)
            self.assertIn("Do not ask", text)

    def test_prelude_question_and_add(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "pkg"
            pkg.mkdir()
            (pkg / "mathy.py").write_text(
                "def compute_total(rows) -> int:\n    return sum(rows)\n",
                encoding="utf-8",
            )
            q_text, q_path = prelude(root, "what does compute_total return?")
            self.assertIn("auto-read", q_text)
            self.assertEqual(q_path, "pkg/mathy.py")
            self.assertIn("-> type", q_text)
            add_text, _add_path = prelude(
                root, "add a function multiply(a, b) and a unit test"
            )
            self.assertIn("(no hits)", add_text)
            self.assertIn("Path: pkg/mathy.py", add_text)
            self.assertIn("def multiply", add_text)

    def test_prelude_named_review_does_not_ask_for_a_patch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            src.mkdir()
            (src / "orders.py").write_text(
                "def total_with_tax(prices):\n"
                "    subtotal = sum(prices)\n"
                "    return subtotl\n",
                encoding="utf-8",
            )
            text, path = prelude(root, "review src/orders.py for bugs")
            self.assertEqual(path, "src/orders.py")
            self.assertIn("must be done", text)
            self.assertIn("subtotl", text)
            self.assertNotIn("must be patch Path:", text)

    def test_refuse_early_done(self) -> None:
        self.assertIn("locate", refuse_early_done("what does apply_source refuse?", "", ""))
        self.assertEqual(
            refuse_early_done(
                "what does apply_source refuse?",
                "src/harness/code.py",
                "src/harness/code.py",
            ),
            "",
        )

    def test_refuse_question_write_and_reread(self) -> None:
        self.assertIn(
            "do not edit",
            refuse_question_write("what does complete do?", "patch").lower(),
        )
        self.assertEqual(refuse_question_write("add a function multiply", "patch"), "")
        self.assertEqual(
            refuse_question_write("review the project structure", "edit"),
            "",
        )
        from harness.locate import refuse_question_ask

        self.assertIn(
            "already located",
            refuse_question_ask("what does add return?", "ask", "pkg/mathy.py"),
        )
        self.assertEqual(
            refuse_question_ask("what does add return?", "ask", ""),
            "",
        )
        self.assertIn(
            "auto-read",
            refuse_redundant_explore(
                "what does listen_addr return?",
                "read",
                "src/harness/http.py",
                "src/harness/http.py",
            ),
        )
        self.assertEqual(
            refuse_redundant_explore(
                "what does listen_addr return?",
                "read",
                "src/harness/run.py",
                "src/harness/http.py",
            ),
            "",
        )

    def test_signature_and_shallow_done(self) -> None:
        grep = (
            "src/harness/http.py:18:"
            "def listen_addr(argv: list[str] | None = None) -> tuple[str, int]:"
        )
        sig = signature_line(grep, "listen_addr")
        self.assertIn("def listen_addr(", sig)
        self.assertEqual(return_annotation(sig), "tuple[str, int]")
        self.assertIn(
            "tuple[str, int]",
            refuse_shallow_done(
                "what does listen_addr return?",
                "a tuple containing the host and port",
                sig,
            ),
        )
        self.assertEqual(
            refuse_shallow_done(
                "what does listen_addr return?",
                "returns tuple[str, int] from env or argv",
                sig,
            ),
            "",
        )
        self.assertEqual(
            refuse_shallow_done("add a function multiply", "done", sig),
            "",
        )
        self.assertIn(
            "what it computes",
            refuse_shallow_done(
                "what does compute_total return?",
                '"int"',
                "def compute_total(prices: list[int]) -> int:",
            ),
        )
        self.assertIn(
            "patch",
            refuse_redundant_locate(
                "add a function multiply(a, b) and a unit test", "locate", True
            ),
        )
        self.assertEqual(
            refuse_redundant_locate(
                "add a function multiply(a, b) and a unit test", "locate", False
            ),
            "",
        )

    def test_design_loop_refuses_done_while_dirty(self) -> None:
        dirty = "design review\n- god module: pkg/kitchen.py has 4 top-level functions"
        self.assertIn(
            "findings remain",
            refuse_design_dirty("review the project structure", dirty),
        )
        clean = "no structure findings in scope — pkg/ and tests/ look split"
        self.assertEqual(
            refuse_design_dirty("review the project structure", clean),
            "",
        )
        self.assertIn(
            "no structure findings",
            refuse_thin_review("review the project structure", "looks fine", clean),
        )
        self.assertEqual(
            refuse_thin_review(
                "review the project structure",
                "no structure findings",
                clean,
            ),
            "",
        )

    def test_write_tests_ask_and_invented_review(self) -> None:
        self.assertIn(
            "patch",
            refuse_write_tests_ask(
                "write unit tests for validate_cron_and_timezone",
                "ask",
            ),
        )
        self.assertEqual(
            refuse_write_tests_ask("what does validate_cron_and_timezone return?", "ask"),
            "",
        )
        body = "def validate_cron_and_timezone(cron_expr: str, timezone: str) -> None:\n"
        self.assertIn(
            "compute_total",
            refuse_invented_review(
                "find errors in scheduling.py",
                "compute_total returns 0 for an empty list",
                body,
            ),
        )
        self.assertEqual(
            refuse_invented_review(
                "find errors in scheduling.py",
                "no errors found in scheduling.py",
                body,
            ),
            "",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIn(
                "tests/",
                refuse_wrong_file(
                    "write unit tests for validate_cron_and_timezone",
                    root,
                    "patch",
                    "surfaces/cli/commands/misses.py",
                ),
            )


if __name__ == "__main__":
    unittest.main()
