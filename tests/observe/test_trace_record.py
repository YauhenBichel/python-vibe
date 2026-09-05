import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.observe.trace_record import append_turn, default_trace_path, redact, render_last


class TraceRecordTest(unittest.TestCase):
    def test_redact_home(self) -> None:
        self.assertIn("/Users/you", redact("/Users/someone/DevBox/app"))

    def test_redact_linux_home_and_hosts(self) -> None:
        text = redact(
            "/home/alice/app https://devbox.example.internal:8080/logs "
            "db.internal runner.example.internal:8443"
        )
        self.assertIn("/home/you/app", text)
        self.assertIn("https://[host]/logs", text)
        self.assertIn("[host] [host]", text)
        self.assertNotIn("runner.", text)

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


    def test_a_url_host_goes_even_when_it_is_not_an_internal_name(self) -> None:
        """The two host rules must be told apart.

        The existing case used `devbox.example.internal:8080`, which the
        bare-name rule also matches, so removing the URL rule altogether
        left every test passing.
        """
        text = redact("posted to https://example.com/logs and http://10.0.0.4:9000/x")
        self.assertIn("https://[host]/logs", text)
        self.assertIn("http://[host]/x", text)
        self.assertNotIn("example.com", text)
        self.assertNotIn("10.0.0.4", text)

    def test_real_python_is_not_mistaken_for_a_hostname(self) -> None:
        """`Path.home()` is standard Python, and this repo calls it.

        A trace is training data. Rewriting `Path.home()` to `[host]()`
        would teach the model a mistake, and the sentence below is one
        of the harness's own refusals — recorded into the trace as the
        next prompt when a draft is refused, so the harness would be
        teaching from its own corrupted advice.
        """
        for good in (
            "use Path.home() for the config",
            "no hardcoded home. Use Path.home().",
            "os.path.exists before writing",
        ):
            with self.subTest(text=good):
                self.assertEqual(redact(good), good)

    def test_a_dotted_file_name_is_not_a_hostname(self) -> None:
        kept = "read .claude/settings.local.json"
        self.assertEqual(redact(kept), kept)

    def test_a_port_makes_it_a_host_beyond_doubt(self) -> None:
        """`box.local:8443` is a host; `Path.home()` never has a port."""
        self.assertEqual(redact("box.local:8443"), "[host]")
        self.assertEqual(redact("nas.home:5000"), "[host]")

    def test_the_unambiguous_endings_still_go(self) -> None:
        for host in ("db.internal", "build.lan", "wiki.corp"):
            with self.subTest(host=host):
                self.assertEqual(redact(host), "[host]")


class LastTurnsTest(unittest.TestCase):
    def test_no_file_says_so(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            text = render_last(Path(tmp))
        self.assertIn("no traces", text)

    def test_it_prints_the_latest_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = default_trace_path(Path(tmp))
            append_turn(dest, {"user": "first", "assistant": "Action: read", "action": "read"})
            append_turn(dest, {"user": "next", "assistant": "Action: done", "action": "done"})
            text = render_last(Path(tmp))
        self.assertIn("2 turns", text)
        self.assertIn("done: Action: done", text)


if __name__ == "__main__":
    unittest.main()
