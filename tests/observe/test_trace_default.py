"""A run records its turns unless asked not to.

Recording was opt-in, behind `--record`. So a week of real work on this
project produced sixty-five rows of training data in total, because
nobody passed the flag — and a trace not written is not recoverable
later. It is on by default now, into the project's own hidden folder,
with `--no-record` to turn it off.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness import Agent, AgentOptions  # noqa: E402
from harness.agent.loop import trace_path  # noqa: E402
from harness.observe.trace_record import default_trace_path  # noqa: E402


class WhereTheTurnsGoTest(unittest.TestCase):
    def test_by_default_into_the_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            options = AgentOptions(project=Path(tmp), task="add a function")
            self.assertEqual(
                trace_path(options), default_trace_path(Path(tmp).resolve())
            )

    def test_the_default_is_hidden_and_inside_the_project(self) -> None:
        where = default_trace_path(Path("/somewhere"))
        self.assertEqual(where.parent.name, ".python-vibe")
        self.assertTrue(where.name.endswith(".jsonl"))

    def test_an_explicit_path_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mine = Path(tmp) / "mine.jsonl"
            options = AgentOptions(
                project=Path(tmp), task="add a function", record=mine
            )
            self.assertEqual(trace_path(options), mine)

    def test_no_record_means_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            options = AgentOptions(
                project=Path(tmp), task="add a function", keep_no_record=True
            )
            self.assertIsNone(trace_path(options))

    def test_no_record_beats_an_explicit_path(self) -> None:
        """Asking for silence is asking for silence."""
        with tempfile.TemporaryDirectory() as tmp:
            options = AgentOptions(
                project=Path(tmp),
                task="add a function",
                record=Path(tmp) / "mine.jsonl",
                keep_no_record=True,
            )
            self.assertIsNone(trace_path(options))


class ARunWritesTheDefaultTraceTest(unittest.TestCase):
    SOURCE = (
        "def compute_total(prices):\n"
        "    return sum(prices)\n\n"
        "def total_with_tax(prices):\n"
        "    subtotal = compute_total(prices)\n"
        "    return subtotl\n"
    )

    def test_a_mechanical_fix_leaves_a_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "orders.py").write_text(self.SOURCE, encoding="utf-8")
            with mock.patch(
                "harness.agent.loop.make_generate",
                side_effect=AssertionError("model must not load"),
            ):
                Agent(
                    AgentOptions(
                        project=root,
                        task="find the NameError and fix it",
                    )
                ).run()
            dest = default_trace_path(root.resolve())
            self.assertTrue(dest.is_file(), dest)
            rows = [
                json.loads(line) for line in dest.read_text(encoding="utf-8").splitlines()
            ]
        self.assertEqual(len(rows), 1)
        self.assertIn("NameError", rows[0]["user"])
        self.assertEqual(rows[0]["stopped"], "done")

    def test_no_record_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "orders.py").write_text(self.SOURCE, encoding="utf-8")
            Agent(
                AgentOptions(
                    project=root,
                    task="find the NameError and fix it",
                    keep_no_record=True,
                )
            ).run()
            self.assertFalse(default_trace_path(root.resolve()).is_file())


class NobodyCommitsTheirTracesTest(unittest.TestCase):
    def test_this_project_ignores_the_trace_folder(self) -> None:
        root = Path(__file__).resolve().parents[2]
        ignored = (root / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".python-vibe/", ignored)



class EveryTurnSaysWhichRunTest(unittest.TestCase):
    """A turn with no run id cannot be told from a turn of a failed run.

    Both mutations below survived until this existed: dropping the id
    from each turn, and never recording how a run ended. Neither is
    visible from anything smaller than a whole run.
    """

    def _run_and_read(self, *drafts: str) -> list[dict]:
        import json
        from unittest import mock

        from harness import Agent, AgentOptions

        def scripted(*bodies: str):
            left = list(bodies)

            def generate(_prompt: str) -> str:
                return left.pop(0) if left else "Action: done\nSummary: out"

            return lambda *a, **k: ("scripted", generate)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "app.py").write_text(
                "def total(rows):\n    return sum(rows)\n", encoding="utf-8"
            )
            (root / "tests" / "test_app.py").write_text("x = 1\n", encoding="utf-8")
            with mock.patch("harness.agent.loop.make_generate", scripted(*drafts)):
                Agent(
                    AgentOptions(project=root, task="add multiply to src/app.py")
                ).run()
            trace = root / ".python-vibe" / "traces.jsonl"
            if not trace.is_file():
                return []
            return [json.loads(line) for line in trace.read_text().splitlines() if line.strip()]

    def test_every_turn_carries_a_run_id(self) -> None:
        rows = self._run_and_read(
            "Action: read\nPath: src/app.py",
            "Action: done\nSummary: read it",
        )
        self.assertTrue(rows, "nothing was recorded at all")
        missing = [r for r in rows if not r.get("run")]
        self.assertEqual(missing, [], f"turns with no run id: {missing}")

    def test_all_the_turns_of_one_run_share_the_id(self) -> None:
        rows = self._run_and_read(
            "Action: read\nPath: src/app.py",
            "Action: done\nSummary: read it",
        )
        self.assertEqual(len({r.get("run") for r in rows}), 1)

    def test_the_run_records_how_it_ended(self) -> None:
        rows = self._run_and_read(
            "Action: read\nPath: src/app.py",
            "Action: done\nSummary: read it",
        )
        closing = [r for r in rows if "ok" in r]
        self.assertEqual(len(closing), 1, f"expected one closing row, got {closing}")
        self.assertIn("stopped", closing[0])


if __name__ == "__main__":
    unittest.main()
