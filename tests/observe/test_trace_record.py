import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.observe.trace_record import append_turn, redact


class TraceRecordTest(unittest.TestCase):
    def test_redact_home(self) -> None:
        self.assertIn("/Users/you", redact("/Users/someone/DevBox/app"))

    def test_redact_linux_home_and_hosts(self) -> None:
        text = redact("/home/alice/app https://devbox.example.internal:8080/logs db.internal")
        self.assertIn("/home/you/app", text)
        self.assertIn("https://[host]/logs", text)
        self.assertTrue(text.endswith("[host]"))

    def test_redact_keeps_python_dotted_names(self) -> None:
        self.assertIn("os.path.exists", redact("check os.path.exists before writing"))

    def test_drop_secret_turns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "extra.jsonl"
            append_turn(dest, {"user": "hi", "assistant": "key = 'sk-ant-" + ("x" * 24) + "'"})
            self.assertFalse(dest.is_file())
            append_turn(
                dest,
                {
                    "user": "Action: grep",
                    "assistant": "Action: read\nPath: a.py",
                    "action": "read",
                    "tool_result": "https://runner.example.internal/out",
                },
            )
            rows = [json.loads(line) for line in dest.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["user"], "Action: grep")
        self.assertEqual(rows[0]["tool_result"], "https://[host]/out")

    def test_drop_secret_tool_result_turns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "extra.jsonl"
            append_turn(
                dest,
                {
                    "user": "Action: run",
                    "assistant": "Action: run\nArgs: ['tool.py']",
                    "action": "run",
                    "tool_result": "token = ghp_" + ("x" * 24),
                },
            )
            self.assertFalse(dest.is_file())


if __name__ == "__main__":
    unittest.main()
