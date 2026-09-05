"""A Find: written without reading the file is written from memory.

Asked to add one field to a dict in a 330-line file, a run drafted
`Find: result = run_case(case, model, steps)` — a line that is not in
that file at all. It was refused, and sent again. Across every failing
run of that task the model went from `grep` straight to `patch` and
spent the budget guessing at a line it could have read.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.agent.policy import (  # noqa: E402
    LoopState,
    refuse_patch_before_reading,
)


def _scripted(*drafts: str):
    """Stand in for the model: hand back these drafts in order."""
    remaining = list(drafts)

    def generate(_prompt: str) -> str:
        return remaining.pop(0) if remaining else "Action: done\nSummary: out of drafts"

    return lambda *a, **k: ("scripted", generate)


class _Turn:
    """The four fields this rule reads off a model turn."""

    def __init__(self, action="patch", path="src/app.py", find="x = 1", append=""):
        self.action = action
        self.path = path
        self.find = find
        self.append = append


def _state(**over) -> LoopState:
    with tempfile.TemporaryDirectory() as tmp:
        state = LoopState(task="fix src/app.py", project=Path(tmp))
    for name, value in over.items():
        setattr(state, name, value)
    return state


class WritingFromMemoryTest(unittest.TestCase):
    def test_a_find_for_a_file_nobody_read_is_refused(self) -> None:
        refused = refuse_patch_before_reading(_state(), _Turn())
        self.assertIn("written from memory", refused)
        self.assertIn("Action: read Path: src/app.py", refused)

    def test_reading_it_first_is_enough(self) -> None:
        state = _state(files_seen={"src/app.py"})
        self.assertEqual(refuse_patch_before_reading(state, _Turn()), "")

    def test_the_harness_locating_it_is_enough(self) -> None:
        """Its text is already in the opening turn, so it has been seen."""
        state = _state(located_path="src/app.py")
        self.assertEqual(refuse_patch_before_reading(state, _Turn()), "")

    def test_a_windows_style_path_counts_as_the_same_file(self) -> None:
        state = _state(files_seen={"src\\app.py"})
        self.assertEqual(refuse_patch_before_reading(state, _Turn()), "")


class WhatItLeavesAloneTest(unittest.TestCase):
    def test_an_append_needs_no_find(self) -> None:
        """Adding a function does not have to match anything."""
        turn = _Turn(find="", append="def total():\n    return 1\n")
        self.assertEqual(refuse_patch_before_reading(_state(), turn), "")

    def test_another_action_is_not_this_rule(self) -> None:
        self.assertEqual(
            refuse_patch_before_reading(_state(), _Turn(action="edit")), ""
        )

    def test_a_patch_with_no_path_at_all(self) -> None:
        turn = _Turn(path="")
        self.assertEqual(refuse_patch_before_reading(_state(), turn), "")

    def test_a_reading_of_a_different_file_does_not_count(self) -> None:
        state = _state(files_seen={"src/other.py"})
        self.assertIn("written from memory", refuse_patch_before_reading(state, _Turn()))



class TheGateActuallyAsksTest(unittest.TestCase):
    """`refuse_before` is what the loop calls, so that is what is tested.

    A whole-run test cannot show this. When the task names a file the
    harness locates it, and a located file is exempt — correctly, its
    text is in the opening turn. When the task names no file, the model
    cannot patch a second one either, because `refuse_wrong_file` gets
    there first. The gate is the honest seam.
    """

    class _FullTurn:
        action = "patch"
        path = "src/app.py"
        find = "x = 1"
        replace = ""
        append = ""
        query = pattern = scope = name = argv = summary = ""

    def test_the_gate_refuses_an_unread_patch(self) -> None:
        from harness.agent.policy import refuse_before

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
            state = LoopState(task="tidy the project", project=root)
            self.assertIn(
                "Nothing has read src/app.py", refuse_before(state, self._FullTurn())
            )

    def test_the_gate_lets_it_through_once_read(self) -> None:
        from harness.agent.policy import refuse_before

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
            state = LoopState(task="tidy the project", project=root)
            state.files_seen.add("src/app.py")
            self.assertEqual(refuse_before(state, self._FullTurn()), "")

    def test_a_run_records_the_files_it_reads(self) -> None:
        """The loop has to put the read into `files_seen` or the gate never clears."""
        from unittest import mock

        from harness import Agent, AgentOptions

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "other.py").write_text(
                "def total(rows):\n    return sum(rows)\n", encoding="utf-8"
            )
            (root / "tests" / "test_other.py").write_text("x = 1\n", encoding="utf-8")
            seen: list[set[str]] = []
            real = LoopState.__init__

            def spy(self, *a, **k):
                real(self, *a, **k)
                seen.append(self.files_seen)

            with mock.patch.object(LoopState, "__init__", spy):
                with mock.patch(
                    "harness.agent.loop.make_generate",
                    _scripted(
                        "Action: read\nPath: tests/test_other.py",
                        "Action: done\nSummary: read the test",
                    ),
                ):
                    # A task naming a file gets past the opening question.
                    # The model then reads a *different* file, which is
                    # the only thing `files_seen` can be learning from.
                    Agent(
                        AgentOptions(
                            project=root, task="change the sum in src/other.py"
                        )
                    ).run()
        self.assertTrue(
            any("tests/test_other.py" in item for item in seen),
            f"the read was never recorded: {seen}",
        )


if __name__ == "__main__":
    unittest.main()
