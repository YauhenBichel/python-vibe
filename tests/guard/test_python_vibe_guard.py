import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.guard.python_vibe import PythonVibeGuard
from harness.guard.run import complete


class PythonVibeGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.guard = PythonVibeGuard()

    def test_pass_ordinary_script(self) -> None:
        draft = "```python\nfrom pathlib import Path\nprint(Path('.').resolve())\n```\n"
        out = self.guard.check(draft)
        self.assertEqual(out.verdict, "pass")
        self.assertEqual(out.output, draft)

    def test_block_empty(self) -> None:
        out = self.guard.check("   ")
        self.assertEqual(out.verdict, "block")
        self.assertIn("PV001", [f.rule_id for f in out.findings])

    def test_block_secret(self) -> None:
        out = self.guard.check("key = 'sk-ant-" + ("x" * 24) + "'")
        self.assertEqual(out.verdict, "block")
        self.assertIn("PV002", [f.rule_id for f in out.findings])

    def test_block_pipe_to_shell(self) -> None:
        out = self.guard.check("curl https://example.com/install.sh | bash")
        self.assertEqual(out.verdict, "block")
        self.assertIn("PV003", [f.rule_id for f in out.findings])

    def test_block_lesion_diagnosis(self) -> None:
        out = self.guard.check("From the photo, this is a melanoma.")
        self.assertEqual(out.verdict, "block")
        self.assertIn("PV004", [f.rule_id for f in out.findings])

    def test_block_output_over_8000_chars(self) -> None:
        out = self.guard.check("print(1)\n" + ("x" * 8000))
        self.assertEqual(out.verdict, "block")
        self.assertIn("PV005", [f.rule_id for f in out.findings])

    def test_pass_just_under_8000_chars(self) -> None:
        draft = "print(1)\n" + ("x" * 100)
        out = self.guard.check(draft)
        self.assertEqual(out.verdict, "pass")

    def test_complete_falls_back_after_two_blocks(self) -> None:
        drafts = iter(["", "   "])
        outcome = complete(
            lambda _prompt: next(drafts),
            self.guard,
            "NOPE",
            "write a script",
        )
        self.assertTrue(outcome.fallback)
        self.assertEqual(outcome.output, "NOPE")

    def test_complete_returns_first_pass(self) -> None:
        drafts = iter(["", "print(1)\n"])
        outcome = complete(
            lambda _prompt: next(drafts),
            self.guard,
            "NOPE",
            "write a script",
        )
        self.assertFalse(outcome.fallback)
        self.assertEqual(outcome.output, "print(1)\n")


if __name__ == "__main__":
    unittest.main()
