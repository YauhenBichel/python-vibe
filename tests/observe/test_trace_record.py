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

    def test_drop_secret_turns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "extra.jsonl"
            append_turn(dest, {"user": "hi", "assistant": "key = 'sk-ant-" + ("x" * 24) + "'"})
            self.assertFalse(dest.is_file())
            append_turn(dest, {"user": "Action: grep", "assistant": "Action: read\nPath: a.py"})
            rows = [json.loads(line) for line in dest.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["user"], "Action: grep")


if __name__ == "__main__":
    unittest.main()
