import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from finetune.everyday import is_tiny_model
from harness.observe.eval_gate import action_parse_rate, bugfix_fixture_ready, held_out_run_pass
from harness.openai_api import parse_chat_body, warn_tiny


class EvalGateTest(unittest.TestCase):
    def test_action_parse_fixtures(self) -> None:
        ok, n = action_parse_rate()
        self.assertGreater(n, 0)
        self.assertEqual(ok, n)

    def test_held_out_gold_scripts(self) -> None:
        ok, n = held_out_run_pass()
        self.assertEqual(n, 2)
        self.assertEqual(ok, n)

    def test_bugfix_fixture_is_1kb_and_applyable(self) -> None:
        ready, reason = bugfix_fixture_ready()
        self.assertTrue(ready, reason)

    def test_tiny_detection(self) -> None:
        self.assertTrue(is_tiny_model("qwen2.5-coder:0.5b"))
        self.assertFalse(is_tiny_model("llama3.1:8b"))

    def test_openai_parse_and_tiny_warn(self) -> None:
        parsed = parse_chat_body(
            b'{"model":"llama3.1:8b","messages":[{"role":"user","content":"hi"}]}'
        )
        self.assertEqual(parsed["model"], "llama3.1:8b")
        self.assertIsNone(warn_tiny("llama3.1:8b"))
        self.assertIsNotNone(warn_tiny("qwen2.5-coder:0.5b"))


if __name__ == "__main__":
    unittest.main()
