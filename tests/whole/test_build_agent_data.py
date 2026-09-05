"""The training set is built from what runs actually record.

Recording turns on by default was the point of one change; reading them
was left out of another. `build_agent_data.py` read only
`data/agent-loop/extra.jsonl`, the file the old opt-in `--record` flag
wrote — so every turn recorded by default landed in
`.python-vibe/traces.jsonl` where nothing looked at it, and the training
set stayed at its seed size while runs piled up.
"""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def _script():
    spec = importlib.util.spec_from_file_location(
        "python_vibe_build_agent_data", ROOT / "scripts" / "weights" / "build_agent_data.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _traced(root: Path, rows: list[dict]) -> Path:
    folder = root / ".python-vibe"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "traces.jsonl"
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    return path


class ReadingRecordedTurnsTest(unittest.TestCase):
    def test_a_recorded_turn_becomes_a_pair(self) -> None:
        build = _script()
        with tempfile.TemporaryDirectory() as tmp:
            path = _traced(
                Path(tmp),
                [{"user": "Action: read", "assistant": "Action: done", "action": "done"}],
            )
            self.assertEqual(
                build.load_turns(path), [("Action: read", "Action: done")]
            )

    def test_a_file_that_is_not_there_reads_as_nothing(self) -> None:
        build = _script()
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(build.load_turns(Path(tmp) / "gone.jsonl"), [])

    def test_a_turn_missing_half_of_the_pair_is_skipped(self) -> None:
        build = _script()
        with tempfile.TemporaryDirectory() as tmp:
            path = _traced(Path(tmp), [{"user": "only a prompt"}])
            self.assertEqual(build.load_turns(path), [])


class WhereItLooksTest(unittest.TestCase):
    def test_it_reads_the_file_runs_record_to(self) -> None:
        """The whole point: the default trace path is one of the sources."""
        build = _script()
        from harness.observe.trace_record import default_trace_path

        names = [path.name for path in build.recorded_files([])]
        parents = [path.parent.name for path in build.recorded_files([])]
        self.assertIn(default_trace_path(ROOT).name, names)
        self.assertIn(".python-vibe", parents)

    def test_the_old_extra_file_is_still_read(self) -> None:
        """Anyone with turns already in it should not lose them."""
        build = _script()
        self.assertIn(
            "extra.jsonl", [path.name for path in build.recorded_files([])]
        )

    def test_another_project_can_be_named(self) -> None:
        build = _script()
        with tempfile.TemporaryDirectory() as tmp:
            found = build.recorded_files([Path(tmp)])
        self.assertTrue(
            any(str(tmp) in str(path) for path in found),
            f"--from was not read: {found}",
        )



class TheSameTurnCountsOnceTest(unittest.TestCase):
    """Training on a duplicated turn weights it twice.

    It happens for real: `--record` pointed at a file this already
    reads, or `--from` naming the project being built in.
    """

    def test_a_turn_in_two_files_is_used_once(self) -> None:
        build = _script()
        row = {"user": "Action: read", "assistant": "Action: done"}
        with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
            first = _traced(Path(one), [row])
            second = _traced(Path(two), [row])
            self.assertEqual(len(build.gather([first, second])), 1)

    def test_two_different_turns_are_both_kept(self) -> None:
        build = _script()
        with tempfile.TemporaryDirectory() as tmp:
            path = _traced(
                Path(tmp),
                [
                    {"user": "Action: read", "assistant": "Action: done"},
                    {"user": "Action: grep", "assistant": "Action: read"},
                ],
            )
            self.assertEqual(len(build.gather([path])), 2)

    def test_the_order_they_were_recorded_in_is_kept(self) -> None:
        build = _script()
        with tempfile.TemporaryDirectory() as tmp:
            path = _traced(
                Path(tmp),
                [
                    {"user": "first", "assistant": "a"},
                    {"user": "second", "assistant": "b"},
                ],
            )
            self.assertEqual([pair[0] for pair in build.gather([path])],
                             ["first", "second"])



class TurnsFromRunsThatFailedTest(unittest.TestCase):
    """About a third of runs fail, and their turns look like the rest.

    Without a run id and an outcome on the record, a turn from a run
    that spent twenty steps and wrote nothing is indistinguishable from
    a turn from a run that did the job — so the training set teaches
    both.
    """

    WORKED = [
        {"run": "aaa", "user": "Action: read", "assistant": "Action: patch"},
        {"run": "aaa", "user": "Action: patch", "assistant": "Action: done"},
        {"run": "aaa", "user": "t", "assistant": "s", "stopped": "done", "ok": True},
    ]
    FAILED = [
        {"run": "bbb", "user": "Action: grep", "assistant": "Action: patch"},
        {"run": "bbb", "user": "t", "assistant": "s", "stopped": "steps", "ok": False},
    ]

    def _file(self, tmp: str, rows: list[dict]) -> Path:
        path = Path(tmp) / "turns.jsonl"
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
        return path

    def test_a_failed_run_is_named_by_its_closing_row(self) -> None:
        build = _script()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._file(tmp, self.WORKED + self.FAILED)
            self.assertEqual(build.failed_runs(path), {"bbb"})

    def test_its_turns_are_left_out(self) -> None:
        build = _script()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._file(tmp, self.WORKED + self.FAILED)
            kept = build.load_turns(path)
        self.assertEqual(kept, [("Action: read", "Action: patch"),
                                ("Action: patch", "Action: done")])

    def test_keep_failed_puts_them_back(self) -> None:
        build = _script()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._file(tmp, self.WORKED + self.FAILED)
            self.assertEqual(len(build.load_turns(path, keep_failed=True)), 3)

    def test_the_closing_row_is_never_a_training_pair(self) -> None:
        """It says how a run ended. Nobody should learn to imitate it."""
        build = _script()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._file(tmp, self.WORKED)
            kept = build.load_turns(path)
        self.assertEqual(len(kept), 2)
        self.assertNotIn(("t", "s"), kept)

    def test_a_file_recorded_before_run_ids_is_unchanged(self) -> None:
        """Turns already collected have no id and no outcome row."""
        build = _script()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._file(
                tmp, [{"user": "Action: read", "assistant": "Action: done"}]
            )
            self.assertEqual(build.failed_runs(path), set())
            self.assertEqual(len(build.load_turns(path)), 1)


if __name__ == "__main__":
    unittest.main()
